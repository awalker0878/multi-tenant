"""Signed TCP observations across independent fixture authorities and cache views."""
import base64
from copy import deepcopy
from datetime import timedelta
from pathlib import Path
import secrets
import tempfile
import unittest
from unittest.mock import patch
import uuid

import dns.exception
import dns.flags
import dns.message
import dns.name
import dns.rcode
import dns.rrset

from lab.dns_authority import Authority
from tests.test_dns_transactions import example
from provisioner.execution import readback_core as c
from provisioner.execution import dns_change as writer, dns_propagation as d, delivery_steps as steps
from provisioner.execution.run_files import digest, encoded, load_private, replace_private, utcnow, write_new


class Cache(Authority):
    """Signed wire fixture, not a claim of real recursive resolution/replication."""
    def respond(self, message):
        result = super().respond(message)
        result.flags &= ~dns.flags.AA
        result.flags |= dns.flags.RA
        return result


class PropagationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.servers = []; self.keys = {}; targets = []
        for role, klass in [('primary', Authority), ('secondary', Authority), ('recursive', Cache)]:
            secret = base64.b64encode(secrets.token_bytes(32)).decode(); self.keys[role] = secret
            server = klass('fixture.invalid.', 'owner.fixture.invalid.', secret).__enter__()
            self.addCleanup(server.__exit__, None, None, None); self.servers.append(server)
            targets.append(dict(id=role, role=role, server='127.0.0.1', port=server.port,
                key_name='owner.fixture.invalid.', tsig_sha256=digest(secret.encode()), view_ref='TEST-VIEW',
                control_name='health.fixture.invalid.', control_value='test-view-generation-1'))
        self.job, self.scope = example(self.servers[0].port)
        self.servers[0].allow(writer.marker_name(self.job), *writer.name_markers(self.job), self.job['records'][0]['name'])
        self.config = dict(format='hosting-dns-propagation/1', job_sha256='', scope_sha256='', receipt_sha256='',
            observer_machine_id=Path('/etc/machine-id').read_text().strip(),
            network_namespace_inode=Path('/proc/self/ns/net').stat().st_ino,
            valid_from=(utcnow()-timedelta(minutes=1)).isoformat(), valid_until=(utcnow()+timedelta(minutes=10)).isoformat(),
            observation_ref='TEST-ONLY', max_seconds=10, targets=targets)
        self.commit()

    def commit(self):
        primary = self.servers[0]
        result = writer.change(self.job, self.scope, writer.Client('127.0.0.1', primary.port,
            self.job['key_name'], self.keys['primary']), execute=True, fixture=True)
        self.assertIn(result['status'], writer.STATES)
        self.receipt = dict(format='hosting-netbox-dns-receipt/1',
            status='AUTHORITATIVE_TOMBSTONE_OBSERVED' if self.job['records'][0]['after'] is None else 'AUTHORITATIVE_REGISTRATION_OBSERVED',
            dns=result, activation_authorized=False, reusable=False)
        for server in self.servers:
            server.store = deepcopy(primary.store)
            server.set('health.fixture.invalid.', 'TXT', 60, ['test-view-generation-1'])
        for record in self.servers[-1].store.values(): record['ttl'] = max(0, record['ttl']-10)
        self.bind()

    def bind(self):
        self.config.update(job_sha256=c.digest(self.job), scope_sha256=c.digest(self.scope), receipt_sha256=c.digest(self.receipt))

    def observe(self): return d.observe(self.config, self.job, self.scope, self.receipt, self.keys, fixture=True)

    def test_signed_primary_secondary_and_decaying_recursive_ttls(self):
        result = self.observe()
        self.assertEqual(result['status'], d.STATUS); self.assertEqual(len(result['observations']), 6)
        self.assertFalse(result['reusable'] or result['activation_authorized'])
        self.assertEqual([s.update_requests for s in self.servers], [1, 0, 0])
        self.assertTrue(all(s.queries > 0 for s in self.servers))

    def test_stale_values_markers_and_inflated_cache_ttls_remain_held(self):
        server = self.servers[-1]; original = deepcopy(server.store)
        cases = [('app.fixture.invalid.', 'values', ['192.0.2.99']),
                 (writer.marker_name(self.job), 'values', ['old-generation']),
                 (writer.name_markers(self.job)[0], 'values', ['foreign-owner']),
                 ('app.fixture.invalid.', 'ttl', 61)]
        for name, field, value in cases:
            server.store = deepcopy(original)
            server.store[(name, 'A' if name == 'app.fixture.invalid.' else 'TXT')][field] = value
            with self.subTest(field=field, name=name), self.assertRaisesRegex(ValueError, 'propagation'):
                self.observe()
        self.assertEqual([s.update_requests for s in self.servers], [1, 0, 0])

    def test_tombstones_require_every_view_to_lose_old_data_and_keep_ownership(self):
        before = deepcopy(self.job['records'][0]['after']); old_marker = writer.marker_value(self.job)
        self.job['operation_id'] = self.scope['operation_id'] = str(uuid.uuid4())
        self.job['previous_marker'] = old_marker; self.job['records'][0].update(before=before, after=None)
        self.commit()
        self.assertEqual(self.observe()['status'], d.STATUS)
        self.servers[-1].set('app.fixture.invalid.', 'A', 1, before['values'])
        with self.assertRaisesRegex(ValueError, 'propagation'): self.observe()
        del self.servers[-1].store[('app.fixture.invalid.', 'A')]
        self.servers[-1].omit_negative_soa = True
        with self.assertRaisesRegex(ValueError, 'exact zone SOA'): self.observe()
        self.assertEqual([s.update_requests for s in self.servers], [2, 0, 0])

    def test_unsigned_answers_unavailable_recursion_servfail_aliases_and_wrong_soa_are_inconclusive(self):
        server = self.servers[-1]; respond = server.respond
        def fault(mode):
            def response(message):
                result = respond(message)
                if mode == 'unsigned': result.tsig = None
                if mode == 'no_recursion': result.flags &= ~dns.flags.RA
                if mode == 'authoritative': result.flags |= dns.flags.AA
                if mode == 'servfail': result.set_rcode(dns.rcode.SERVFAIL)
                if mode == 'alias': result.answer.append(dns.rrset.from_text(str(message.question[0].name), 30, 'IN', 'CNAME', 'other.fixture.invalid.'))
                if mode == 'wrong_soa' and result.authority: result.authority[0].name = dns.name.from_text('elsewhere.invalid.')
                return result
            return response
        for mode in ('unsigned', 'no_recursion', 'authoritative', 'servfail', 'alias', 'wrong_soa'):
            with self.subTest(mode=mode), patch.object(server, 'respond', side_effect=fault(mode)), \
                    self.assertRaises((ValueError, dns.exception.DNSException)):
                self.observe()

    def test_second_sweep_detects_reversion_and_positive_control_mismatch(self):
        primary = self.servers[0]; cache = self.servers[-1]; respond = cache.respond; calls = 0
        def revert(message):
            nonlocal calls
            result = respond(message)
            if str(message.question[0].name) == 'health.fixture.invalid.':
                calls += 1
                if calls == 2: primary.set(writer.marker_name(self.job), 'TXT', 300, ['reverted'])
            return result
        with patch.object(cache, 'respond', side_effect=revert), self.assertRaisesRegex(ValueError, 'propagation'):
            self.observe()
        primary.set('health.fixture.invalid.', 'TXT', 60, ['wrong-view'])
        with self.assertRaisesRegex(ValueError, 'positive control'): self.observe()

    def test_wrong_keys_host_scope_receipt_or_target_coverage_rejected_before_contact(self):
        original = deepcopy(self.config); queries = [s.queries for s in self.servers]
        for mode in ('key', 'host', 'namespace', 'receipt', 'missing', 'duplicate', 'primary_alias', 'expired'):
            self.config = deepcopy(original)
            if mode == 'key': self.config['targets'][-1]['tsig_sha256'] = '0'*64
            if mode == 'host': self.config['observer_machine_id'] = '0'*32
            if mode == 'namespace': self.config['network_namespace_inode'] += 1
            if mode == 'receipt': self.config['receipt_sha256'] = '0'*64
            if mode == 'missing': self.config['targets'].pop()
            if mode == 'duplicate': self.config['targets'][-1]['id'] = 'secondary'
            if mode == 'primary_alias': self.config['targets'][-1]['port'] = self.servers[0].port
            if mode == 'expired': self.config['valid_until'] = (utcnow()-timedelta(seconds=1)).isoformat()
            with self.subTest(mode=mode), self.assertRaises(ValueError): self.observe()
            self.assertEqual([s.queries for s in self.servers], queries)

    def test_retained_receipt_cannot_omit_views_change_generation_or_invent_time(self):
        original = self.observe()
        d.validate_result(original,self.config,self.job,self.scope,self.receipt)
        for mode in ('missing', 'reordered', 'generation', 'future'):
            value = deepcopy(original)
            if mode == 'missing': value['observations'].pop()
            if mode == 'reordered': value['observations'].reverse()
            if mode == 'generation': value['observations'][0]['snapshot']['marker']['values'] = ['other-generation']
            if mode == 'future': value['finished_at'] = (utcnow()+timedelta(minutes=1)).isoformat()
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                d.validate_result(value,self.config,self.job,self.scope,self.receipt)

    def test_expired_write_is_readable_with_fresh_observation_and_bounded_timeout(self):
        for record in (self.job, self.scope): record['valid_until'] = (utcnow()-timedelta(seconds=1)).isoformat()
        self.receipt['dns'].update(job_sha256=c.digest(self.job), scope_sha256=c.digest(self.scope)); self.bind()
        self.assertEqual(self.observe()['status'], d.STATUS)
        with patch.object(d.time, 'monotonic', side_effect=[0, 11]), self.assertRaisesRegex(ValueError, 'budget'):
            self.observe()

    def test_reverse_zone_PTR_propagates_with_its_own_generation(self):
        zone = '2.0.192.in-addr.arpa.'
        self.job,self.scope = example(self.servers[0].port,zone=zone,name='10.'+zone,rtype='PTR',value='app.fixture.invalid.')
        for target,server in zip(self.config['targets'],self.servers):
            server.zone = dns.name.from_text(zone); server.store.clear()
            target['control_name'] = 'health.'+zone
        self.servers[0].allow(writer.marker_name(self.job),*writer.name_markers(self.job),self.job['records'][0]['name'])
        self.commit()
        for server in self.servers: server.set('health.'+zone,'TXT',60,['test-view-generation-1'])
        self.assertEqual(self.observe()['status'],d.STATUS)

    def delivery(self):
        base = self.base/'run'; upstream = base/'steps/dns'; upstream.mkdir(parents=True, mode=0o700)
        directory = base/'steps/propagation'; directory.mkdir(mode=0o700)
        scope = dict(environment_key='lab', site_key='site-01', platform='openstack', tenant_key='tenant-001', wsd_key='wsd-01')
        def file(name, value):
            path = self.base/(name+'.json'); write_new(path, encoded(value))
            return dict(path=str(path), sha256=digest(path.read_bytes()))
        parent = dict(files={key:file(key, value) for key,value in [('job',self.job),('scope',self.scope),('allocation',{'scope':scope})]})
        write_new(upstream/'packet.json', encoded(parent)); write_new(upstream/'result.json', encoded(self.receipt))
        step = dict(id='propagation', kind='dns_propagation', needs=['dns'])
        plan = dict(scope=scope, steps=[dict(id='dns',kind='dns',needs=[]),step])
        packet = dict(parameters={'dns_step':'dns'}, files={'config':file('config',self.config),'secrets':file('secrets',self.keys)})
        return step,packet,directory,base,plan,Path('.')

    def test_delivery_handoff_recovers_saved_observation_without_any_network_retry(self):
        args = self.delivery()
        validate, observe = d.validate, d.observe
        def fixture_validate(*args, **kwargs): return validate(*args, **(kwargs | {'fixture':True}))
        def fixture_observe(*args, **kwargs): return observe(*args, **(kwargs | {'fixture':True}))
        with patch.object(d,'validate',side_effect=fixture_validate), patch.object(d,'observe',side_effect=fixture_observe), \
                patch.object(steps,'complete',side_effect=InterruptedError), self.assertRaises(InterruptedError):
            steps.dispatch(*args)
        with patch.object(d,'validate',side_effect=fixture_validate), patch.object(d,'observe',side_effect=AssertionError('network replay')):
            result,names = steps.recover(*args)
            self.assertEqual(result['status'],d.STATUS); self.assertIn('owner-completion.json',names)
        self.assertEqual([s.update_requests for s in self.servers], [1,0,0])

    def test_incomplete_read_renews_window_only_and_never_reissues_update(self):
        args = self.delivery(); validate,observe = d.validate,d.observe
        def fixture_validate(*args, **kwargs): return validate(*args, **(kwargs | {'fixture':True}))
        def fixture_observe(*args, **kwargs): return observe(*args, **(kwargs | {'fixture':True}))
        with patch.object(d,'validate',side_effect=fixture_validate), patch.object(d,'observe',side_effect=InterruptedError), \
                self.assertRaises(InterruptedError):
            steps.dispatch(*args)
        renewed = deepcopy(self.config); renewed['observation_ref'] = 'TEST-RENEWAL'
        renewed['valid_until'] = (utcnow()+timedelta(minutes=15)).isoformat()
        path = self.base/'renewal.json'; changed = deepcopy(renewed); changed['targets'][-1]['view_ref'] = 'OTHER-VIEW'
        write_new(path,encoded(changed))
        with patch.object(d,'observe',side_effect=AssertionError('changed view contacted')), self.assertRaisesRegex(ValueError,'renewal'):
            steps.recover(*args,recovery_authority=path)
        replace_private(path,encoded(renewed))
        with patch.object(d,'validate',side_effect=fixture_validate), patch.object(d,'observe',side_effect=fixture_observe):
            result,_ = steps.recover(*args,recovery_authority=path)
        self.assertEqual(result['status'],d.STATUS)
        self.assertEqual([s.update_requests for s in self.servers], [1,0,0])


if __name__ == '__main__': unittest.main()
