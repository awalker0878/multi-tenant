"""Deployed HTTP correlation and real bounded-collection fault campaign."""
import hashlib
import json
import secrets
import time

from local_runtime import SERVICES, PHP_SERVICES
from telemetry import control, export, freshness, records


FILL_PROBE = '''import json,ssl,sys,time,urllib.request
request=json.load(sys.stdin)
context=ssl.create_default_context(cafile='/run/secrets/ca.crt')
samples=[]
for _ in range(256):
    started=time.monotonic()
    with urllib.request.urlopen(request['url'],context=context,timeout=8) as response:
        response.read(65536)
        samples.append({'status':response.status,'state':response.headers.get('x-telemetry-state'),
                        'span_id':response.headers.get('x-span-id'),
                        'elapsed_ms':round((time.monotonic()-started)*1000,3)})
    if samples[-1]['state']=='full':
        break
print(json.dumps(samples))
'''


class TelemetryCampaign:
    telemetry_environment = 'p01-compose'

    def telemetry_snapshot(self, service, stage, acknowledge=False):
        raw = self.telemetry_exec(service, control(service, 'snapshot'))
        rows = records(raw, service, self.revision, self.telemetry_environment)
        # The canary covers query/header/cookie/tenant/baggage content. Actual
        # synthetic diagnostic tokens must also be absent from every sink.
        secrets_to_check = [b'P01_PRIVATE_SIGNAL_CANARY']
        secrets_to_check.extend(p.read_bytes().strip() for p in (self.runtime / 'secrets').glob('*health-token'))
        self.check('telemetry-redacted-owned-bounded-snapshot',
                   all(value not in raw for value in secrets_to_check),
                   {'stage': stage, 'service': service, 'bytes': len(raw), 'records': len(rows)})
        path = self.output / 'telemetry' / f'{stage}-{service}.jsonl'
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(raw)
        identity = hashlib.sha256(raw).hexdigest()
        self.report.setdefault('telemetry_snapshots', []).append(
            {'path': str(path.relative_to(self.output)), 'sha256': identity, 'bytes': len(raw),
             'records': len(rows), 'service': service, 'stage': stage})
        self.save()
        if acknowledge:
            self.telemetry_exec(service, control(service, 'acknowledge', identity))
        return raw, rows

    def measure_telemetry(self):
        for service in SERVICES:
            self.telemetry_snapshot(service, 'before-journey', acknowledge=True)
        trace, parent = secrets.token_hex(16), secrets.token_hex(8)
        headers = {'traceparent': f'00-{trace}-{parent}-01',
                   'Cookie': 'P01_PRIVATE_SIGNAL_CANARY', 'X-Tenant-Id': 'P01_PRIVATE_SIGNAL_CANARY',
                   'Baggage': 'P01_PRIVATE_SIGNAL_CANARY', 'X-Request-Id': 'P01_PRIVATE_SIGNAL_CANARY'}
        rows = []
        for service in SERVICES:
            status, observed = self.telemetry_request(service, '/health/dependencies?private=P01_PRIVATE_SIGNAL_CANARY', headers, True)
            self.check('telemetry-correlated-authorized-diagnostic', status == 200
                       and observed.get('x-trace-id') == trace and observed.get('x-telemetry-state') == 'buffered',
                       {'service': service, 'status': status, 'headers': observed})
            denied, invalid = self.telemetry_request(service, '/health/dependencies',
                         {'traceparent': f'00-{"0" * 32}-{parent}-01'}, False)
            self.check('telemetry-correlation-cannot-authorize', denied == 401
                       and invalid.get('x-trace-id') not in {trace, '0' * 32}, {'service': service, 'status': denied})
            reader, _ = self.telemetry_request(service, '/telemetry', headers, False)
            self.check('telemetry-public-reader-denied', reader == 404, {'service': service, 'status': reader})
            _, collected = self.telemetry_snapshot(service, 'journey', acknowledge=True)
            span = [row for row in collected if row['span_id'] == observed.get('x-span-id')]
            self.check('telemetry-response-log-span-correlation', len(span) == 1
                       and span[0]['trace_id'] == trace and span[0]['parent_span_id'] == parent
                       and span[0]['status'] == 200 and span[0]['route'] == '/health/dependencies',
                       {'service': service, 'span_id': observed.get('x-span-id')})
            rows.extend(collected)
        summary = export(rows, self.output / 'telemetry' / 'journey-signals')
        self.report['telemetry_journey'] = {**summary, 'trace_id': trace,
            'scope': 'Authorized operator diagnostic fan-out to seven actual services; no business workflow or native attempt.'}
        self.check('telemetry-three-signal-views-agree', summary['records'] == summary['spans']
                   == summary['response_count'] and summary['records'] >= 21 and summary['freshness'] == 'FRESH', summary)

        # Stop collection until each language implementation fills its real spool.
        # Request handling remains bounded, with explicit signal loss, never a
        # false implication that an absent telemetry sample means healthy.
        for service in ('governance', 'planning'):
            samples = self.telemetry_fill(service)
            self.check('telemetry-collector-outage-exhausts-real-buffer',
                       2 <= len(samples) <= 256 and samples[0]['state'] == 'buffered'
                       and samples[-1]['state'] == 'full' and all(s['status'] == 200 for s in samples),
                       {'service': service, 'requests': len(samples),
                        'max_response_ms': max(s['elapsed_ms'] for s in samples),
                        'last_state': samples[-1]['state']})
            raw, full_rows = self.telemetry_snapshot(service, 'collector-outage')
            self.check('telemetry-loss-is-explicit', samples[-1]['span_id'] not in {r['span_id'] for r in full_rows}
                       and len(raw) <= 65536 and len(full_rows) < len(samples), {'service': service})
            # An unavailable filesystem is distinct from saturation. Preserve and
            # restore the real bounded data even if a response assertion fails.
            self.telemetry_exec(service, ['sh', '-ec', 'mv /tmp/product-telemetry /tmp/product-telemetry-saved; touch /tmp/product-telemetry'])
            try:
                status, unavailable = self.telemetry_request(service, '/health/live', {}, False)
                self.check('telemetry-unavailable-explicit-with-liveness', status == 200
                           and unavailable.get('x-telemetry-state') == 'unavailable', {'service': service, 'status': status})
            finally:
                self.telemetry_exec(service, ['sh', '-ec', 'rm /tmp/product-telemetry; mv /tmp/product-telemetry-saved /tmp/product-telemetry'])
            # No collector acknowledgement until validation and retained bytes
            # above. Digest comparison rejects a stale acknowledgement.
            self.telemetry_exec(service, control(service, 'acknowledge', '0' * 64),
                                expected=255 if service in PHP_SERVICES else 1)
            unchanged, _ = self.telemetry_snapshot(service, 'stale-ack-denied')
            self.check('telemetry-stale-ack-preserves-buffer', unchanged == raw, {'service': service})
            self.telemetry_exec(service, control(service, 'acknowledge', hashlib.sha256(raw).hexdigest()))
            _, empty_rows = self.telemetry_snapshot(service, 'after-ack')
            self.check('telemetry-missing-is-not-healthy', freshness(empty_rows, time.time_ns() // 1000, 300000000) == 'MISSING', {'service': service})
            status, recovered = self.telemetry_request(service, '/health/live', headers, False)
            _, recovery_rows = self.telemetry_snapshot(service, 'collection-recovered', acknowledge=True)
            self.check('telemetry-collection-recovered', status == 200
                       and recovered.get('x-telemetry-state') == 'buffered'
                       and any(row['span_id'] == recovered.get('x-span-id') for row in recovery_rows), {'service': service})
        self.save()
