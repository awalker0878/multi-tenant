#!/usr/bin/env python3
"""Validate site/cell/service-class capacity envelopes and fail closed for admission.

This is an engineering evidence layer for PLACE-001, SVCM-001/002 and CAP-001/002.
It does not select a site, reserve resources, allocate addresses, mutate capacity,
contact infrastructure, or issue production authorization.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import check_platform_qualification as qualification

INDEX = ROOT / 'sources/capabilities/site_service_capacity_index.json'
FORMAT = 'portable-hosting-site-service-capacity/1'
STATUS = 'ENGINEERING_CAPACITY_RECORDS_NOT_RESERVATION_AUTHORITY'
PLATFORMS = {'nutanix', 'vmware-nsx', 'openstack'}
ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.:-]{1,191}$')
SHA = re.compile(r'^[0-9a-f]{64}$')
INDEX_KEYS = {'format', 'status', 'reviewed_source_revision', 'records'}
RECORD_KEYS = {
    'id', 'state', 'site_id', 'cell_id', 'service_class_id', 'platform',
    'product_tuple_id', 'qualification_record_id', 'assurance_profiles',
    'profile_refs', 'failure_model', 'capacity_measured_at', 'capacity_expires_at',
    'dimensions', 'owners', 'source_refs'
}
PROFILE_KEYS = {
    'co_residency', 'compute', 'storage', 'network', 'security_edge',
    'availability', 'recovery', 'location', 'key', 'backup'
}
FAILURE_KEYS = {'id', 'description', 'evidence_ref'}
DIMENSION_KEYS = {
    'id', 'unit', 'measured_surviving_capacity', 'operational_reserve',
    'existing_commitment', 'unavailable_capacity', 'procured', 'received',
    'staged', 'commissioned', 'reserved', 'consumed', 'evidence_ref'
}
OWNER_KEYS = {'capacity_owner_role', 'platform_owner_role', 'service_owner_role'}


def bounded(value, label, limit=512):
    if (not isinstance(value, str) or not value.strip() or len(value) > limit
            or any(ord(c) < 32 or ord(c) == 127 for c in value)):
        raise ValueError(f'{label}: bounded nonempty text required')
    return value


def identifier(value, label='identifier'):
    bounded(value, label, 192)
    if not ID.fullmatch(value):
        raise ValueError(f'{label}: invalid identifier')
    return value


def unique_strings(value, label, *, allow_empty=False, maximum=64):
    if not isinstance(value, list) or len(value) > maximum or (not allow_empty and not value):
        raise ValueError(f'{label}: bounded list required')
    if any(not isinstance(x, str) or not x.strip() for x in value):
        raise ValueError(f'{label}: nonempty strings required')
    if len(value) != len(set(value)):
        raise ValueError(f'{label}: duplicates not allowed')
    return value


def instant(value, label):
    bounded(value, label, 64)
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        raise ValueError(f'{label}: timezone required')
    return dt.astimezone(timezone.utc)


def number(value, label):
    if not isinstance(value, str) or not value or len(value) > 64:
        raise ValueError(f'{label}: decimal string required')
    try:
        n = Decimal(value)
    except InvalidOperation:
        raise ValueError(f'{label}: invalid decimal') from None
    if not n.is_finite() or n < 0:
        raise ValueError(f'{label}: nonnegative finite decimal required')
    return n


def repository_ref(value, root=ROOT):
    bounded(value, 'repository reference')
    path = Path(value)
    if path.is_absolute() or '..' in path.parts or '\\' in value or ':' in value:
        raise ValueError('Repository reference must be normalized and relative')
    if not (root / path).exists():
        raise ValueError(f'Repository reference does not exist: {value}')
    return value


def load(path: Path = INDEX):
    with path.open('rb') as stream:
        raw = stream.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise ValueError('Site capacity index exceeds bounded size')
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate JSON property')
            result[key] = value
        return result
    def reject(_):
        raise ValueError('Non-finite JSON number')
    value = json.loads(raw, object_pairs_hook=pairs, parse_constant=reject)
    if not isinstance(value, dict):
        raise ValueError('Site capacity index must be a JSON object')
    return value


def dimension_available(dimension):
    surviving = number(dimension['measured_surviving_capacity'], 'measured_surviving_capacity')
    reserve = number(dimension['operational_reserve'], 'operational_reserve')
    commitment = number(dimension['existing_commitment'], 'existing_commitment')
    unavailable = number(dimension['unavailable_capacity'], 'unavailable_capacity')
    return surviving - reserve - commitment - unavailable


def validate_record(record, *, qindex, provenance_index=None, as_of, root=ROOT):
    if not isinstance(record, dict) or set(record) != RECORD_KEYS:
        raise ValueError('Site capacity record has unexpected or missing fields')
    if record['state'] != 'CURRENT_COMMISSIONED':
        raise ValueError('Only CURRENT_COMMISSIONED records belong in the active index')
    for key in ('id', 'site_id', 'cell_id', 'service_class_id', 'product_tuple_id',
                'qualification_record_id'):
        identifier(record[key], key)
    if record['platform'] not in PLATFORMS:
        raise ValueError('Unknown platform family')

    qsummary = qualification.validate(qindex, as_of=as_of, root=root, provenance_index=provenance_index)
    matches = [
        item for item in qsummary['records']
        if item['id'] == record['qualification_record_id']
        and item['platform'] == record['platform']
        and item['product_tuple_id'] == record['product_tuple_id']
    ]
    if len(matches) != 1:
        raise ValueError('Site service class is not bound to one current exact-tuple qualification record')
    qrecord = matches[0]

    assurance = unique_strings(record['assurance_profiles'], 'assurance_profiles', allow_empty=True)
    if not set(assurance) <= set(qrecord['assurance_profiles']):
        raise ValueError('Site service class advertises assurance outside the current qualification record')

    profiles = record['profile_refs']
    if not isinstance(profiles, dict) or set(profiles) != PROFILE_KEYS:
        raise ValueError('Exact service/placement profile references are required')
    for key, value in profiles.items():
        bounded(value, f'profile_refs.{key}')

    failure = record['failure_model']
    if not isinstance(failure, dict) or set(failure) != FAILURE_KEYS:
        raise ValueError('Failure-model record required')
    identifier(failure['id'], 'failure_model.id')
    bounded(failure['description'], 'failure_model.description', 1024)
    bounded(failure['evidence_ref'], 'failure_model.evidence_ref')

    measured = instant(record['capacity_measured_at'], 'capacity_measured_at')
    expires = instant(record['capacity_expires_at'], 'capacity_expires_at')
    if measured > as_of or expires <= measured or as_of >= expires:
        raise ValueError('Capacity measurement is future-dated, reversed or expired')

    dimensions = record['dimensions']
    if not isinstance(dimensions, list) or not dimensions or len(dimensions) > 128:
        raise ValueError('At least one bounded capacity dimension is required')
    seen = set()
    normalized = []
    for dim in dimensions:
        if not isinstance(dim, dict) or set(dim) != DIMENSION_KEYS:
            raise ValueError('Capacity dimension shape invalid')
        identifier(dim['id'], 'dimension.id')
        if dim['id'] in seen:
            raise ValueError('Duplicate capacity dimension')
        seen.add(dim['id'])
        bounded(dim['unit'], 'dimension.unit', 64)
        bounded(dim['evidence_ref'], 'dimension.evidence_ref')
        values = {key: number(dim[key], key) for key in (
            'measured_surviving_capacity', 'operational_reserve', 'existing_commitment',
            'unavailable_capacity', 'procured', 'received', 'staged', 'commissioned',
            'reserved', 'consumed'
        )}
        # Procured/received/staged/commissioned are retained as separately
        # reported lifecycle states. The architecture does not define them as a
        # cumulative monotonic arithmetic chain, so this generic checker does not
        # invent one. Only the explicit admission commitment is reconciled here.
        if max(values['reserved'], values['consumed']) > values['existing_commitment']:
            raise ValueError('Existing commitment must cover reserved and consumed observations without double-counting them')
        available = dimension_available(dim)
        if available < 0:
            raise ValueError('Capacity envelope is already overcommitted under its failure model')
        normalized.append({
            'id': dim['id'],
            'unit': dim['unit'],
            'available_after_failure_and_reserve': str(available.normalize()),
            'evidence_ref': dim['evidence_ref']
        })

    owners = record['owners']
    if not isinstance(owners, dict) or set(owners) != OWNER_KEYS:
        raise ValueError('Capacity/service owner fields required')
    for key in OWNER_KEYS:
        bounded(owners[key], key)

    refs = unique_strings(record['source_refs'], 'source_refs')
    for ref in refs:
        repository_ref(ref, root)

    return {
        'id': record['id'],
        'site_id': record['site_id'],
        'cell_id': record['cell_id'],
        'service_class_id': record['service_class_id'],
        'platform': record['platform'],
        'product_tuple_id': record['product_tuple_id'],
        'qualification_record_id': record['qualification_record_id'],
        'assurance_profiles': sorted(assurance),
        'profile_refs': dict(profiles),
        'failure_model_id': failure['id'],
        'capacity_expires_at': expires.isoformat(),
        'dimensions': normalized
    }


def validate(index, *, qindex=None, provenance_index=None, as_of=None, root=ROOT):
    if as_of is None:
        as_of = datetime.now(timezone.utc)
    if not isinstance(as_of, datetime) or as_of.tzinfo is None:
        raise ValueError('Timezone-aware as_of required')
    as_of = as_of.astimezone(timezone.utc)
    if qindex is None:
        qindex = qualification.load()
    if set(index) != INDEX_KEYS:
        raise ValueError('Unexpected site capacity index fields')
    if index['format'] != FORMAT or index['status'] != STATUS:
        raise ValueError('Unsupported site capacity format or authority boundary')
    revision = index['reviewed_source_revision']
    if not isinstance(revision, str) or not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('Reviewed source revision must be an exact Git SHA')
    if not isinstance(index['records'], list) or len(index['records']) > 256:
        raise ValueError('Site capacity records must be a bounded list')

    seen = set()
    records = []
    service_keys = set()
    for record in index['records']:
        checked = validate_record(record, qindex=qindex, provenance_index=provenance_index, as_of=as_of, root=root)
        if checked['id'] in seen:
            raise ValueError('Duplicate site capacity record ID')
        seen.add(checked['id'])
        key = (checked['site_id'], checked['cell_id'], checked['service_class_id'])
        if key in service_keys:
            raise ValueError('Duplicate active site/cell/service-class envelope')
        service_keys.add(key)
        records.append(checked)
    return {
        'current_service_envelopes': len(records),
        'sites': sorted({x['site_id'] for x in records}),
        'cells': sorted({x['cell_id'] for x in records}),
        'service_classes': sorted({x['service_class_id'] for x in records}),
        'records': records
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--index', type=Path, default=INDEX)
    parser.add_argument('--as-of', help='ISO-8601 review instant; defaults to current UTC')
    args = parser.parse_args()
    try:
        as_of = instant(args.as_of, 'as_of') if args.as_of else datetime.now(timezone.utc)
        summary = validate(load(args.index), as_of=as_of)
        result = {
            'status': 'PASSED_SITE_SERVICE_CAPACITY_INDEX',
            'as_of': as_of.isoformat(),
            **summary,
            'may_select_site': False,
            'may_reserve_capacity': False,
            'may_allocate': False,
            'may_apply': False,
            'may_activate': False,
            'limits': [
                'Engineering inventory only; no site selection or reservation is created.',
                'Surviving capacity is evaluated under the recorded failure model and operational reserve.',
                'Quota, address, storage, key, recovery and shared-service dependencies remain explicit admission inputs.'
            ]
        }
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, OSError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({
            'status': 'FAILED_SITE_SERVICE_CAPACITY_INDEX',
            'reason': str(exc),
            'may_select_site': False,
            'may_reserve_capacity': False,
            'may_allocate': False,
            'may_apply': False,
            'may_activate': False
        }, indent=2))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
