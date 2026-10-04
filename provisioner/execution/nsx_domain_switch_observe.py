#!/usr/bin/env python3
"""GET-only owned domain configuration plus exact realized logical-switch evidence."""
from copy import deepcopy
from pathlib import Path
import sys
from provisioner.execution import nsx_domain_observe as domain
from provisioner.execution import nsx_segment_observe as switches
from provisioner.execution.run_files import require

PROFILE = 'nsx-local-policy-v1-domain-switches'
observation_keys = switches.observation_keys


def domain_manifest(m):
    result = deepcopy(m); result['profile'] = domain.PROFILE
    for resource in result['resources']: resource.pop('logical_switch', None)
    return result


def segment_manifest(m):
    """Project an already validated domain profile for the existing NIC binding."""
    validate(m)
    result = deepcopy(m); result['profile'] = switches.PROFILE
    for resource in result['resources']: resource['expected'].pop('display_name')
    return result


def validate(m):
    require(m.get('profile') == PROFILE, 'Explicit domain/switch profile required')
    domain.validate(domain_manifest(m))
    switches.validate_bindings(m)


def targets(m):
    validate(m)
    return domain.targets(domain_manifest(m)) | {switches.entity_target(r['path']) for r in m['resources'] if r['kind'] == 'segment'}


def sample(m, client):
    segments = [r for r in m['resources'] if r['kind'] == 'segment']
    before = {r['path']: switches.read(r, client) for r in segments}
    states = domain.sample(domain_manifest(m), client)
    return states + [switches.switch_state(r, before[r['path']], switches.read(r, client)) for r in segments]


def validate_observation_history(m, history, states, current=None):
    if len(states) == 1 and states[0].get('resource_key') == 'scope':
        domain.validate_observation_history(domain_manifest(m), history, states, current); return
    size = len(m['resources'])
    domain.validate_observation_history(domain_manifest(m), history, states[:size], current)
    switches.validate_switch_history(m, states[size:])


if __name__ == '__main__':
    from provisioner.execution.readback_cli import run
    raise SystemExit(run(sys.modules[__name__], 'NSXT'))
