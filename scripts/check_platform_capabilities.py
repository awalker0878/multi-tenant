#!/usr/bin/env python3
"""Validate the engineering capability registry and fail closed for placement eligibility.

This tool does not contact a platform, choose a site, deploy resources, or authorize a
workload. It verifies that capability claims are bound to repository engineering
sources and that NATIVE_QUALIFIED claims are backed by a current exact-tuple
qualification dossier.
"""
from __future__ import annotations
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import check_platform_qualification as qualification

REGISTRY = ROOT / 'sources/capabilities/platform_registry.json'
CAPABILITIES = {
    'network_domain', 'ipv4', 'ipv6', 'distributed_firewall', 'gateway_policy',
    'dynamic_routing', 'service_insertion', 'native_load_balancer',
    'dedicated_edge_context', 'audit_logging'
}
SOURCE_STATES = {'UNASSESSED', 'DOCUMENTED_EXPECTATION', 'CANDIDATE_SOURCE', 'LOCAL_FIXTURE_ONLY'}
QUALIFICATIONS = {'NOT_QUALIFIED', 'NATIVE_QUALIFIED'}
PLATFORMS = {'nutanix', 'vmware-nsx', 'openstack'}


def load(path: Path = REGISTRY) -> dict:
    with path.open('rb') as stream:
        raw = stream.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise ValueError('Capability registry exceeds bounded size')
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate JSON property')
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs)


def validate(registry: dict, root: Path = ROOT, qualification_index=None, provenance_index=None, as_of=None) -> dict:
    if set(registry) != {'format', 'status', 'reviewed_source_revision', 'qualification_rule', 'capability_ids', 'profiles'}:
        raise ValueError('Unexpected registry fields')
    if registry['format'] != 'portable-hosting-capability-registry/1':
        raise ValueError('Unsupported capability-registry format')
    if registry['status'] != 'ENGINEERING_EVIDENCE_REGISTRY_NOT_PLACEMENT_AUTHORITY':
        raise ValueError('Registry status must retain its engineering-evidence boundary')
    if set(registry['capability_ids']) != CAPABILITIES or len(registry['capability_ids']) != len(CAPABILITIES):
        raise ValueError('Portable capability vocabulary differs from the reviewed profile')
    if set(registry['profiles']) != PLATFORMS:
        raise ValueError('Exactly the three implemented platform families are required')

    if qualification_index is None:
        qualification_index = qualification.load()
    qsummary = qualification.validate(qualification_index, as_of=as_of, root=root, provenance_index=provenance_index)
    qrecords = qsummary['records']

    source_refs = set()
    qualified = 0
    for name, profile in registry['profiles'].items():
        if set(profile) != {'platform_family', 'product_tuple', 'terraform_providers', 'assurance_profiles', 'capabilities'}:
            raise ValueError(f'{name}: unexpected profile fields')
        if profile['product_tuple'] == 'UNSELECTED' and profile['assurance_profiles']:
            raise ValueError(f'{name}: an unselected native tuple cannot advertise an assurance profile')
        if not isinstance(profile['terraform_providers'], list) or not profile['terraform_providers']:
            raise ValueError(f'{name}: provider-interface record required')
        if set(profile['capabilities']) != CAPABILITIES:
            raise ValueError(f'{name}: portable capability set is incomplete')

        tuple_records = [
            r for r in qrecords
            if r['platform'] == name and r['product_tuple_id'] == profile['product_tuple']
        ] if profile['product_tuple'] != 'UNSELECTED' else []

        for cap, claim in profile['capabilities'].items():
            if set(claim) != {'source_state', 'qualification', 'evidence_refs', 'native_evidence_refs'}:
                raise ValueError(f'{name}/{cap}: unexpected claim fields')
            if claim['source_state'] not in SOURCE_STATES or claim['qualification'] not in QUALIFICATIONS:
                raise ValueError(f'{name}/{cap}: unsupported state')
            if not isinstance(claim['evidence_refs'], list) or not claim['evidence_refs']:
                raise ValueError(f'{name}/{cap}: repository evidence reference required')
            if not isinstance(claim['native_evidence_refs'], list):
                raise ValueError(f'{name}/{cap}: native evidence list required')
            for ref in claim['evidence_refs']:
                if not isinstance(ref, str) or ref.startswith('/') or '..' in Path(ref).parts or not (root / ref).exists():
                    raise ValueError(f'{name}/{cap}: invalid repository evidence reference')
                source_refs.add(ref)

            if claim['qualification'] == 'NATIVE_QUALIFIED':
                qualified += 1
                if profile['product_tuple'] == 'UNSELECTED':
                    raise ValueError(f'{name}/{cap}: native qualification requires an exact installed tuple')
                if not claim['native_evidence_refs'] or any(not isinstance(x, str) or not x.strip() for x in claim['native_evidence_refs']):
                    raise ValueError(f'{name}/{cap}: native qualification requires external evidence references')
                supporting = [r for r in tuple_records if cap in r['qualified_capabilities']]
                if not supporting:
                    raise ValueError(f'{name}/{cap}: no current exact-tuple qualification dossier covers this claim')
                allowed_evidence = {ref for r in supporting for ref in r['evidence_refs']}
                if not set(claim['native_evidence_refs']) <= allowed_evidence:
                    raise ValueError(f'{name}/{cap}: registry evidence is not contained in the qualification dossier')
            elif claim['native_evidence_refs']:
                raise ValueError(f'{name}/{cap}: native evidence cannot be attached to a NOT_QUALIFIED claim')

        if profile['assurance_profiles']:
            qualified_assurance = {item for r in tuple_records for item in r['assurance_profiles']}
            if not set(profile['assurance_profiles']) <= qualified_assurance:
                raise ValueError(f'{name}: assurance profile is not covered by a current exact-tuple qualification dossier')

    return {
        'platforms': len(PLATFORMS),
        'capabilities_per_platform': len(CAPABILITIES),
        'native_qualified_claims': qualified,
        'repository_evidence_refs': len(source_refs),
        'current_qualification_records': qsummary['current_records']
    }


