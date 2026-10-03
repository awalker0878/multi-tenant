#!/usr/bin/env python3
"""Observe exact NSX distributed-port attachments; no port or VM mutations."""
import os
from pathlib import Path
import re
import sys
if __package__ in (None, ''): sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from provisioner.execution import readback_core as c
from tools import vsphere_network_observe as pg, vsphere_observe as vm
from tools.nutanix_vm_observe import selected
from provisioner.execution.run_files import require

PROFILE = 'vsphere-vi-json-8.0.3.0-nsx-port-attachments'
PORT_FIELDS = {'_typeName', 'key', 'config', 'dvsUuid', 'portgroupKey', 'proxyHost',
               'connectee', 'conflict', 'state', 'connectionCookie', 'lastStatusChange'}
IDENTITY = {'_typeName', 'key', 'dvsUuid', 'portgroupKey', 'proxyHost', 'connectee', 'connectionCookie'}


def group_manifest(m):
    return m | {'profile': pg.PROFILE, 'resources': [{k: v for k, v in r.items() if k != 'ports'} for r in m['resources']]}


def cookie(value):
    require(type(value) is int and -(2**31) <= value < 2**31, 'Native int32 connection cookie required')


def validate(m):
    require(m['profile'] == PROFILE, 'Port attachment profile required')
    pg.validate(group_manifest(m)); seen = set(); connectees = set(); count = 0
    for r in m['resources']:
        c.exact_keys(r, {'kind', 'moid', 'segment_path', 'expected', 'ports'})
        require(isinstance(r['ports'], list) and 1 <= len(r['ports']) <= 64, 'Bounded accepted port list required')
        for port in r['ports']:
            c.exact_keys(port, PORT_FIELDS)
            require(port['_typeName'] == 'DistributedVirtualPort' and port['conflict'] is False, 'Non-conflicting native port required')
            c.text(port['key']); cookie(port['connectionCookie']); c.timestamp(port['lastStatusChange'])
            require((port['dvsUuid'], port['portgroupKey']) == pg.backing_key(r), 'Foreign port backing')
            identity = (port['dvsUuid'], port['key']); require(identity not in seen, 'Duplicate port identity'); seen.add(identity)
            c.exact_keys(port['config'], {'_typeName', 'configVersion'})
            require(port['config']['_typeName'] == 'DVPortConfigInfo', 'Port config required'); c.text(port['config']['configVersion'])
            vm.reference(port['proxyHost'], 'HostSystem', 'host')
            entity = port['connectee']; c.exact_keys(entity, {'_typeName', 'connectedEntity', 'nicKey', 'type'})
            require(entity['_typeName'] == 'DistributedVirtualSwitchPortConnectee' and entity['type'] == 'vmVnic', 'VM NIC connectee required')
            vm.reference(entity['connectedEntity'], 'VirtualMachine', 'vm')
            require(isinstance(entity['nicKey'], str) and re.fullmatch(r'0|[1-9][0-9]{0,9}', entity['nicKey']), 'Native NIC key required')
            nic = (entity['connectedEntity']['value'], entity['nicKey'])
            require(nic not in connectees, 'Duplicate VM NIC attachment'); connectees.add(nic)
            state = port['state']; c.exact_keys(state, {'_typeName', 'runtimeInfo'})
            require(state['_typeName'] == 'DVPortState', 'Port state required')
            runtime = state['runtimeInfo']; c.exact_keys(runtime, {'_typeName', 'linkUp', 'blocked', 'macAddress'})
            require(runtime['_typeName'] == 'DVPortStatus' and runtime['linkUp'] is True and runtime['blocked'] is False, 'Usable native port required')
            require(isinstance(runtime['macAddress'], str) and re.fullmatch(r'(?:[0-9a-f]{2}:){5}[0-9a-f]{2}', runtime['macAddress']), 'Native MAC required')
        count += len(r['ports'])
    require(count <= 100, 'Total port observation limit exceeded')


