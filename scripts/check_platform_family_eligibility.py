#!/usr/bin/env python3
"""Evaluate platform-family capability eligibility before site placement.

This is a fail-closed engineering precheck, not a placement scheduler, allocator,
reservation service, provisioning controller, or authorization engine. It evaluates
only the portable capability subset recorded in the repository. Site/cell/pool,
capacity, zone-sharing, storage, service, recovery, quota and authority gates remain
separate even when a platform family satisfies every requested capability.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import check_platform_capabilities as capabilities
FORMAT = 'portable-hosting-platform-family-eligibility/1'
STATUS = 'PLANNING_ONLY_NOT_AUTHORIZED'
MODE = 'SINGLE_PLATFORM_WSD'
HOLD = 'HOLD_NO_NATIVE_QUALIFIED_PLATFORM'
MATCH = 'PLATFORM_FAMILY_CAPABILITY_MATCH_SITE_GATES_REMAIN'
REQUEST_KEYS = {
    'format', 'status', 'request_id', 'wsd_engineering_ref', 'placement_mode',
    'candidate_platforms', 'mandatory_capabilities', 'optional_capabilities',
    'required_assurance_profile', 'site_binding', 'production_authority',
    'source_refs'
}
SITE_KEYS = {'site_ref', 'cell_ref', 'service_class_ref'}
REQUEST_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$')


def bounded_text(value, label, limit=512):
    if (not isinstance(value, str) or not value.strip() or len(value) > limit
            or any(ord(c) < 32 or ord(c) == 127 for c in value)):
        raise ValueError(f'{label}: bounded nonempty text required')
    return value


def unique_strings(value, label, *, allow_empty=False):
    if not isinstance(value, list) or (not allow_empty and not value) or len(value) > 64:
        raise ValueError(f'{label}: bounded list required')
    if any(not isinstance(item, str) or not item for item in value):
        raise ValueError(f'{label}: nonempty strings required')
    if len(value) != len(set(value)):
        raise ValueError(f'{label}: duplicates are not allowed')
    return value


def repository_ref(value):
    bounded_text(value, 'repository reference')
    path = Path(value)
    if path.is_absolute() or '..' in path.parts or '\\' in value or ':' in value:
        raise ValueError('Repository reference must be a normalized relative path')
    target = ROOT / path
    if not target.exists():
        raise ValueError(f'Repository reference does not exist: {value}')
    return value


def load_request(path: Path) -> dict:
    with path.open('rb') as stream:
        raw = stream.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise ValueError('Request exceeds bounded size')

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
        raise ValueError('Request must be a JSON object')
    return value


def validate_request(request: dict, registry: dict) -> None:
    if set(request) != REQUEST_KEYS:
        raise ValueError('Unexpected or missing pre-placement request fields')
    if request['format'] != FORMAT or request['status'] != STATUS:
        raise ValueError('Unsupported request format or authority boundary')
    if not isinstance(request['request_id'], str) or not REQUEST_ID.fullmatch(request['request_id']):
        raise ValueError('Invalid request identity')
    wsd_ref = repository_ref(request['wsd_engineering_ref'])
    refs = unique_strings(request['source_refs'], 'source_refs')
    for ref in refs:
        repository_ref(ref)
    if wsd_ref not in refs:
        raise ValueError('The maintained WSD engineering reference must be in source_refs')
    if request['placement_mode'] != MODE:
        raise ValueError('This profile supports only the default single-platform WSD realization')

    candidates = unique_strings(request['candidate_platforms'], 'candidate_platforms')
    if any(platform not in registry['profiles'] for platform in candidates):
        raise ValueError('Unknown candidate platform family')

    mandatory = unique_strings(request['mandatory_capabilities'], 'mandatory_capabilities')
    optional = unique_strings(request['optional_capabilities'], 'optional_capabilities', allow_empty=True)
    vocabulary = set(registry['capability_ids'])
    if not set(mandatory) <= vocabulary or not set(optional) <= vocabulary:
        raise ValueError('Request uses a capability outside the portable registry vocabulary')
    if set(mandatory) & set(optional):
        raise ValueError('A capability cannot be both mandatory and optional')

    assurance = request['required_assurance_profile']
    if assurance is not None:
        bounded_text(assurance, 'required_assurance_profile', 160)

    site = request['site_binding']
    if not isinstance(site, dict) or set(site) != SITE_KEYS:
        raise ValueError('Exact unselected site-binding fields required')
    if any(site[key] != 'UNSELECTED' for key in SITE_KEYS):
        raise ValueError('This precheck cannot bind a site, cell or service class')
    if request['production_authority'] != 'NOT_ASSESSED':
        raise ValueError('This precheck cannot carry production authority')


def evaluate(request: dict, registry: dict, qualification_index=None, as_of=None) -> dict:
    capabilities.validate(registry, qualification_index=qualification_index, as_of=as_of)
    validate_request(request, registry)
    mandatory = set(request['mandatory_capabilities'])
    assurance = request['required_assurance_profile']
    results = []
    eligible_platforms = []

    for platform in request['candidate_platforms']:
        profile = registry['profiles'][platform]
        family_ok, blockers = capabilities.eligible(
            registry, platform, mandatory, assurance_profile=assurance,
            qualification_index=qualification_index, as_of=as_of)
        optional_unavailable = sorted(
            cap for cap in request['optional_capabilities']
            if profile['capabilities'][cap]['qualification'] != 'NATIVE_QUALIFIED')
        if family_ok:
            eligible_platforms.append(platform)
        results.append({
            'platform': platform,
            'platform_family': profile['platform_family'],
            'product_tuple': profile['product_tuple'],
            'family_capability_eligible': family_ok,
            'mandatory_blockers': blockers,
            'optional_unavailable': optional_unavailable
        })

    status = MATCH if eligible_platforms else HOLD
    return {
        'kind': 'PLATFORM_FAMILY_PRE_PLACEMENT_EVALUATION',
        'status': status,
        'request_id': request['request_id'],
        'wsd_engineering_ref': request['wsd_engineering_ref'],
        'eligible_platforms': eligible_platforms,
        'evaluations': results,
        'may_select_site': False,
        'may_reserve_capacity': False,
        'may_allocate': False,
        'may_apply': False,
        'may_activate': False,
        'remaining_gates': [
            'requester authority and approved profile',
            'site/cell/service-class eligibility',
            'zone-sharing and physical placement policy',
            'quota and surviving capacity',
            'compute, storage, network, key and recovery compatibility',
            'address and security-edge capacity',
            'shared-service dependencies',
            'site-specific native qualification and operating acceptance'
        ],
        'limits': [
            'Platform-family capability evidence only; not complete Admit or Place-and-reserve.',
            'Optional unavailable capabilities are disclosed but do not satisfy or weaken mandatory requirements.',
            'An eligible platform family still requires an already authorized site/cell/pool and separate capacity/security decisions.',
            'No infrastructure, reservation, address, route, policy or authorization is created by this check.'
        ]
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('request', type=Path)
    parser.add_argument('--registry', type=Path, default=capabilities.REGISTRY)
    parser.add_argument('--expected-status', choices=(HOLD, MATCH))
    args = parser.parse_args()
    try:
        registry = capabilities.load(args.registry)
        request = load_request(args.request)
        result = evaluate(request, registry)
        print(json.dumps(result, indent=2))
        if args.expected_status is not None:
            return 0 if result['status'] == args.expected_status else 2
        return 0 if result['status'] == MATCH else 2
    except (ValueError, OSError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({
            'kind': 'PLATFORM_FAMILY_PRE_PLACEMENT_EVALUATION',
            'status': 'INVALID_PRE_PLACEMENT_REQUEST',
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