def eligible(registry: dict, platform: str, required: set[str], assurance_profile: str | None = None,
             qualification_index=None, provenance_index=None, as_of=None) -> tuple[bool, list[str]]:
    validate(registry, qualification_index=qualification_index, provenance_index=provenance_index, as_of=as_of)
    if platform not in PLATFORMS or not required <= CAPABILITIES:
        raise ValueError('Unknown platform or capability requirement')
    profile = registry['profiles'][platform]
    blockers = [cap for cap in sorted(required) if profile['capabilities'][cap]['qualification'] != 'NATIVE_QUALIFIED']
    if profile['product_tuple'] == 'UNSELECTED':
        blockers.insert(0, 'product_tuple:UNSELECTED')
    if assurance_profile is not None and assurance_profile not in profile['assurance_profiles']:
        blockers.append('assurance_profile:' + assurance_profile)
    return not blockers, blockers


def main() -> int:
    try:
        registry = load(); summary = validate(registry)
        result = {
            'status': 'PASSED_CAPABILITY_REGISTRY_STRUCTURE',
            **summary,
            'production_eligible_platforms': [
                p for p in sorted(PLATFORMS)
                if eligible(registry, p, {'network_domain','ipv4'})[0]
            ],
            'limits': [
                'Repository/source evidence is not native qualification.',
                'NATIVE_QUALIFIED requires a current exact-tuple qualification dossier backed by CURRENT_SUPPORTED version/source provenance.',
                'This check never performs platform placement or contacts infrastructure.'
            ]
        }
        print(json.dumps(result, indent=2)); return 0
    except (ValueError, OSError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({'status': 'FAILED_CAPABILITY_REGISTRY', 'reason': str(exc)})); return 2


if __name__ == '__main__':
    raise SystemExit(main())
