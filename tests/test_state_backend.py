import unittest
from provisioner.execution.state_backend import compile_backend


class StateBackendTests(unittest.TestCase):
    def test_each_writer_scope_has_a_distinct_locked_state(self):
        scope = dict(environment_key='dev', site_key='site-a', platform='nutanix',
                     tenant_key='tenant-a', wsd_key='science', phase='domains')
        first = compile_backend('https://gitlab.example.com', 20, scope)
        self.assertEqual(first['lock_address'], first['address'] + '/lock')
        for key, value in dict(environment_key='prod', site_key='site-b', platform='vmware',
                               tenant_key='tenant-b', wsd_key='portal', phase='workloads').items():
            with self.subTest(key=key):
                self.assertNotEqual(first['address'], compile_backend('https://gitlab.example.com', 20,
                                                                      scope | {key: value})['address'])
        self.assertNotEqual(first['address'], compile_backend('https://gitlab.example.com', 21, scope)['address'])

    def test_rejects_credential_and_path_injection(self):
        scope = dict(environment_key='dev', site_key='site-a', platform='openstack',
                     tenant_key='tenant-a', wsd_key='science', phase='workloads')
        for origin in ['http://gitlab.example.com', 'https://user:secret@gitlab.example.com',
                       'https://gitlab.example.com/?token=x', 'https://gitlab.example.com/other']:
            with self.subTest(origin=origin), self.assertRaises(ValueError):
                compile_backend(origin, 20, scope)
