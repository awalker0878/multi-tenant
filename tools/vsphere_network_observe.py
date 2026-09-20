#!/usr/bin/env python3
"""GET-only NSX-backed vSphere portgroup identities; no DFW enforcement claim."""
from pathlib import Path
import re
import sys
if __package__ in (None, ''): sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import readback_core as c, vsphere_observe as vm, nsx_observe as nsx
from tools.nutanix_vm_observe import selected, uuid
from tools.run_files import require

PROFILE = 'vsphere-vi-json-8.0.3.0-nsx-portgroups'
CONFIG = {'_typeName', 'key', 'configVersion', 'distributedVirtualSwitch', 'backingType', 'type', 'uplink', 'logicalSwitchUuid'}


def backing_key(r): return (r['expected']['switch']['uuid'], r['expected']['config']['key'])


def validate(m):
    c.common_manifest(m, 'vmware')
    require(m['profile'] == PROFILE and 'task' not in m, 'NSX portgroup profile required')
    seen = set(); backings = set(); switches = {}
    for r in m['resources']:
        c.exact_keys(r, {'kind', 'moid', 'segment_path', 'expected'})
        require(r['kind'] == 'nsx-portgroup', 'Only NSX distributed portgroups supported')
        vm.moid(r['moid'], 'dvportgroup')
        require(r['moid'] not in seen, 'Duplicate portgroup'); seen.add(r['moid'])
        require(isinstance(r['segment_path'], str) and re.fullmatch(nsx.PATTERNS['segment'], r['segment_path']), 'Exact Local Manager segment path required')
        e = r['expected']; c.exact_keys(e, {'config', 'switch'}); config = e['config']; c.exact_keys(config, CONFIG)
        require(config['_typeName'] == 'DVPortgroupConfigInfo' and config['backingType'] == 'nsx'
                and config['type'] == 'ephemeral' and config['uplink'] is False, 'NSX ephemeral non-uplink required')
        c.text(config['key']); c.text(config['configVersion']); uuid(config['logicalSwitchUuid'])
        vm.reference(config['distributedVirtualSwitch'], 'VmwareDistributedVirtualSwitch', 'dvs')
        c.exact_keys(e['switch'], {'_typeName', 'uuid'})
        require(e['switch']['_typeName'] == 'DVSSummary', 'DVS summary required'); c.text(e['switch']['uuid'])
        switch = config['distributedVirtualSwitch']['value']
        require(switch not in switches or switches[switch] == e['switch'], 'Contradictory switch identity')
        switches[switch] = e['switch']
        key = backing_key(r); require(key not in backings, 'Ambiguous backing identity'); backings.add(key)
    require(len({s['uuid'] for s in switches.values()}) == len(switches), 'Duplicate switch UUID')


def properties(r):
    switch = r['expected']['config']['distributedVirtualSwitch']['value']
    return {'config': vm.PREFIX + 'DistributedVirtualPortgroup/' + r['moid'] + '/config',
            'switch': vm.PREFIX + 'VmwareDistributedVirtualSwitch/' + switch + '/summary'}


def targets(m):
    validate(m)
    return {path for r in m['resources'] for path in properties(r).values()}


def read(r, client):
    return {key: selected(client.get(path)[0], r['expected'][key]) for key, path in properties(r).items()}


def sample(m, client):
    states = []
    for r in m['resources']:
        before = read(r, client); after = read(r, client)
        mismatches = c.differences(after, r['expected'])
        stable = c.digest(before) == c.digest(after)
        identity = all(not c.differences(x, {'config': {k: r['expected']['config'][k]
            for k in ('_typeName', 'key', 'distributedVirtualSwitch')}, 'switch': r['expected']['switch']}) for x in (before, after))
        if not stable: mismatches.append('/snapshot:changed_during_observation')
        unknown = not stable or not identity or any(p.endswith((':missing', ':type')) for p in mismatches)
        states.append(dict(resource_key=r['moid'], identity_match=identity, config_status='UNKNOWN' if unknown else 'DIFFERENT' if mismatches else 'MATCH',
            progress='COMPLETE', mismatch_fields=mismatches, config_sha256=c.digest(after), task_completion_observed=False,
            reason='PORTGROUP_IDENTITY_ONLY_NOT_PORT_ATTACHMENT_OR_DFW_ENFORCEMENT'))
    return states


if __name__ == '__main__':
    from tools.readback_cli import run
    raise SystemExit(run(sys.modules[__name__], 'VCENTER', session=True))
