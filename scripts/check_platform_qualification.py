#!/usr/bin/env python3
"""Validate time-bounded native PlatformProfile qualification dossiers.

This is an engineering evidence check for QUAL-001/ASSUR-003. It does not contact
platforms, select sites, reserve capacity, deploy resources, or issue production
authorization. A current record can support registry qualification claims only for
its exact installed tuple and explicitly qualified capabilities.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import check_version_source_provenance as provenance

INDEX = ROOT / 'sources/capabilities/qualification_index.json'
FORMAT = 'portable-hosting-native-qualification-index/1'
STATUS = 'ENGINEERING_QUALIFICATION_RECORDS_NOT_PRODUCTION_AUTHORITY'
CAPABILITIES = {
    'network_domain', 'ipv4', 'ipv6', 'distributed_firewall', 'gateway_policy',
    'dynamic_routing', 'service_insertion', 'native_load_balancer',
    'dedicated_edge_context', 'audit_logging'
}
PLATFORMS = {'nutanix', 'vmware-nsx', 'openstack'}
ID = re.compile(r'^[A-Z][A-Z0-9_.-]{2,127}$')
TUPLE_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.:-]{2,191}$')
SHA = re.compile(r'^[0-9a-f]{64}$')
RECORD_KEYS = {
    'id', 'state', 'platform', 'product_tuple_id', 'product_tuple',
    'assurance_profiles', 'qualified_capabilities', 'applicable_test_sets',
    'tested_limits', 'evidence', 'approval', 'owners', 'exclusions', 'source_refs'
}
TUPLE_KEYS = {
    'product', 'product_version', 'api', 'api_version', 'automation_providers',
    'hardware_profile_ref', 'feature_licenses'
}
LIMIT_KEYS = {'name', 'observed_bound', 'unit', 'evidence_ref'}
EVIDENCE_KEYS = {'ref', 'sha256', 'observed_at', 'expires_at', 'test_set'}
APPROVAL_KEYS = {'authority_role', 'decision_ref', 'approved_at', 'expires_at'}
OWNER_KEYS = {'platform_engineering_role', 'security_authority_role'}


def bounded(value, label, limit=512):
    if (not isinstance(value, str) or not value.strip() or len(value) > limit
            or any(ord(c) < 32 or ord(c) == 127 for c in value)):
        raise ValueError(f'{label}: bounded nonempty text required')
    return value


def unique_strings(value, label, *, allow_empty=False, maximum=128):
    if not isinstance(value, list) or len(value) > maximum or (not allow_empty and not value):
        raise ValueError(f'{label}: bounded list required')
    if any(not isinstance(x, str) or not x.strip() for x in value):
        raise ValueError(f'{label}: nonempty strings required')
    if len(value) != len(set(value)):
        raise ValueError(f'{label}: duplicate values not allowed')
    return value


def instant(value, label):
    bounded(value, label, 64)
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        raise ValueError(f'{label}: timezone required')
    return dt.astimezone(timezone.utc)


def repository_ref(value, root=ROOT):
    bounded(value, 'repository reference')
    p = Path(value)
    if p.is_absolute() or '..' in p.parts or '\\' in value or ':' in value:
        raise ValueError('Repository reference must be normalized and relative')
    if not (root / p).exists():
        raise ValueError(f'Repository reference does not exist: {value}')
    return value


def load(path: Path = INDEX):
    with path.open('rb') as stream:
        raw = stream.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise ValueError('Qualification index exceeds bounded size')
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
        raise ValueError('Qualification index must be a JSON object')
    return value


def validate_record(record, *, as_of, root=ROOT):
    if set(record) != RECORD_KEYS:
        raise ValueError('Qualification record has unexpected or missing fields')
    if not isinstance(record['id'], str) or not ID.fullmatch(record['id']):
        raise ValueError('Qualification record ID is invalid')
    if record['state'] != 'CURRENT_APPROVED':
        raise ValueError('Only CURRENT_APPROVED records belong in the active qualification index')
    if record['platform'] not in PLATFORMS:
        raise ValueError('Qualification record uses an unknown platform family')
    if not isinstance(record['product_tuple_id'], str) or not TUPLE_ID.fullmatch(record['product_tuple_id']):
        raise ValueError('Exact product tuple ID required')

    product = record['product_tuple']
    if not isinstance(product, dict) or set(product) != TUPLE_KEYS:
        raise ValueError('Exact product/API/provider/hardware tuple fields required')
    for key in ('product', 'product_version', 'api', 'api_version', 'hardware_profile_ref'):
        bounded(product[key], f'product_tuple.{key}')
    providers = unique_strings(product['automation_providers'], 'automation_providers')
    licenses = unique_strings(product['feature_licenses'], 'feature_licenses', allow_empty=True)
    if not providers:
        raise ValueError('At least one tested automation-provider tuple is required')

    assurance = unique_strings(record['assurance_profiles'], 'assurance_profiles', allow_empty=True)
    caps = unique_strings(record['qualified_capabilities'], 'qualified_capabilities')
    if not set(caps) <= CAPABILITIES:
        raise ValueError('Record qualifies an unknown portable capability')
    tests = unique_strings(record['applicable_test_sets'], 'applicable_test_sets')
    if any(len(x) > 128 for x in tests):
        raise ValueError('Test-set reference too long')

    limits = record['tested_limits']
    if not isinstance(limits, list) or not limits or len(limits) > 64:
        raise ValueError('At least one bounded tested-limit record is required')
    evidence_by_ref = {}
    evidence = record['evidence']
    if not isinstance(evidence, list) or not evidence or len(evidence) > 128:
        raise ValueError('Native evidence records are required')
    for item in evidence:
        if not isinstance(item, dict) or set(item) != EVIDENCE_KEYS:
            raise ValueError('Evidence entry shape invalid')
        ref = bounded(item['ref'], 'evidence.ref')
        if ref in evidence_by_ref:
            raise ValueError('Duplicate evidence reference')
        if not isinstance(item['sha256'], str) or not SHA.fullmatch(item['sha256']):
            raise ValueError('Evidence SHA-256 required')
        observed = instant(item['observed_at'], 'evidence.observed_at')
        expires = instant(item['expires_at'], 'evidence.expires_at')
        bounded(item['test_set'], 'evidence.test_set', 128)
        if observed > as_of or expires <= observed:
            raise ValueError('Evidence time range is invalid')
        evidence_by_ref[ref] = (observed, expires, item['test_set'])

    for item in limits:
        if not isinstance(item, dict) or set(item) != LIMIT_KEYS:
            raise ValueError('Tested-limit entry shape invalid')
        for key in ('name', 'observed_bound', 'unit'):
            bounded(item[key], f'tested_limits.{key}')
        if item['evidence_ref'] not in evidence_by_ref:
            raise ValueError('Tested limit is not bound to native evidence')

    approval = record['approval']
    if not isinstance(approval, dict) or set(approval) != APPROVAL_KEYS:
        raise ValueError('Approval record shape invalid')
    bounded(approval['authority_role'], 'approval.authority_role')
    bounded(approval['decision_ref'], 'approval.decision_ref')
    approved = instant(approval['approved_at'], 'approval.approved_at')
    approval_expires = instant(approval['expires_at'], 'approval.expires_at')
    if approved > as_of or approval_expires <= approved:
        raise ValueError('Approval time range invalid')
    if as_of >= approval_expires:
        raise ValueError('Qualification approval is expired')

    for ref, (observed, expires, test_set) in evidence_by_ref.items():
        if as_of >= expires:
            raise ValueError(f'Qualification evidence is expired: {ref}')
        if test_set not in tests:
            raise ValueError('Evidence uses a test set outside applicable_test_sets')
        if observed > approved:
            raise ValueError('Approval predates required native evidence')

    owners = record['owners']
    if not isinstance(owners, dict) or set(owners) != OWNER_KEYS:
        raise ValueError('Qualification owner fields required')
    for key in OWNER_KEYS:
        bounded(owners[key], key)

    unique_strings(record['exclusions'], 'exclusions', allow_empty=True)
    refs = unique_strings(record['source_refs'], 'source_refs')
    for ref in refs:
        repository_ref(ref, root)

    return {
        'id': record['id'],
        'platform': record['platform'],
        'product_tuple_id': record['product_tuple_id'],
        'product_tuple': dict(record['product_tuple']),
        'qualified_capabilities': sorted(caps),
        'assurance_profiles': sorted(assurance),
        'evidence_refs': sorted(evidence_by_ref),
        'approval_expires_at': approval_expires.isoformat()
    }


def validate(index, *, as_of=None, root=ROOT, provenance_index=None):
    if as_of is None:
        as_of = datetime.now(timezone.utc)
    if not isinstance(as_of, datetime) or as_of.tzinfo is None:
        raise ValueError('Timezone-aware as_of required')
    as_of = as_of.astimezone(timezone.utc)
    if set(index) != {'format', 'status', 'reviewed_source_revision', 'records'}:
        raise ValueError('Unexpected qualification-index fields')
    if index['format'] != FORMAT or index['status'] != STATUS:
        raise ValueError('Unsupported qualification-index format or authority boundary')
    revision = index['reviewed_source_revision']
    if not isinstance(revision, str) or not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('Reviewed source revision must be an exact Git SHA')
    if not isinstance(index['records'], list) or len(index['records']) > 64:
        raise ValueError('Qualification records must be a bounded list')
    if provenance_index is None:
        provenance_index = provenance.load()
    provenance_summary = provenance.validate(provenance_index, as_of=as_of, root=root)
    provenance_records = provenance_summary['records']
    seen = set()
    records = []
    for record in index['records']:
        checked = validate_record(record, as_of=as_of, root=root)
        if checked['id'] in seen:
            raise ValueError('Duplicate qualification record ID')
        supporting = [
            item for item in provenance_records
            if item['state'] == 'CURRENT_SUPPORTED'
            and item['platform'] == checked['platform']
            and item['product_tuple_id'] == checked['product_tuple_id']
        ]
        if len(supporting) != 1:
            raise ValueError('Current qualification requires one matching CURRENT_SUPPORTED version/source provenance record')
        if supporting[0]['product_tuple'] != checked['product_tuple']:
            raise ValueError('Qualification product tuple differs from current version/source provenance record')
        checked['provenance_id'] = supporting[0]['provenance_id']
        seen.add(checked['id'])
        records.append(checked)
    return {
        'current_records': len(records),
        'qualified_capability_claims': sum(len(x['qualified_capabilities']) for x in records),
        'platforms_with_current_records': sorted({x['platform'] for x in records}),
        'records': records
    }


def records_for(index, platform, product_tuple_id, *, as_of=None, root=ROOT, provenance_index=None):
    summary = validate(index, as_of=as_of, root=root, provenance_index=provenance_index)
    return [r for r in summary['records']
            if r['platform'] == platform and r['product_tuple_id'] == product_tuple_id]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--index', type=Path, default=INDEX)
    parser.add_argument('--as-of', help='ISO-8601 review instant; defaults to current UTC')
    args = parser.parse_args()
    try:
        as_of = instant(args.as_of, 'as_of') if args.as_of else datetime.now(timezone.utc)
        index = load(args.index)
        summary = validate(index, as_of=as_of)
        result = {
            'status': 'PASSED_NATIVE_QUALIFICATION_INDEX',
            'as_of': as_of.isoformat(),
            **summary,
            'may_select_site': False,
            'may_reserve_capacity': False,
            'may_allocate': False,
            'may_apply': False,
            'may_activate': False,
            'limits': [
                'Qualification-record consistency only; no platform contact occurs.',
                'A current qualification record requires a matching CURRENT_SUPPORTED version/source provenance record.',
                'A current qualification record is not production placement or service authorization.',
                'Site/cell capacity, requester authority, recovery and operating acceptance remain separate.'
            ]
        }
        print(json.dumps(result, indent=2))
        return 0
    except (ValueError, OSError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({
            'status': 'FAILED_NATIVE_QUALIFICATION_INDEX',
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
