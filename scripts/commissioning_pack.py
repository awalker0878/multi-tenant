#!/usr/bin/env python3
"""Check a repository planning kit or export NEW unfilled local campaign worksheets.

No API calls, subprocesses, discovery, credentials, deployment or approval handling.
This checks planning structure, not an actual environment or completed evidence.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PLAN = 'sources/commissioning/native_reference_plan.json'
FAMILIES = 'sources/assurance/verification_families.json'
IDS = {f'W14-{n:02d}' for n in range(1, 13)}
PHASES = {f'B14-{n:02d}' for n in range(1, 9)}
PACKAGES = {f'P{n}' for n in range(7)} | {'G0', 'G1', 'G2', 'G3', 'G4-initial', 'G4-recurring'}
MAX_BYTES = 1024 * 1024
# Required markers from the source B14 stage responsibilities. They are planning
# dependencies, not approval objects or a native execution scheduler.
STAGE_PACKAGES = {
    'B14-01': {'G0'}, 'B14-02': {'P0', 'P1', 'G1'},
    'B14-03': {'P2', 'P3'}, 'B14-04': {'P4', 'P5'},
    'B14-05': {'G2'}, 'B14-06': {'G4-initial'},
    'B14-07': {'P4', 'P5', 'G3'}, 'B14-08': {'P6', 'G4-recurring'},
}
ACTUAL_OBSERVATION_FIELDS = (
    'attempt_id', 'platform_tuple_ref', 'topology_generation', 'family', 'placement',
    'direction', 'operation', 'observer_identity_ref', 'procedure_variant',
    'native_resources_ref', 'started_utc', 'finished_utc', 'control_result_ref',
    'reason', 'artifact_ref', 'artifact_sha256', 'reviewer',
)


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 4096:
        raise ValueError(f'{label}: nonempty bounded text required')
    if any(ord(c) < 32 for c in value):
        raise ValueError(f'{label}: control characters are not supported')
    return value


def shape(value: Any, keys: set[str], label: str) -> dict:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(f'{label}: exact fields required')
    return value


def unique_list(value: Any, label: str, minimum: int = 1) -> list[str]:
    if not isinstance(value, list) or not minimum <= len(value) <= 100:
        raise ValueError(f'{label}: bounded list required')
    for v in value:
        text(v, label)
    if len(value) != len(set(value)):
        raise ValueError(f'{label}: duplicate entry')
    return value


def safe_source(root: Path, relative: Any) -> Path:
    text(relative, 'source path')
    p = PurePosixPath(relative)
    if (p.is_absolute() or str(p) != relative or '\\' in relative or ':' in relative
            or any(x in ('.', '..', '.git') for x in p.parts)):
        raise ValueError('Only normalized repository-relative source paths are supported')
    result = root.joinpath(*p.parts)
    if not result.is_relative_to(root):
        raise ValueError('Source escapes repository')
    for candidate in (result, *result.parents):
        if candidate == root.parent:
            break
        if candidate.is_symlink():
            raise ValueError('Source symlink is not supported')
    if not result.is_file():
        raise ValueError(f'Missing source: {relative}')
    return result


def bounded_bytes(path: Path) -> bytes:
    with path.open('rb') as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError('Source exceeds size limit')
    return raw


def load_json(path: Path) -> tuple[dict, bytes]:
    raw = bounded_bytes(path)

    def pairs(items):
        result = {}
        for k, v in items:
            if k in result:
                raise ValueError('Duplicate JSON property')
            result[k] = v
        return result

    def nonfinite(_):
        raise ValueError('Nonfinite number is not permitted')

    try:
        result = json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite)
    except (UnicodeError, RecursionError) as exc:
        raise ValueError('Invalid JSON encoding or nesting') from exc
    if not isinstance(result, dict):
        raise ValueError('JSON object required')
    return result, raw


def validate(plan: dict) -> None:
    shape(plan, {'format', 'status', 'basis_commit', 'scope', 'source_refs', 'inputs',
                 'work_packages', 'observations', 'cleanup_step'}, 'planning package')
    if plan['format'] != 'native-reference-planning/1' or plan['status'] != 'PROPOSED_NOT_EXECUTED':
        raise ValueError('This format represents a proposed unexecuted planning package only')
    if not isinstance(plan['basis_commit'], str) or not re.fullmatch('[0-9a-f]{40}', plan['basis_commit']):
        raise ValueError('Exact source-basis commit required')
    scope = shape(plan['scope'], {'solution', 'topology', 'families', 'platform',
                                 'public_ingress', 'internet_egress', 'production_authority'}, 'scope')
    if (scope['families'] != 'SELECT_AT_SITE_REVIEW' or scope['platform'] != 'NOT_SELECTED'
            or scope['production_authority'] != 'NOT_ASSESSED'
            or scope['public_ingress'] is not False or scope['internet_egress'] is not False):
        raise ValueError('The reusable internal kit cannot select a site, expose traffic or claim authority')
    for key in ('solution', 'topology'):
        text(scope[key], key)
    refs = set(unique_list(plan['source_refs'], 'source_refs'))
    if scope['solution'] not in refs or FAMILIES not in refs:
        raise ValueError('Maintained solution and existing verification family source required')
    inputs = plan['inputs']
    if not isinstance(inputs, list) or not 1 <= len(inputs) <= 100:
        raise ValueError('Input schedule is required')
    inputs_by_id = {}
    for item in inputs:
        shape(item, {'id', 'title', 'owner_role', 'question', 'hold_point', 'source_refs'}, 'input')
        for key in ('id', 'title', 'owner_role', 'question', 'hold_point'):
            text(item[key], key)
        if not re.fullmatch('[A-Z][A-Z0-9_-]{1,31}', item['id']) or item['id'] in inputs_by_id:
            raise ValueError('Input identities must be bounded and unique')
        if not set(unique_list(item['source_refs'], 'input source_refs')) <= refs:
            raise ValueError('Input references an undeclared source')
        inputs_by_id[item['id']] = item
    steps = plan['work_packages']
    if not isinstance(steps, list) or not 1 <= len(steps) <= 30:
        raise ValueError('Work packages are required')
    steps_by_id = {}
    for step in steps:
        shape(step, {'id', 'source_stage', 'packages', 'title', 'depends_on', 'input_refs',
                     'deliverable', 'hold_point'}, 'work package')
        for key in ('id', 'source_stage', 'title', 'deliverable', 'hold_point'):
            text(step[key], key)
        if not re.fullmatch('NC[0-9]{2}', step['id']) or step['id'] in steps_by_id:
            raise ValueError('Work package identity must be unique')
        if step['source_stage'] not in PHASES:
            raise ValueError('Unknown original B14 phase')
        if not set(unique_list(step['packages'], 'packages')) <= PACKAGES:
            raise ValueError('Unknown work package or decision type')
        if not set(unique_list(step['input_refs'], 'input_refs')) <= inputs_by_id.keys():
            raise ValueError('Work package references an unknown input')
        unique_list(step['depends_on'], 'depends_on', 0)
        steps_by_id[step['id']] = step
    visited = set()
    active = set()

    def visit(key):
        if key not in steps_by_id:
            raise ValueError('Unknown work-package dependency')
        if key in active:
            raise ValueError('Cyclic work-package dependencies')
        if key not in visited:
            active.add(key)
            for parent in steps_by_id[key]['depends_on']:
                visit(parent)
            active.remove(key)
            visited.add(key)

    for key in steps_by_id:
        visit(key)

    ancestor_cache = {}

    def ancestors(key):
        if key in ancestor_cache:
            return ancestor_cache[key]
        result = set()
        for parent in steps_by_id[key]['depends_on']:
            result.add(parent)
            result.update(ancestors(parent))
        ancestor_cache[key] = result
        return result

    cleanup = text(plan['cleanup_step'], 'cleanup_step')
    if cleanup not in steps_by_id or 'P6' not in steps_by_id[cleanup]['packages']:
        raise ValueError('A distinct owner-scoped cleanup work package is required')
    cleanup_packages = set(steps_by_id[cleanup]['packages']) | {
        p for key in ancestors(cleanup) for p in steps_by_id[key]['packages']}
    if cleanup_packages & {'G2', 'G3', 'G4-initial', 'G4-recurring'}:
        raise ValueError('Failed-fixture cleanup cannot depend on successful qualification or production')
    if {s['source_stage'] for s in steps} != PHASES:
        raise ValueError('Every original B14 phase must be represented')
    for stage, required in STAGE_PACKAGES.items():
        assigned = {p for step in steps if step['source_stage'] == stage for p in step['packages']}
        if not required <= assigned:
            raise ValueError('Original stage responsibilities or acceptance marker missing')
    cleanup_prior = {p for key in ancestors(cleanup) for p in steps_by_id[key]['packages']}
    if cleanup_prior != {'G0'}:
        raise ValueError('Failed-build cleanup must not depend on completed installation or testing')
    for step in steps:
        prior = {p for key in ancestors(step['id']) for p in steps_by_id[key]['packages']}
        if 'G3' in step['packages'] and not {'G0', 'G1', 'G2', 'G4-initial'} <= prior:
            raise ValueError('Production review must depend on applicable initial readiness, not later recurring G4')
        if step['source_stage'] == 'B14-04' and 'G2' in prior:
            raise ValueError('First restricted qualification must not require its own completed G2')
    observed = set()
    for row in plan['observations'] if isinstance(plan['observations'], list) else []:
        shape(row, {'assertion_id', 'title', 'owner_role', 'input_refs', 'control',
                    'evidence_to_collect', 'safe_stop', 'execution_status', 'source_ref'}, 'observation')
        for key in ('assertion_id', 'title', 'owner_role', 'control', 'evidence_to_collect', 'safe_stop', 'source_ref'):
            text(row[key], key)
        if row['assertion_id'] in observed or row['assertion_id'] not in IDS:
            raise ValueError('Duplicate or unknown W14 observation')
        if row['execution_status'] != 'NOT_RUN' or row['source_ref'] not in refs:
            raise ValueError('Observation planning must not assert an executed result')
        if not set(unique_list(row['input_refs'], 'observation inputs')) <= inputs_by_id.keys():
            raise ValueError('Observation references unknown input')
        observed.add(row['assertion_id'])
    if observed != IDS:
        raise ValueError('All twelve existing W14 assertions must be planned, not renamed')
    referenced = {k for step in steps for k in step['input_refs']} | {
        k for row in plan['observations'] for k in row['input_refs']}
    if referenced != inputs_by_id.keys():
        raise ValueError('Every requested input must serve a work package or observation')


def sources(root: Path, plan: dict) -> tuple[dict, dict]:
    fingerprints = {}
    for rel in set(plan['source_refs']) | {plan['scope']['topology']}:
        fingerprints[rel] = digest(bounded_bytes(safe_source(root, rel)))
    families, _ = load_json(safe_source(root, FAMILIES))
    if not isinstance(families.get('supplemental_mappings'), list):
        raise ValueError('Existing verification-family mapping is missing')
    rows = [r for r in families['supplemental_mappings'] if isinstance(r, dict) and r.get('family') == 'W14']
    if len(rows) != 12 or {r.get('id') for r in rows} != IDS:
        raise ValueError('Original W14 mapping must contain twelve unique assertions')
    originals = {}
    for row in rows:
        if row.get('execution_status') != 'not-run':
            raise ValueError('Repository specification is not fresh observation evidence')
        rel = row.get('source_path')
        raw = bounded_bytes(safe_source(root, rel))
        fingerprints[rel] = digest(raw)
        table = list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
        matches = [r for r in table if r.get('assertion', '').split('/', 1)[0].strip() == row['id']]
        if len(matches) != 1 or row.get('original_record') != matches[0]:
            raise ValueError('W14 mapping differs from the preserved original register')
        originals[row['id']] = matches[0]
    return originals, fingerprints


def inspect(root: Path = ROOT) -> tuple[dict, dict, dict]:
    root = root.absolute()
    plan, raw = load_json(safe_source(root, PLAN))
    validate(plan)
    originals, fingerprints = sources(root, plan)
    fingerprints[PLAN] = digest(raw)
    report = {'status': 'PLANNING_PACKAGE_CONSISTENT_NOT_EXECUTED',
              'inputs': len(plan['inputs']), 'work_packages': len(plan['work_packages']),
              'w14_run_sheets': len(plan['observations']), 'source_sha256': fingerprints,
              'exporter_sha256': digest(bounded_bytes(safe_source(root, 'scripts/commissioning_pack.py'))),
              'limits': ['Document structure and source associations only; no semantic design approval',
                         'No selected site/platform, target contact, native tests or operating authority'],
              'may_apply': False, 'may_delete': False, 'may_activate': False}
    return plan, originals, report


def cell(value: Any) -> str:
    value = str(value)
    # Formula protection in spreadsheet viewers; no effect on ordinary source prose.
    return "'" + value if value.lstrip().startswith(('=', '+', '-', '@')) else value


def csv_bytes(headers: list[str], rows: list[list]) -> bytes:
    stream = io.StringIO(newline='')
    writer = csv.writer(stream, lineterminator='\n')
    writer.writerow(headers)
    writer.writerows([[cell(v) for v in row] for row in rows])
    return stream.getvalue().encode('utf-8')


def worksheets(plan: dict, originals: dict) -> dict[str, bytes]:
    inputs = [[r['id'], r['title'], r['owner_role'], r['question'], r['hold_point'],
               '', '', 'UNREVIEWED'] for r in plan['inputs']]
    packages = [[r['id'], r['source_stage'], ';'.join(r['packages']), r['title'],
                 ';'.join(r['depends_on']), ';'.join(r['input_refs']), r['deliverable'],
                 r['hold_point'], '', 'NOT_RUN'] for r in plan['work_packages']]
    observation_headers = [
        'assertion_id', 'original_assertion', 'original_observation', 'original_procedures',
        'responsible_role', 'control_to_demonstrate', 'evidence_to_collect', 'safe_stop',
        *ACTUAL_OBSERVATION_FIELDS, 'result',
    ]
    observations = []
    for row in plan['observations']:
        original = originals[row['assertion_id']]
        values = dict.fromkeys(observation_headers, '')
        values.update(assertion_id=row['assertion_id'], original_assertion=original['assertion'],
                      original_observation=original['observation'],
                      original_procedures=original['mapped_procedures_and_status'],
                      responsible_role=row['owner_role'], control_to_demonstrate=row['control'],
                      evidence_to_collect=row['evidence_to_collect'], safe_stop=row['safe_stop'],
                      result='NOT_RUN')
        observations.append([values[key] for key in observation_headers])
    return {
        'engineering-inputs.csv': csv_bytes(
            ['input_id', 'subject', 'responsible_role', 'question', 'hold_point',
             'controlled_record_reference', 'assigned_owner', 'review_state'], inputs),
        'work-package-runs.csv': csv_bytes(
            ['step_id', 'source_stage', 'packages', 'title', 'planning_prerequisites',
             'required_inputs', 'planned_deliverable', 'hold_point', 'actual_change_reference', 'result'], packages),
        'observation-attempts.csv': csv_bytes(observation_headers, observations),
    }


def write_new(output: Path, payloads: dict[str, bytes], report: dict) -> None:
    if not output.is_absolute():
        raise ValueError('Use an explicit absolute path in the approved local evidence workspace')
    for candidate in (output, *output.parents):
        if candidate.is_symlink():
            raise ValueError('Output path must not traverse symlinks')
    if not output.parent.is_dir():
        raise ValueError('Output parent must already exist and be trusted')
    if output.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError('Keep filled native campaign material outside the source repository')
    if set(payloads) != {'engineering-inputs.csv', 'work-package-runs.csv', 'observation-attempts.csv'}:
        raise ValueError('Unexpected worksheet output set')
    output.mkdir(mode=0o700, exist_ok=False)

    def private_write(name, data):
        fd = os.open(output / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())

    manifest = {'status': 'STARTED_INCOMPLETE', 'created_at': datetime.now(timezone.utc).isoformat(),
                'planning_source_sha256': report['source_sha256'],
                'exporter_sha256': report['exporter_sha256'],
                'native_execution': 'NOT_RUN', 'authority': 'NOT_ASSESSED',
                'may_apply': False, 'may_delete': False, 'may_activate': False}
    private_write('manifest.json', (json.dumps(manifest, indent=2) + '\n').encode())
    for name, data in payloads.items():
        private_write(name, data)
    private_write('README.txt', b'UNFILLED PLANNING WORKSHEETS - NOT EVIDENCE OR AUTHORIZATION\n'
                  b'Use a separate attempt row per family, placement, direction, variant and run.\n'
                  b'Keep real endpoint values and credentials in the approved controlled systems.\n'
                  b'Original source assertions are not executed results. Populate artifact references\n'
                  b'and actual observations only after separately authorized native work.\n'
                  b'An unknown or unsuccessful positive control makes a negative result inconclusive.\n'
                  b'This export does not schedule, execute, approve or validate that native work.\n')
    manifest.update(status='DRAFT_ONLY_NOT_EVIDENCE', file_sha256={k: digest(v) for k, v in payloads.items()})
    private_write('.manifest-complete', (json.dumps(manifest, indent=2) + '\n').encode())
    os.replace(output / '.manifest-complete', output / 'manifest.json')


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('operation', choices=('check', 'draft'))
    p.add_argument('--output', type=Path)
    args = p.parse_args()
    try:
        if (args.operation == 'draft') != (args.output is not None):
            raise ValueError('Only draft requires --output; check writes no files')
        plan, originals, report = inspect()
        if args.operation == 'draft':
            write_new(args.output, worksheets(plan, originals), report)
            report['status'] = 'DRAFT_ONLY_NOT_EVIDENCE'
        print(json.dumps(report, indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError, csv.Error) as exc:
        # Do not echo user-supplied source values or actual evidence paths.
        print(json.dumps({'status': 'INVALID_OR_INCOMPLETE_PLANNING_PACKAGE',
                          'error_type': type(exc).__name__, 'native_execution': 'NOT_RUN',
                          'may_apply': False, 'may_delete': False, 'may_activate': False}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
