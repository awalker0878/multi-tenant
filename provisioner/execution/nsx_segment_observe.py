#!/usr/bin/env python3
"""GET-only Local Manager segment-to-logical-switch realization identities."""
from pathlib import Path
import re
import sys
from urllib.parse import urlencode
from provisioner.execution import readback_core as c
from provisioner.execution import nsx_observe as nsx
from provisioner.execution.nutanix_vm_observe import uuid
from provisioner.execution.run_files import require

PROFILE = 'nsx-local-policy-v1-segment-switches'
FIELDS = {'resource_type', 'entity_type', 'id', 'path', '_revision', 'intent_reference',
          'enforcement_point_path', 'realization_specific_identifier', 'state'}


def policy_manifest(m):
    return m | {'profile': nsx.PROFILE, 'resources': [{k: v for k, v in r.items() if k != 'logical_switch'} for r in m['resources']]}


def validate(m):
    require(m.get('profile') == PROFILE, 'Segment switch profile required'); nsx.validate(policy_manifest(m))
    validate_bindings(m)


def validate_bindings(m):
    """Shared segment association contract; caller validates its policy profile."""
    switches = set(); found = False
    for r in m['resources']:
        if r['kind'] != 'segment':
            require('logical_switch' not in r, 'Only segments have switch bindings'); continue
        found = True; c.exact_keys(r, {'kind', 'path', 'expected', 'realization', 'logical_switch'})
        e = r['logical_switch']; c.exact_keys(e, FIELDS)
        require(e['resource_type'] == 'GenericPolicyRealizedResource' and e['entity_type'] == 'RealizedLogicalSwitch'
                and e['state'] == 'REALIZED' and e['intent_reference'] == [r['path']], 'Exact realized segment switch required')
        require(r['realization']['enforcement_points'] == [e['enforcement_point_path']], 'Single Local Manager enforcement point required')
        require(isinstance(e['path'], str) and re.fullmatch(r'/infra/realized-state/enforcement-points/' + nsx.PART + r'/logical-switches/' + nsx.PART, e['path']), 'Exact realized logical switch path required')
        c.identifier(e['id']); require(e['path'].rsplit('/', 1)[1] == e['id'], 'Realized switch path/ID differ')
        require(type(e['_revision']) is int and e['_revision'] >= 0, 'Native realized revision required')
        uuid(e['realization_specific_identifier'])
        require(e['realization_specific_identifier'] not in switches, 'Duplicate switch association')
        switches.add(e['realization_specific_identifier'])
    require(found, 'At least one segment binding required')


def entity_target(path):
    return '/policy/api/v1/infra/realized-state/realized-entities?' + urlencode({'intent_path': path})


def targets(m):
    validate(m)
    return nsx.targets(policy_manifest(m)) | {entity_target(r['path']) for r in m['resources'] if r['kind'] == 'segment'}


def read(r, client):
    body, _ = client.get(entity_target(r['path']))
    rows = body.get('results'); count = body.get('result_count')
    if not isinstance(rows, list) or len(rows) > 100 or type(count) is not int or count != len(rows) or body.get('cursor') not in (None, ''):
        raise c.ObservationError('NSX_REALIZED_ENTITY_COVERAGE_UNKNOWN')
    result = []; seen = set()
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get('entity_type'), str) or not isinstance(row.get('path'), str) or row['path'] in seen:
            raise c.ObservationError('NSX_REALIZED_ENTITY_IDENTITY_UNKNOWN')
        seen.add(row['path'])
        if row['entity_type'] == 'RealizedLogicalSwitch':
            result.append({k: row[k] for k in FIELDS if k in row} | {'alarms_empty': isinstance(row.get('alarms'), list) and not row['alarms']})
    return sorted(result, key=lambda row: row['path'])


def switch_state(r, before, after):
    status = 'UNKNOWN'; progress = 'UNKNOWN'; mismatches = []
    if len(before) == len(after) == 1 and c.digest(before) == c.digest(after):
        e = r['logical_switch'] | {'alarms_empty': True}; mismatches = c.differences(after[0], e)
        unknown = any(p.endswith((':missing', ':type')) for p in mismatches)
        identity = not c.differences(after[0], {k: e[k] for k in ('resource_type', 'entity_type', 'id', 'path', 'intent_reference', 'enforcement_point_path')})
        status = 'UNKNOWN' if unknown or not identity else 'DIFFERENT' if mismatches else 'MATCH'
        state = after[0].get('state')
        progress = ('FAILED' if state == 'ERROR' or not after[0]['alarms_empty'] else
                    'COMPLETE' if state == 'REALIZED' else 'PENDING' if state == 'UNREALIZED' else 'UNKNOWN')
    else: mismatches = ['/realization:ambiguous_missing_or_changed_switch']
    return dict(resource_key=r['path'] + ':logical-switch', identity_match=status != 'UNKNOWN', config_status=status,
        progress=progress, mismatch_fields=mismatches, config_sha256=c.digest({'before': before, 'after': after}),
        switch_witness={'before': before, 'after': after},
        reason='SEGMENT_SWITCH_IDENTITY_ONLY_NOT_EFFECTIVE_DFW_OR_ATTACHMENT')


def observation_keys(m):
    return {r['path'] for r in m['resources']} | {r['path'] + ':logical-switch' for r in m['resources'] if r['kind'] == 'segment'}


def validate_switch_history(m, states):
    segments = [r for r in m['resources'] if r['kind'] == 'segment']
    try:
        require(len(states) == len(segments), 'Realized-switch coverage differs')
        for resource, state in zip(segments, states):
            witness = state['switch_witness']; c.exact_keys(witness, {'before', 'after'})
            for rows in witness.values():
                require(isinstance(rows, list) and len(rows) <= 100, 'Unbounded switch witness')
                for row in rows:
                    c.exact_keys(row, {'alarms_empty'}, FIELDS)
                    require(type(row['alarms_empty']) is bool, 'Invalid switch alarm indicator')
            require(c.digest(state) == c.digest(switch_state(resource, witness['before'], witness['after'])),
                    'Realized-switch summary contradicts native evidence')
    except (ValueError, TypeError, KeyError, IndexError, AttributeError):
        raise c.ObservationError('NSX_SWITCH_WITNESS_INVALID') from None


def validate_observation_history(m, history, states, current=None):
    if len(states) == 1 and states[0].get('resource_key') == 'scope':
        nsx.validate_observation_history(policy_manifest(m), history, states, current); return
    size = len(m['resources'])
    nsx.validate_observation_history(policy_manifest(m), history, states[:size], current)
    validate_switch_history(m, states[size:])


def sample(m, client):
    segments = [r for r in m['resources'] if r['kind'] == 'segment']
    before = {r['path']: read(r, client) for r in segments}
    states = nsx.sample(policy_manifest(m), client)
    return states + [switch_state(r, before[r['path']], read(r, client)) for r in segments]


if __name__ == '__main__':
    from provisioner.execution.readback_cli import run
    raise SystemExit(run(sys.modules[__name__], 'NSXT'))
