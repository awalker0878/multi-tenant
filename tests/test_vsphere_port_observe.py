"""Exact native port reads fail closed on reuse, omissions and changing attachments."""
from copy import deepcopy
import json
import unittest
from lab.native_readback_fixture import Fixture
from tests.test_vsphere_network_observe import manifest as pg_manifest, Client as GroupClient
from tests.test_vsphere_observe import ref
from provisioner.execution import readback_core as c
from provisioner.execution import vsphere_port_observe as p
from provisioner.execution import vsphere_network_observe as pg


def manifest(origin='https://vc.example.test'):
    m = pg_manifest(origin); m['profile'] = p.PROFILE
    m['resources'][0]['ports'] = [dict(_typeName='DistributedVirtualPort', key='17', dvsUuid='fixture-dvs-uuid',
        portgroupKey='dvportgroup-1', config=dict(_typeName='DVPortConfigInfo', configVersion='3'),
        proxyHost=ref('HostSystem', 'host-1'), conflict=False, connectionCookie=12345, lastStatusChange='2026-09-19T12:00:00Z',
        connectee=dict(_typeName='DistributedVirtualSwitchPortConnectee', connectedEntity=ref('VirtualMachine', 'vm-1'), nicKey='4000', type='vmVnic'),
        state=dict(_typeName='DVPortState', runtimeInfo=dict(_typeName='DVPortStatus', linkUp=True, blocked=False, macAddress='00:50:56:01:02:03')))]
    return m


class Client(GroupClient):
    def __init__(self, m):
        super().__init__(m); self.rows = {r['moid']: deepcopy(r['ports']) for r in m['resources']}; self.port_transform = None
    def ports(self, identity):
        self.request_count += 1; rows = deepcopy(self.rows[identity])
        if self.port_transform: self.port_transform(rows, self.request_count)
        return rows


class PortTests(unittest.TestCase):
    def setUp(self): self.m = manifest(); self.client = Client(self.m)
    def observe(self): return c.observe(self.m, self.client, p, interval=0)
    def test_matching_attachment_is_not_activation_or_task_completion(self):
        result = self.observe(); self.assertEqual(result['outcome'], 'READBACK_MATCH_NOT_QUALIFIED')
        self.assertEqual(result['request_count'], 12); self.assertFalse(result['may_activate'])
        self.assertFalse(result['history'][-1]['states'][0]['task_completion_observed'])
    def test_port_reuse_host_change_and_missing_connectee_hold(self):
        for change in (lambda r: r.update(connectionCookie=987), lambda r: r.update(dvsUuid='foreign'),
            lambda r: r.update(portgroupKey='foreign'), lambda r: r['proxyHost'].update(value='host-2'),
            lambda r: r['connectee']['connectedEntity'].update(value='vm-2'), lambda r: r['connectee'].update(nicKey='4001'),
            lambda r: r['connectee'].pop('connectedEntity'), lambda r: r.update(connectionCookie=True)):
            self.client = Client(self.m); change(self.client.rows['dvportgroup-1'][0])
            self.assertEqual(self.observe()['outcome'], 'HOLD_UNCERTAIN')
    def test_runtime_and_revision_difference_hold(self):
        for change in (lambda r: r.update(conflict=True), lambda r: r['state']['runtimeInfo'].update(linkUp=False),
            lambda r: r['state']['runtimeInfo'].update(blocked=True), lambda r: r['state']['runtimeInfo'].update(macAddress='00:50:56:01:02:04'),
            lambda r: r['config'].update(configVersion='4'), lambda r: r.update(lastStatusChange='2026-09-19T12:00:01Z')):
            self.client = Client(self.m); change(self.client.rows['dvportgroup-1'][0])
            self.assertEqual(self.observe()['outcome'], 'HOLD_DIFFERENCE')
    def test_port_set_missing_extra_duplicate_and_malformed_hold(self):
        port = self.m['resources'][0]['ports'][0]
        for rows in ([], [port, port], [port | dict(key='foreign')], [None], {}, [port | dict(key=[]) ]):
            self.client = Client(self.m); self.client.rows['dvportgroup-1'] = rows
            self.assertEqual(self.observe()['outcome'], 'HOLD_UNCERTAIN')
        self.m['resources'][0]['ports'].append(deepcopy(port) | dict(key='18', connectee=deepcopy(port['connectee']) | dict(nicKey='4001')))
        self.client = Client(self.m); self.client.rows['dvportgroup-1'] = [port, port]
        self.assertEqual(self.observe()['outcome'], 'HOLD_UNCERTAIN')
    def test_port_reads_bracket_group_reads_and_detect_races(self):
        self.client.port_transform = lambda rows, count: rows[0].update(connectionCookie=42) if count > 1 else None
        self.assertEqual(self.observe()['outcome'], 'HOLD_UNCERTAIN')
        self.client = Client(self.m)
        self.client.transform = lambda path, body, count: body.update(configVersion='new') if path.endswith('/config') and count > 2 else None
        self.assertEqual(self.observe()['outcome'], 'HOLD_UNCERTAIN')
    def test_unbounded_ambiguous_or_unusable_expectations_rejected(self):
        for change in (lambda m: m.update(profile=pg.PROFILE), lambda m: m['resources'][0].update(ports=[]),
            lambda m: m['resources'][0]['ports'].append(deepcopy(m['resources'][0]['ports'][0])),
            lambda m: m['resources'][0]['ports'][0].update(connectionCookie=True),
            lambda m: m['resources'][0]['ports'][0].update(connectionCookie=2**31),
            lambda m: m['resources'][0]['ports'][0]['state']['runtimeInfo'].update(linkUp=False),
            lambda m: m['resources'][0]['ports'][0]['connectee'].update(type='pnic'),
            lambda m: m['resources'][0]['ports'][0].update(dvsUuid='foreign')):
            m = deepcopy(self.m); change(m)
            with self.assertRaises(ValueError): p.targets(m)
    def test_real_tls_exact_scoped_post_body_and_private_projection(self):
        with Fixture() as f:
            m = manifest(f.origin); fake = Client(m); r = m['resources'][0]; path, body = p.request(r)
            f.routes = {k: dict(body=v) for k, v in fake.routes.items()}
            rows = deepcopy(r['ports']); rows[0]['config']['description'] = 'PRIVATE-SENTINEL'
            rows[0]['state']['stats'] = {'private': 'PRIVATE-SENTINEL'}
            f.post_routes[path] = lambda actual: dict(body=rows) if actual == body else dict(status=400, body={})
            http = p.Client(m, f.origin, 'fixture-session', str(f.directory / 'ca.pem'))
            with self.assertRaises(c.ObservationError): http.ports('dvportgroup-99')
            with self.assertRaises(c.ObservationError): http.get(path)
            result = c.observe(m, http, p, interval=0)
            self.assertEqual(result['outcome'], 'READBACK_MATCH_NOT_QUALIFIED'); self.assertNotIn('PRIVATE-SENTINEL', json.dumps(result))
            self.assertEqual([x['method'] for x in f.requests], ['POST', 'GET', 'GET', 'GET', 'GET', 'POST'] * 2)
            self.assertTrue(all(x['has_session_auth'] and not x['has_basic_auth'] for x in f.requests))
            self.assertEqual(body, {'criteria': {'portKey': ['17']}})
            self.assertEqual({x['path'] for x in f.requests}, p.targets(m) | {path})


if __name__ == '__main__': unittest.main()