def targets(m):
    validate(m)
    return pg.targets(group_manifest(m))


def request(r):
    switch = r['expected']['config']['distributedVirtualSwitch']['value']
    return vm.PREFIX + 'VmwareDistributedVirtualSwitch/' + switch + '/FetchDVPorts', {'criteria': {'portKey': sorted(p['key'] for p in r['ports'])}}


class Client(c.ReadClient):
    """Fixed FetchDVPorts reads only; no unconstrained POST or inventory query."""
    def __init__(self, m, expected_origin, session, ca_file=None):
        super().__init__(m['origin'], expected_origin, None, None, targets(m), ca_file, budget=120, session_token=session)
        self._requests = {r['moid']: request(r) for r in m['resources']}

    def ports(self, identity):
        if identity not in self._requests: raise c.ObservationError('PORTGROUP_NOT_IN_ACCEPTED_SCOPE')
        path, body = self._requests[identity]
        return self._request('POST', path, body, response_type=list)[0]


def read(r, client):
    rows = client.ports(r['moid']); expected = {p['key']: p for p in r['ports']}
    if not isinstance(rows, list) or len(rows) != len(expected): raise c.ObservationError('PORT_SET_INCOMPLETE_OR_EXTRA')
    result = {}
    for row in rows:
        key = row.get('key') if isinstance(row, dict) else None
        if not isinstance(key, str) or key not in expected or key in result: raise c.ObservationError('PORT_IDENTITY_AMBIGUOUS')
        result[key] = selected(row, expected[key])
    return result


def observation_keys(m): return pg.observation_keys(m)


def witness_state(r, evidence):
    c.exact_keys(evidence, {'before', 'after', 'portgroup'})
    expected = {p['key']: p for p in r['ports']}
    for phase in ('before', 'after'):
        c.exact_keys(evidence[phase], set(expected))
        require(c.digest(selected(evidence[phase], expected)) == c.digest(evidence[phase]), 'Selected port witness required')
    before, after = evidence['before'], evidence['after']
    state = pg.witness_state(r, evidence['portgroup']); del state['group_witness']
    mismatch = c.differences(after, expected)
    stable = c.digest(before) == c.digest(after)
    identity = all(not c.differences(snapshot, {key: {k: p[k] for k in IDENTITY} for key, p in expected.items()}) for snapshot in (before, after))
    if not stable: mismatch.append('/snapshot:changed_during_observation')
    unknown = not stable or not identity or any(p.endswith((':missing', ':type')) for p in mismatch)
    state['identity_match'] = state['identity_match'] and identity
    if unknown: state['config_status'] = 'UNKNOWN'
    elif mismatch and state['config_status'] == 'MATCH': state['config_status'] = 'DIFFERENT'
    state['mismatch_fields'] += ['/ports' + p for p in mismatch]
    state['config_sha256'] = c.digest({'portgroup_sha256': state['config_sha256'], 'ports': after})
    state['attachment_witness'] = evidence
    state['reason'] = 'SELECTED_PORT_ATTACHMENT_ONLY_NOT_DFW_ENFORCEMENT_OR_WRITER_FENCE'
    return state


def sample(m, client):
    states = []
    for r in m['resources']:
        before = read(r, client)
        group = dict(before=pg.read(r, client), after=pg.read(r, client))
        states.append(witness_state(r, dict(before=before, portgroup=group, after=read(r, client))))
    return states


def validate_observation_history(m, history, states, current=None):
    pg.validate_witnesses(m, states, witness_state, 'attachment_witness')


if __name__ == '__main__':
    from tools.readback_cli import run
    raise SystemExit(run(sys.modules[__name__], 'VCENTER', session=True,
        client_factory=lambda m, a: Client(m, a.expected_origin, os.environ.get('VCENTER_SESSION', ''), a.ca_file)))
