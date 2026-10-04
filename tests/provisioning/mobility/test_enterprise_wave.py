"""Cross-tenant budget binding and fair-turn contract, without native claims."""
from dataclasses import replace
from datetime import timedelta
import unittest

from provisioner.migration.enterprise_wave import (
    EnterpriseWavePool, PoolDomain, fair_tenant_order)
from provisioner.migration.wave_schedule import WaveHeld
from tests.provisioning.mobility.test_wave_schedule import NOW, domain, member


class EnterpriseWaveContractTests(unittest.TestCase):
    def setUp(self):
        a, _ = member('pool-a')
        local = domain(a)
        b, _ = member('pool-b', tenant='tenant-other')
        remote = replace(local, tenant_id='tenant-other', domain_id='remote-domain',
                         scopes=tuple((scope, 'remote-risk') for scope in (b.source, b.destination)),
                         shared_risk_limits=(('remote-risk', 8),))
        self.local = PoolDomain.from_domain(local, {'shared-native-hosts': 'physical-hosts'})
        self.remote = PoolDomain.from_domain(remote, {'remote-risk': 'physical-hosts'})
        self.pool = EnterpriseWavePool('enterprise-pool', (self.local, self.remote),
            local.budget, (('physical-hosts', 8),), 'f'*64,
            NOW-timedelta(minutes=10), NOW+timedelta(days=1))

    def test_roundtrip_and_digest_ignore_domain_and_risk_map_order(self):
        self.assertEqual(EnterpriseWavePool.from_record(self.pool.to_record()), self.pool)
        self.assertEqual(replace(self.pool, domains=tuple(reversed(self.pool.domains))).digest,
                         self.pool.digest)
        value = self.pool.to_record()
        value['domains'][0]['domainDigest'] = '0'*64
        self.assertNotEqual(EnterpriseWavePool.from_record(value).digest, self.pool.digest)

    def test_tenant_authorities_cannot_split_waves_to_get_more_turns(self):
        a, b = ('org-01', 'tenant-a'), ('org-01', 'tenant-b')
        c = ('org-02', 'tenant-a')
        self.assertEqual(fair_tenant_order([a, a, a, b, c], a), (b, c, a))
        self.assertEqual(fair_tenant_order([a, b], c), (a, b))
        self.assertEqual(fair_tenant_order([b, a], ('org-01', 'tenant-aa')), (b, a))
        self.assertEqual(fair_tenant_order([], a), ())

    def test_complete_risk_map_and_aggregate_caps_are_mandatory(self):
        for changes in ({'shared_risk_limits': ()},
                        {'shared_risk_limits': (('another-host', 8),)},
                        {'shared_risk_limits': (('physical-hosts', True),)},
                        {'shared_risk_limits': (('physical-hosts', 9),)},
                        {'domains': (self.local, self.local)},
                        {'expires_at': NOW-timedelta(hours=1)},
                        {'expires_at': NOW+timedelta(days=32)}):
            with self.subTest(changes=changes), self.assertRaises(WaveHeld):
                replace(self.pool, **changes)
        with self.assertRaises(WaveHeld):
            replace(self.local, risk_groups=(('same-risk', 'a'), ('same-risk', 'b')))
        with self.assertRaises(WaveHeld):
            replace(self.pool, domains=(self.local, replace(self.local, domain_id='split-domain')))

    def test_strict_record_rejects_unknown_fields_and_ambiguous_primitive_values(self):
        value = self.pool.to_record()
        value['nativeContact'] = True
        with self.assertRaises(WaveHeld):
            EnterpriseWavePool.from_record(value)
        with self.assertRaises(WaveHeld):
            fair_tenant_order([('org-01', '../tenant')])
        with self.assertRaises(WaveHeld):
            fair_tenant_order([('org-01', 'tenant-a')], 'tenant-a')


if __name__ == '__main__':
    unittest.main()
