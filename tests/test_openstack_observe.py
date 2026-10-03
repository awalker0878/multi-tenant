import copy
from datetime import timedelta
import json
import unittest

from lab.native_readback_fixture import Fixture
from tools import openstack_observe as o
from provisioner.execution.run_files import utcnow

PROJECT = '1bdef490bc60447c9877632b03933b33'
SERVER = 'bbfe612f-640a-408e-a0d4-a363a263f4bb'
VOLUME = '87a26cce-9d57-4d94-aa65-6446a01de433'
IMAGE = '7b594f30-3714-4843-8bb3-3a4a7f7cdb57'


def manifest(origin):
    scope = dict(environment_key='qualification-01', site_key='site-01', platform='openstack',
                 tenant_key='tenant-01', wsd_key='wsd-01')
    server = {'id': SERVER, 'tenant_id': PROJECT, 'status': 'ACTIVE',
              'OS-EXT-STS:task_state': None, 'OS-EXT-STS:power_state': 1,
              'OS-EXT-AZ:availability_zone': 'az-oz', 'OS-EXT-SRV-ATTR:host': 'compute-01',
              'OS-EXT-SRV-ATTR:hypervisor_hostname': 'compute-01.internal',
              'flavor': {'vcpus': 2, 'ram': 4096, 'disk': 0, 'original_name': 'small'},
              'metadata': {'tenant_key': 'tenant-01'}, 'config_drive': 'True',
              'os-extended-volumes:volumes_attached': [{'id': VOLUME, 'delete_on_termination': False}]}
    volume = {'id': VOLUME, 'os-vol-tenant-attr:tenant_id': PROJECT, 'status': 'in-use',
              'size': 40, 'encrypted': True, 'bootable': 'true', 'availability_zone': 'storage-oz',
              'volume_type': 'encrypted', 'attachments': [{'server_id': SERVER, 'volume_id': VOLUME}],
              'metadata': {'tenant_key': 'tenant-01'}, 'volume_image_metadata': {'image_id': IMAGE}}
    image = {'id': IMAGE, 'owner': PROJECT, 'status': 'active', 'visibility': 'private',
             'protected': True, 'disk_format': 'qcow2', 'container_format': 'bare',
             'os_hash_algo': 'sha256', 'os_hash_value': 'a' * 64, 'min_disk': 40, 'min_ram': 1024}
    return {'format': 'hosting-openstack-readback/1', 'scope': scope, 'project_id': PROJECT,
            'endpoints': {'compute': origin + '/compute/v2.1', 'volume': origin + '/volume/v3/' + PROJECT,
                          'image': origin + '/image/v2'},
            'resources': [{'kind': kind, 'id': value['id'], 'expected': value}
                          for kind, value in [('server', server), ('volume', volume), ('image', image)]]}


class OpenStackReadbackTests(unittest.TestCase):
    def setUp(self):
        self.f = Fixture(); self.addCleanup(self.f.close)
        self.m = manifest(self.f.origin)
        self.authority = {'valid_from': (utcnow() - timedelta(minutes=1)).isoformat(),
                          'valid_until': (utcnow() + timedelta(minutes=5)).isoformat()}
        self.paths = []
        for resource in self.m['resources']:
            service, collection, envelope, version, _ = o.KINDS[resource['kind']]
            path = self.m['endpoints'][service][len(self.f.origin):] + '/' + collection + '/' + resource['id']
            self.paths.append(path)
            self.f.routes[path] = {'body': {envelope: copy.deepcopy(resource['expected'])} if envelope else copy.deepcopy(resource['expected']),
                                   'headers': [('OpenStack-API-Version', version)] if version else []}

    def observe(self):
        return o.observe(self.m, o.Client(self.m, 'fixture-token', (self.f.directory / 'ca.pem').read_bytes(), self.authority))

    def test_real_tls_six_gets_exact_objects_no_mutations(self):
        r = self.observe()
        self.assertEqual(r['status'], 'OBSERVED_MATCH_NOT_QUALIFIED')
        self.assertFalse(r['production_qualified']); self.assertFalse(r['mutations_performed'])
        self.assertEqual(len(self.f.requests), 6)
        self.assertTrue(all(q['method'] == 'GET' and q['path'] in self.paths for q in self.f.requests))

    def test_native_drift_and_missing_restricted_fields_hold(self):
        for index, key, value in [(0, 'OS-EXT-SRV-ATTR:host', 'other-host'),
                                  (0, 'tenant_id', 'foreign-project'), (0, 'OS-EXT-STS:power_state', True),
                                  (0, 'os-extended-volumes:volumes_attached', []),
                                  (1, 'encrypted', False), (1, 'attachments', []), (2, 'os_hash_value', 'b' * 64)]:
            with self.subTest(key=key):
                body = self.f.routes[self.paths[index]]['body']
                envelope = o.KINDS[self.m['resources'][index]['kind']][2]
                target = body[envelope] if envelope else body
                original = target[key]; target[key] = value
                self.assertEqual(self.observe()['status'], 'HOLD'); target[key] = original
        del self.f.routes[self.paths[0]]['body']['server']['OS-EXT-SRV-ATTR:host']
        self.assertEqual(self.observe()['status'], 'HOLD')

    def test_unstable_then_matching_object_holds(self):
        def hook(path, count, spec):
            if path == self.paths[0] and count == 1: spec['body']['server']['status'] = 'BUILD'
            return spec
        self.f.hook = hook
        self.assertEqual(self.observe()['status'], 'HOLD')

    def test_transport_and_microversion_failures_hold(self):
        original = copy.deepcopy(self.f.routes[self.paths[0]])
        for patch in [{'status': 302}, {'status': 403}, {'headers': []},
                      {'headers': [('OpenStack-API-Version', 'compute 2.78')]},
                      {'length': 20000000}, {'headers': [('Transfer-Encoding', 'chunked')]},
                      {'raw': b'{"server":{},"server":{}}'}, {'content_type': 'text/html'}]:
            with self.subTest(patch=patch):
                self.f.routes[self.paths[0]] = {**original, **patch}
                self.assertEqual(self.observe()['status'], 'HOLD')

    def test_expired_authority_makes_no_requests(self):
        self.authority['valid_until'] = (utcnow() - timedelta(seconds=1)).isoformat()
        self.assertEqual(self.observe()['status'], 'HOLD'); self.assertFalse(self.f.requests)

    def test_untrusted_ca_holds(self):
        with Fixture() as other:
            client = o.Client(self.m, 'fixture-token', (other.directory / 'ca.pem').read_bytes(), self.authority)
            self.assertEqual(o.observe(self.m, client)['status'], 'HOLD')

    def test_unexpected_native_metadata_is_not_reported(self):
        self.f.routes[self.paths[0]]['body']['server']['metadata']['password'] = 'SENTINEL'
        self.assertNotIn('SENTINEL', json.dumps(self.observe()))

    def test_manifest_rejects_foreign_and_unsafe_expectations(self):
        for key, value in [('tenant_id', 'foreign'), ('config_drive', ''),
                           ('OS-EXT-STS:task_state', 'migrating'), ('OS-EXT-STS:power_state', True)]:
            m = copy.deepcopy(self.m); m['resources'][0]['expected'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): o.validate(m)
        for endpoint in ['http://localhost/v2.1', self.f.origin + '/v2.1?x=1',
                         self.f.origin + '/v2.1/other-project']:
            m = copy.deepcopy(self.m); m['endpoints']['compute'] = endpoint
            with self.assertRaises(ValueError): o.validate(m)


if __name__ == '__main__': unittest.main()
