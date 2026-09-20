import copy
import unittest
from unittest.mock import patch

from lab import run_namespace_lab as lab


class HostConfigurationFingerprintTests(unittest.TestCase):
    def snapshot(self):
        return {'namespace': 'net:[1]', 'links': [{'ifname': 'eth0', 'mtu': 1500, 'flags': ['UP', 'BROADCAST']}],
                'addresses': [{'local': '192.0.2.1', 'valid_life_time': 100, 'preferred_life_time': 90}],
                'ipv4_routes': [{'dst': '192.0.2.0/24', 'gateway': '198.51.100.1', 'metric': 10},
                                {'dst': '198.51.100.0/24', 'dev': 'eth0'}], 'ipv4_forwarding': '0'}

    def test_order_and_elapsed_lifetimes_are_not_configuration(self):
        before = self.snapshot(); after = copy.deepcopy(before)
        after['links'][0]['flags'].reverse(); after['ipv4_routes'].reverse()
        after['addresses'][0]['valid_life_time'] -= 5
        after['addresses'][0]['preferred_life_time'] -= 5
        after['links'][0]['stats64'] = {'rx': {'packets': 10}}
        self.assertEqual(lab.configuration_digest(before), lab.configuration_digest(after))

    def test_real_configuration_changes_always_change_fingerprint(self):
        mutations = [('links', 'mtu', 9000), ('addresses', 'local', '192.0.2.2'),
                     ('ipv4_routes', 'gateway', '198.51.100.2'), ('ipv4_routes', 'metric', 11)]
        before = self.snapshot()
        for section, field, value in mutations:
            with self.subTest(field=field):
                after = copy.deepcopy(before); after[section][0][field] = value
                self.assertNotEqual(lab.configuration_digest(before), lab.configuration_digest(after))
        after = copy.deepcopy(before); after['ipv4_forwarding'] = '1'
        self.assertNotEqual(lab.configuration_digest(before), lab.configuration_digest(after))

    def test_ipv4_parent_uses_canonical_full_snapshot(self):
        before = self.snapshot(); after = copy.deepcopy(before); after['ipv4_routes'].reverse()
        with patch.object(lab, 'configuration_snapshot', side_effect=[before, after]):
            self.assertEqual(lab.host_fingerprint(), lab.host_fingerprint())
