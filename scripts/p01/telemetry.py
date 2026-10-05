"""Validate bounded diagnostic snapshots and derive three inspectable signal views.

This collector is an operator tool for the disposable P01 campaigns. It has no
network listener, product authority, durable audit role or implied OTLP endpoint.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import re
import time

from local_runtime import SERVICES

LIMIT = 65536
FIELDS = {'schema_version', 'event', 'service', 'source_revision', 'environment',
          'timestamp_unix_us', 'trace_id', 'span_id', 'parent_span_id',
          'route', 'method', 'status', 'duration_us'}
ROUTES = {'/', '/health/live', '/health/ready', '/health/dependencies', 'other'}
METHODS = {'GET', 'HEAD', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'OTHER'}
BUCKETS_US = (1000, 10000, 100000, 1000000)


def identifier(value, length):
    return (isinstance(value, str) and re.fullmatch('[0-9a-f]{%d}' % length, value)
            and value != '0' * length)


def records(raw: bytes, service: str, revision: str, environment: str) -> list[dict]:
    if len(raw) > LIMIT or (raw and not raw.endswith(b'\n')):
        raise ValueError('Oversized or incomplete diagnostic snapshot')
    rows, seen = [], set()
    for line in raw.splitlines():
        if len(line) > 1024:
            raise ValueError('Oversized diagnostic record')
        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError('Duplicate diagnostic field')
                result[key] = value
            return result
        row = json.loads(line, object_pairs_hook=unique)
        if not isinstance(row, dict) or set(row) != FIELDS:
            raise ValueError('Unexpected diagnostic fields')
        if (type(row['schema_version']) is not int or row['schema_version'] != 1
                or row['event'] != 'http.response' or service not in SERVICES
                or row['service'] != service or row['source_revision'] != revision
                or not re.fullmatch('[0-9a-f]{40}', revision)
                or environment not in {'development', 'p01-compose', 'p01-kubernetes'}
                or row['environment'] != environment):
            raise ValueError('Diagnostic ownership or revision mismatch')
        if (not identifier(row['trace_id'], 32) or not identifier(row['span_id'], 16)
                or (row['parent_span_id'] is not None and not identifier(row['parent_span_id'], 16))):
            raise ValueError('Invalid diagnostic correlation')
        if (type(row['route']) is not str or row['route'] not in ROUTES
                or type(row['method']) is not str or row['method'] not in METHODS):
            raise ValueError('Unbounded diagnostic dimension')
        for field, low, high in [('status', 100, 599), ('duration_us', 0, 86400000000),
                                 ('timestamp_unix_us', 1, 2**63 - 1)]:
            if type(row[field]) is not int or not low <= row[field] <= high:
                raise ValueError('Invalid diagnostic measurement')
        if row['span_id'] in seen:
            raise ValueError('Duplicate diagnostic span')
        seen.add(row['span_id'])
        rows.append(row)
    return rows


def freshness(rows: list[dict], now_us: int, maximum_age_us: int) -> str:
    if not rows:
        return 'MISSING'
    age = now_us - max(row['timestamp_unix_us'] for row in rows)
    if age < -1000000:
        return 'CLOCK_INVALID'
    return 'FRESH' if age <= maximum_age_us else 'STALE'


def export(rows: list[dict], directory: Path) -> dict:
    """Already validated records only; retain logs, spans and bounded metrics."""
    directory.mkdir(parents=True, exist_ok=False)
    logs = b''.join((json.dumps(row, sort_keys=True) + '\n').encode() for row in rows)
    (directory / 'logs.jsonl').write_bytes(logs)
    spans = []
    counts, durations, buckets = Counter(), Counter(), {}
    for row in rows:
        spans.append({key: row[key] for key in ('service', 'source_revision', 'environment',
                       'trace_id', 'span_id', 'parent_span_id', 'timestamp_unix_us',
                       'duration_us', 'route', 'method', 'status')})
        key = (row['service'], row['route'], row['method'], str(row['status'] // 100) + 'xx')
        counts[key] += 1
        durations[key] += row['duration_us']
        bins = buckets.setdefault(key, [0] * (len(BUCKETS_US) + 1))
        for i, upper in enumerate(BUCKETS_US):
            bins[i] += row['duration_us'] <= upper
        bins[-1] += 1
    (directory / 'spans.jsonl').write_text(''.join(json.dumps(row, sort_keys=True) + '\n' for row in spans))
    metrics = {'scope': 'observed_response_headers_only', 'missing_data_is_zero': False,
               'duration_unit': 'microseconds', 'bucket_upper_bounds': [*BUCKETS_US, None],
               'series': [{'labels': dict(zip(('service', 'route', 'method', 'status_class'), key)),
                           'responses': counts[key], 'duration_sum_us': durations[key],
                           'duration_buckets_cumulative': buckets[key]} for key in sorted(counts)]}
    (directory / 'metrics.json').write_text(json.dumps(metrics, indent=2) + '\n')
    return {'records': len(rows), 'spans': len(spans), 'metric_series': len(metrics['series']),
            'response_count': sum(counts.values()),
            'freshness': freshness(rows, time.time_ns() // 1000, 300000000)}


def control(service: str, operation: str, expected_sha256: str | None = None) -> list[str]:
    """Fixed privileged exec adapter, never an HTTP route or caller-provided code."""
    if service not in SERVICES or operation not in {'snapshot', 'acknowledge', 'permissions'}:
        raise ValueError('Unknown diagnostic control')
    if operation == 'acknowledge' and not re.fullmatch('[0-9a-f]{64}', expected_sha256 or ''):
        raise ValueError('Invalid snapshot identity')
    if operation == 'permissions':
        if service in {'console', 'governance', 'catalogue', 'assurance'}:
            return ['php', '-r', "echo json_encode(['directory_mode'=>fileperms('/tmp/product-telemetry') & 07777,'file_mode'=>fileperms('/tmp/product-telemetry/events.jsonl') & 07777]);"]
        return ['/opt/venv/bin/python', '-I', '-c', "import json,os; print(json.dumps({'directory_mode':os.stat('/tmp/product-telemetry').st_mode & 0o7777,'file_mode':os.stat('/tmp/product-telemetry/events.jsonl').st_mode & 0o7777}))"]
    if service in {'console', 'governance', 'catalogue', 'assurance'}:
        code = "require '/app/vendor/autoload.php'; $b=new App\\Infrastructure\\Foundation\\BoundedSignalBuffer; "
        code += 'echo $b->snapshot();' if operation == 'snapshot' else f"$b->acknowledge('{expected_sha256}');"
        return ['php', '-r', code]
    code = f'from {service}.infrastructure.telemetry import BoundedSignalBuffer; import sys; b=BoundedSignalBuffer(); '
    code += 'sys.stdout.buffer.write(b.snapshot())' if operation == 'snapshot' else f'b.acknowledge("{expected_sha256}")'
    return ['/opt/venv/bin/python', '-I', '-c', code]
