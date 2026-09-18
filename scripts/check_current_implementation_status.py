#!/usr/bin/env python3
"""Validate and render the current implementation-status overlay.

The historical Increment02-04 backlog is preserved byte-for-byte. This overlay reports
what the repository now implements without claiming live native qualification or
production authorization.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
STATUS_PATH = ROOT / 'sources/implementation/current_status.json'
MARKDOWN_PATH = ROOT / 'docs/implementation/current-status.md'
FORMAT = 'portable-hosting-current-implementation-status/1'
TOP_KEYS = {
    'format', 'status', 'historical_backlog_ref', 'historical_backlog_policy',
    'reviewed_baseline_commit', 'historical_backlog_git_blob_sha', 'items'
}
ITEM_KEYS = {
    'id', 'current_state', 'evidence_levels', 'evidence_refs', 'remaining_evidence',
    'native_target_contact', 'native_qualification', 'formal_authorization'
}
EVIDENCE_LEVELS = {
    'ENGINE_CI', 'OPEN_DECISION', 'PLANNING_ONLY', 'CANDIDATE_SOURCE',
    'LOCAL_PACKET_FIXTURE', 'LOCAL_PROTOCOL_FIXTURE', 'LOCAL_HTTPS_FIXTURE',
    'ENGINEERING_PRECHECK'
}
ID_PATTERN = re.compile(r'^I(0[1-9]|10)$')
STATE_PATTERN = re.compile(r'^[A-Z][A-Z0-9_]{2,127}_(OPEN|HOLD)$')
HEX40 = re.compile(r'^[0-9a-f]{40}$')


def strict_json(path: Path) -> dict:
    raw = path.read_bytes()
    if len(raw) > 1024 * 1024:
        raise ValueError('Current status source exceeds bounded size')

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate JSON property')
            result[key] = value
        return result

    value = json.loads(raw, object_pairs_hook=pairs)
    if not isinstance(value, dict):
        raise ValueError('Current status source must be an object')
    return value


def git_blob_sha(raw: bytes) -> str:
    header = f'blob {len(raw)}\0'.encode()
    return hashlib.sha1(header + raw).hexdigest()


def normalized_ref(value: object) -> str:
    if not isinstance(value, str) or not value or len(value) > 512:
        raise ValueError('Invalid repository evidence reference')
    path = Path(value)
    if path.is_absolute() or '..' in path.parts or '.git' in path.parts or '\\' in value or ':' in value:
        raise ValueError('Repository evidence reference must be normalized and relative')
    target = ROOT / path
    if not target.exists() or target.is_symlink():
        raise ValueError(f'Missing or symlinked repository evidence reference: {value}')
    return value


def unique_strings(value: object, label: str) -> list[str]:
    if not isinstance(value, list) or not value or len(value) > 64:
        raise ValueError(f'{label}: bounded nonempty list required')
    if any(not isinstance(item, str) or not item.strip() or len(item) > 1024 for item in value):
        raise ValueError(f'{label}: bounded nonempty strings required')
    if len(value) != len(set(value)):
        raise ValueError(f'{label}: duplicate entry')
    return value


def read_backlog(path: Path) -> tuple[list[dict], bytes]:
    raw = path.read_bytes()
    rows = list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
    required = {
        'id', 'work', 'status', 'increment02_delivery', 'remaining_evidence',
        'hold_point', 'increment03_delivery', 'increment04_delivery'
    }
    if not rows or set(rows[0]) != required:
        raise ValueError('Historical backlog columns differ from the preserved format')
    ids = [row['id'] for row in rows]
    if ids != [f'I{i:02d}' for i in range(1, 11)]:
        raise ValueError('Historical backlog must contain I01-I10 in original order')
    return rows, raw


def validate(source: dict) -> tuple[list[dict], dict]:
    if set(source) != TOP_KEYS:
        raise ValueError('Unexpected current-status source fields')
    if source['format'] != FORMAT:
        raise ValueError('Unsupported current-status format')
    if source['status'] != 'CURRENT_REPOSITORY_STATE_NOT_NATIVE_AUTHORIZATION':
        raise ValueError('Current-status authority boundary changed')
    if source['historical_backlog_policy'] != 'PRESERVE_ORIGINAL_INCREMENT_ROWS':
        raise ValueError('Historical backlog preservation policy changed')
    if not isinstance(source['reviewed_baseline_commit'], str) or not HEX40.fullmatch(source['reviewed_baseline_commit']):
        raise ValueError('Reviewed baseline must be an exact commit SHA')
    if not isinstance(source['historical_backlog_git_blob_sha'], str) or not HEX40.fullmatch(source['historical_backlog_git_blob_sha']):
        raise ValueError('Historical backlog Git blob SHA required')

    backlog_ref = normalized_ref(source['historical_backlog_ref'])
    rows, raw = read_backlog(ROOT / backlog_ref)
    if git_blob_sha(raw) != source['historical_backlog_git_blob_sha']:
        raise ValueError('Historical implementation backlog bytes changed')
    historical = {row['id']: row for row in rows}

    items = source['items']
    if not isinstance(items, list) or len(items) != 10:
        raise ValueError('Current status must contain exactly I01-I10')
    ids = [item.get('id') if isinstance(item, dict) else None for item in items]
    if ids != [f'I{i:02d}' for i in range(1, 11)]:
        raise ValueError('Current status items must be unique I01-I10 in order')

    for item in items:
        if set(item) != ITEM_KEYS:
            raise ValueError(f"{item.get('id', 'unknown')}: unexpected status fields")
        ident = item['id']
        if not isinstance(ident, str) or not ID_PATTERN.fullmatch(ident) or ident not in historical:
            raise ValueError('Unknown implementation backlog ID')
        state = item['current_state']
        if not isinstance(state, str) or not STATE_PATTERN.fullmatch(state):
            raise ValueError(f'{ident}: state must explicitly remain OPEN or HOLD')
        levels = unique_strings(item['evidence_levels'], f'{ident} evidence_levels')
        if not set(levels) <= EVIDENCE_LEVELS:
            raise ValueError(f'{ident}: unknown evidence level')
        for ref in unique_strings(item['evidence_refs'], f'{ident} evidence_refs'):
            normalized_ref(ref)
        unique_strings(item['remaining_evidence'], f'{ident} remaining_evidence')
        if item['native_target_contact'] != 'NOT_RUN':
            raise ValueError(f'{ident}: actual native target contact cannot be claimed by this overlay')
        if item['native_qualification'] != 'NOT_RUN':
            raise ValueError(f'{ident}: native qualification cannot be claimed by this overlay')
        if item['formal_authorization'] != 'NOT_ISSUED':
            raise ValueError(f'{ident}: formal authorization cannot be claimed by this overlay')

    summary = {
        'items': len(items),
        'open_or_hold_items': len(items),
        'native_target_contacted_items': 0,
        'native_qualified_items': 0,
        'authorized_items': 0,
        'historical_backlog_git_blob_sha': source['historical_backlog_git_blob_sha']
    }
    return rows, summary


def link(from_path: str, target: str, label: str | None = None) -> str:
    relative = os.path.relpath(target, Path(from_path).parent).replace(os.sep, '/')
    return f'[{label or target}]({relative})'


def code(value: str) -> str:
    return '<code>' + value + '</code>'


def render(source: dict, backlog_rows: list[dict]) -> str:
    path = 'docs/implementation/current-status.md'
    works = {row['id']: row['work'] for row in backlog_rows}
    lines = [
        '# Current implementation status',
        '',
        '**Purpose:** provide a maintained view of repository implementation progress without rewriting the preserved Increment02–04 backlog or turning local/CI evidence into native qualification.',
        '',
        'Reviewed baseline: ' + code(source['reviewed_baseline_commit']) + '.',
        '',
        'Historical source: ' + link(path, source['historical_backlog_ref'], 'preserved implementation backlog') + ' · Git blob ' + code(source['historical_backlog_git_blob_sha']) + '.',
        '',
        'Every item below remains **NOT_RUN** for actual native target contact and native qualification, and **NOT_ISSUED** for formal authorization. A repository implementation, engine test, or local fixture is therefore not a production-ready service claim.',
        '',
        '## Summary',
        '',
        '| ID | Original work item | Current repository state | Evidence level | Native / authorization |',
        '| --- | --- | --- | --- | --- |'
    ]
    for item in source['items']:
        levels = ', '.join(code(x) for x in item['evidence_levels'])
        lines.append(
            f"| {item['id']} | {works[item['id']]} | {code(item['current_state'])} | {levels} | native contact **NOT_RUN**; qualification **NOT_RUN**; authorization **NOT_ISSUED** |"
        )

    lines += [
        '',
        '## Interpretation',
        '',
        'The historical CSV records what earlier increments reported. This page is the current overlay. It may advance when repository implementation or bounded local evidence advances, but it must not relabel historical results or close native/site hold points without the required external evidence.',
        ''
    ]

    for item in source['items']:
        lines += [
            f"## {item['id']} — {works[item['id']]}",
            '',
            'Current state: ' + code(item['current_state']) + '.',
            '',
            'Evidence levels: ' + ' · '.join(code(x) for x in item['evidence_levels']) + '.',
            '',
            'Repository evidence:'
        ]
        for ref in item['evidence_refs']:
            lines.append(f"- {link(path, ref)}")
        lines += ['', 'Remaining evidence:']
        for remaining in item['remaining_evidence']:
            lines.append(f'- {remaining}')
        lines += [
            '',
            'Native target contact: **NOT_RUN** · Native qualification: **NOT_RUN** · Formal authorization: **NOT_ISSUED**.',
            ''
        ]

    lines += [
        '## Maintenance rule',
        '',
        'Update ' + code('sources/implementation/current_status.json') + ' first. The checker validates I01–I10, repository evidence paths, the preserved historical backlog blob, explicit OPEN/HOLD state and the non-authorization boundary. Regenerate or update this page to match that source; do not edit the historical increment rows to make current progress look older.',
        '',
        link(path, 'docs/NEXT_WORK.md', 'Next work') + ' · ' + link(path, 'docs/implementation/code-map.md', 'Implementation map') + ' · ' + link(path, 'docs/implementation/native-reference/README.md', 'Native reference commissioning'),
        ''
    ]
    return '\n'.join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-markdown', action='store_true')
    args = parser.parse_args()
    try:
        source = strict_json(STATUS_PATH)
        backlog, summary = validate(source)
        expected = render(source, backlog)
        if args.write_markdown:
            MARKDOWN_PATH.write_text(expected)
        elif not MARKDOWN_PATH.is_file() or MARKDOWN_PATH.read_text() != expected:
            raise ValueError('Current-status Markdown differs from its machine-readable source')
        print(json.dumps({
            'status': 'PASSED_CURRENT_IMPLEMENTATION_STATUS',
            **summary,
            'historical_backlog_preserved': True,
            'native_qualification': 'NOT_RUN',
            'formal_authorization': 'NOT_ISSUED'
        }, indent=2))
        return 0
    except (ValueError, OSError, TypeError, KeyError, json.JSONDecodeError, csv.Error) as exc:
        print(json.dumps({'status': 'FAILED_CURRENT_IMPLEMENTATION_STATUS', 'reason': str(exc)}, indent=2))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
