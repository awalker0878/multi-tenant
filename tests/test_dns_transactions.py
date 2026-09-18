from __future__ import annotations
import base64
import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import secrets
import tempfile
import unittest
from unittest.mock import patch
import uuid
import dns.message
import dns.query
import dns.rdatatype
import dns.exception
from tools import dns_change as d
from lab.dns_authority import Authority


def example(port, *, zone='fixture.invalid.', name='app.fixture.invalid.', rtype='A', value='192.0.2.10'):
    job = dict(version=1, enabled=True, operation_id=str(uuid.uuid4()), tenant_id='tenant-001',
               resource_id='workload-001', zone=zone, server='127.0.0.1', port=port,
               key_name='owner.fixture.invalid.', engineering_record_ref='LOCAL-FIXTURE-NOT-APPROVAL',
               valid_until=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat(),
               previous_marker=None, records=[dict(name=name, type=rtype, before=None,
                                                   after={'ttl': 60, 'values': [value]})])
    scope = {k: copy.deepcopy(v) for k,v in job.items() if k not in ('previous_marker','records')}
    scope.update(transport_acceptance_ref='LOCAL-LOOPBACK-TEST-ONLY', allowed_records=[
        dict(name=name,type=rtype,values=[value],maximum_ttl=300)])
    return job,scope


class DNSWireTests(unittest.TestCase):
    def setUp(self):
        self.secret = base64.b64encode(secrets.token_bytes(32)).decode()
        self.server = Authority('fixture.invalid.', 'owner.fixture.invalid.', self.secret).__enter__()
        self.addCleanup(self.server.__exit__, None,None,None)
        self.job,self.scope = example(self.server.port)
        self.server.allow(d.marker_name(self.job), *d.name_markers(self.job), *[r['name'] for r in self.job['records']])
        self.client = d.Client(self.job['server'],self.server.port,self.job['key_name'],self.secret,timeout=.3)

    def run_change(self, execute=True):
        return d.change(self.job,self.scope,self.client,execute=execute,fixture=True)

    def next_job(self, value):
        before = copy.deepcopy(self.job['records'][0]['after'])
        old = d.marker_value(self.job)
        self.job['operation_id'] = self.scope['operation_id'] = str(uuid.uuid4())
        self.job['previous_marker']=old
        self.job['records'][0]['before']=before
        self.job['records'][0]['after']=value
        if value:
            self.scope['allowed_records'][0]['values'] = sorted(set((before or {'values':[]})['values']+value['values']))

    def test_simultaneous_first_claims_have_one_native_winner(self):
        from concurrent.futures import ThreadPoolExecutor
        import threading
        other,scope=example(self.server.port,value='192.0.2.11')
        other['tenant_id']=scope['tenant_id']='tenant-002'
        self.server.allow(d.marker_name(other),*d.name_markers(other))
        barrier=threading.Barrier(2)
        def record(r):
            if r['events'][-1]['stage']=='UPDATE_PENDING':barrier.wait(timeout=2)
        def run(job,accepted):
            return d.change(job,accepted,d.Client('127.0.0.1',self.server.port,job['key_name'],self.secret),
                            execute=True,fixture=True,record=record)
        with ThreadPoolExecutor(max_workers=2) as pool:
            first=pool.submit(run,self.job,self.scope);second=pool.submit(run,other,scope)
            results=[first.result(),second.result()]
        self.assertEqual(sorted(x['status'] for x in results),['APPLIED_OBSERVED','PREREQUISITE_CONFLICT'])
        self.assertEqual(self.server.commits,1)

    def test_real_signed_create(self):
        result=self.run_change()
        self.assertEqual(result['status'],'APPLIED_OBSERVED')
        self.assertEqual(self.server.commits,1)
        self.assertFalse(result['activation_authorized'])
        self.assertTrue(d.matches(d.snapshot(self.job,self.client),self.job,'after'))

    def test_name_tombstone_prevents_another_owner_reclaim(self):
        self.run_change();self.next_job(None);self.run_change()
        self.job,self.scope=example(self.server.port)
        self.job['tenant_id']=self.scope['tenant_id']='tenant-002'
        self.job['resource_id']=self.scope['resource_id']='other-workload'
        self.server.allow(d.marker_name(self.job),*d.name_markers(self.job))
        self.assertEqual(self.run_change()['status'],'CONFLICT_NO_UPDATE')
        self.assertEqual(self.server.commits,2)

    def test_cross_family_name_takeover_is_blocked(self):
        self.run_change()
        self.job,self.scope=example(self.server.port,rtype='AAAA',value='2001:db8::10')
        self.job['tenant_id']=self.scope['tenant_id']='tenant-002'
        self.server.allow(d.marker_name(self.job),*d.name_markers(self.job))
        self.assertEqual(self.run_change()['status'],'CONFLICT_NO_UPDATE')
        self.assertNotIn(('app.fixture.invalid.','AAAA'),self.server.store)

    def test_first_name_claim_rejects_existing_unmanaged_other_type(self):
        self.server.set('app.fixture.invalid.','AAAA',60,['2001:db8::10'])
        self.assertEqual(self.run_change()['status'],'PREREQUISITE_CONFLICT')
        self.assertEqual(self.server.commits,0)

    def test_readonly_does_not_update(self):
        self.assertEqual(self.run_change(False)['status'],'READY_FOR_INDEPENDENT_REVIEW_NO_UPDATE')
        self.assertEqual(self.server.update_requests,0)

    def test_replay_does_not_update_twice(self):
        self.run_change()
        self.assertEqual(self.run_change()['status'],'ALREADY_APPLIED_OBSERVED')
        self.assertEqual(self.server.update_requests,1)

    def test_owned_update_then_delete_retains_tombstone(self):
        self.run_change();self.next_job({'ttl':120,'values':['192.0.2.11']})
        self.assertEqual(self.run_change()['status'],'APPLIED_OBSERVED')
        self.next_job(None)
        self.assertEqual(self.run_change()['status'],'APPLIED_OBSERVED')
        self.assertNotIn(('app.fixture.invalid.','A'),self.server.store)
        self.assertIn((d.marker_name(self.job),'TXT'),self.server.store)
        self.assertEqual(self.run_change()['status'],'ALREADY_APPLIED_OBSERVED')

    def test_lost_reply_readback_reconciles_without_retry(self):
        self.server.drop_update_reply=True
        self.assertEqual(self.run_change()['status'],'RECONCILED_APPLIED_OBSERVED')
        self.assertEqual(self.server.update_requests,1)

    def test_lost_reply_and_readback_does_not_retry_or_rollback(self):
        self.server.drop_update_reply=True;self.server.fail_after_commit=True
        self.assertEqual(self.run_change()['status'],'UNKNOWN_OUTCOME_OPERATOR_RECONCILIATION')
        self.assertEqual(self.server.commits,1)
        self.assertEqual(self.server.update_requests,1)

    def test_acknowledged_write_but_no_readback_is_inconclusive(self):
        self.server.fail_after_commit=True
        self.assertEqual(self.run_change()['status'],'APPLIED_READBACK_INCONCLUSIVE')
        self.assertEqual(self.server.commits,1)

    def test_racing_foreign_record_fails_authority_prerequisite(self):
        self.server.before_update=lambda a:a.set('app.fixture.invalid.','A',60,['192.0.2.99'])
        self.assertEqual(self.run_change()['status'],'PREREQUISITE_CONFLICT')
        self.assertEqual(self.server.commits,0)
        self.assertNotIn((d.marker_name(self.job),'TXT'),self.server.store)

    def test_racing_cname_fails_prerequisite(self):
        self.server.before_update=lambda a:a.set('app.fixture.invalid.','CNAME',60,['other.fixture.invalid.'])
        self.assertEqual(self.run_change()['status'],'PREREQUISITE_CONFLICT')
        self.assertEqual(self.server.commits,0)

    def test_existing_foreign_record_not_adopted(self):
        self.server.set('app.fixture.invalid.','A',60,['192.0.2.99'])
        self.assertEqual(self.run_change()['status'],'CONFLICT_NO_UPDATE')
        self.assertEqual(self.server.update_requests,0)

    def test_foreign_marker_is_not_accepted(self):
        self.server.set(d.marker_name(self.job),'TXT',300,['foreign'])
        self.assertEqual(self.run_change()['status'],'CONFLICT_NO_UPDATE')
        self.assertEqual(self.server.update_requests,0)

    def test_existing_alias_is_not_followed(self):
        self.server.set('app.fixture.invalid.','CNAME',60,['other.fixture.invalid.'])
        self.assertEqual(self.run_change()['status'],'INCONCLUSIVE_NO_UPDATE')
        self.assertEqual(self.server.update_requests,0)

    def test_unsigned_reply_is_not_authority(self):
        self.server.unsigned_answers=True
        self.assertEqual(self.run_change()['status'],'INCONCLUSIVE_NO_UPDATE')
        self.assertEqual(self.server.update_requests,0)

    def test_non_authoritative_reply_is_not_evidence(self):
        self.server.authoritative_answers=False
        self.assertEqual(self.run_change()['status'],'INCONCLUSIVE_NO_UPDATE')
        self.assertEqual(self.server.update_requests,0)

    def test_negative_without_soa_is_not_absence(self):
        self.server.omit_negative_soa=True
        self.assertEqual(self.run_change()['status'],'INCONCLUSIVE_NO_UPDATE')
        self.assertEqual(self.server.update_requests,0)

    def test_bad_key_never_updates(self):
        self.client=d.Client('127.0.0.1',self.server.port,self.job['key_name'],base64.b64encode(b'z'*32).decode(),timeout=.3)
        self.assertEqual(self.run_change()['status'],'INCONCLUSIVE_NO_UPDATE')
        self.assertEqual(self.server.update_requests,0)

    def test_authority_acl_refuses_ungranted_name(self):
        self.server.allowed_names.remove('app.fixture.invalid.')
        self.assertEqual(self.run_change()['status'],'UPDATE_REJECTED')
        self.assertEqual(self.server.commits,0)

    def test_authority_refusal_is_not_retried(self):
        self.server.refuse_updates=True
        self.assertEqual(self.run_change()['status'],'UPDATE_REJECTED')
        self.assertEqual(self.server.update_requests,1)

    def test_actual_wire_aaaa_and_a_are_one_transaction(self):
        self.job['records'].append(dict(name='app.fixture.invalid.',type='AAAA',before=None,after={'ttl':60,'values':['2001:db8::10']}))
        self.scope['allowed_records'].append(dict(name='app.fixture.invalid.',type='AAAA',values=['2001:db8::10'],maximum_ttl=300))
        self.assertEqual(self.run_change()['status'],'APPLIED_OBSERVED')
        self.assertEqual(self.server.commits,1)
        self.assertIn(('app.fixture.invalid.','AAAA'),self.server.store)

    def test_atomic_group_conflict_leaves_other_type_absent(self):
        self.job['records'].append(dict(name='app.fixture.invalid.',type='AAAA',before=None,after={'ttl':60,'values':['2001:db8::10']}))
        self.scope['allowed_records'].append(dict(name='app.fixture.invalid.',type='AAAA',values=['2001:db8::10'],maximum_ttl=300))
        self.server.before_update=lambda a:a.set('app.fixture.invalid.','AAAA',60,['2001:db8::99'])
        self.assertEqual(self.run_change()['status'],'PREREQUISITE_CONFLICT')
        self.assertNotIn(('app.fixture.invalid.','A'),self.server.store)
        self.assertNotIn((d.marker_name(self.job),'TXT'),self.server.store)

    def test_exact_rrset_prerequisite_rejects_extra_value_race(self):
        self.run_change(); self.next_job({'ttl':60,'values':['192.0.2.11']})
        self.server.before_update=lambda a:a.set('app.fixture.invalid.','A',60,['192.0.2.10','192.0.2.12'])
        self.assertEqual(self.run_change()['status'],'PREREQUISITE_CONFLICT')
        self.assertEqual(self.server.commits,1)

    def test_ttl_drift_detected_by_before_read_not_prerequisite(self):
        self.run_change();self.next_job({'ttl':60,'values':['192.0.2.11']})
        self.server.store[('app.fixture.invalid.','A')]['ttl']=61
        self.assertEqual(self.run_change()['status'],'CONFLICT_NO_UPDATE')
        self.assertEqual(self.server.commits,1)

    def test_pending_journal_failure_prevents_send(self):
        def write(r):
            if r['events'][-1]['stage']=='UPDATE_PENDING': raise OSError('write failed')
        with self.assertRaises(OSError):
            d.change(self.job,self.scope,self.client,execute=True,fixture=True,record=write)
        self.assertEqual(self.server.update_requests,0)

    def test_expiry_rechecked_after_observation(self):
        original=d.snapshot
        def delayed(job,client):
            result=original(job,client)
            job['valid_until']='2000-01-01T00:00:00Z'
            return result
        with patch.object(d,'snapshot',side_effect=delayed):
            with self.assertRaises(d.DNSChangeError): self.run_change()
        self.assertEqual(self.server.update_requests,0)

    def test_output_does_not_contain_secret(self):
        result=self.run_change()
        self.assertNotIn(self.secret,json.dumps(result))
        self.assertNotIn('192.0.2.10',json.dumps(result))

    def test_disabled_prevents_reads_and_writes(self):
        self.job['enabled']=False
        with self.assertRaises(d.DNSChangeError):self.run_change()
        self.assertEqual(self.server.queries,0)

    def test_group_can_recreate_owned_tombstone(self):
        self.run_change();self.next_job(None);self.run_change()
        self.next_job({'ttl':60,'values':['192.0.2.10']})
        self.assertEqual(self.run_change()['status'],'APPLIED_OBSERVED')


class DNSInputTests(unittest.TestCase):
    def setUp(self):self.job,self.scope=example(5353)
    def reject(self):
        with self.assertRaises(d.DNSChangeError):d.validate(self.job,self.scope,fixture=True)
    def test_fixture_not_native(self):
        with self.assertRaises(d.DNSChangeError):d.validate(self.job,self.scope)
    def test_scope_diff(self): self.scope['tenant_id']='tenant-002';self.reject()
    def test_unsupported_type(self): self.scope['allowed_records'][0]['type']='NS';self.reject()
    def test_unknown_field(self):self.job['secret']='not-allowed';self.reject()
    def test_bool_version(self):self.scope['version']=True;self.reject()
    def test_unhashable_type(self):self.job['records'][0]['type']=[];self.reject()
    def test_wildcard(self):self.job['records'][0]['name']='*.fixture.invalid.';self.reject()
    def test_outside_zone(self):self.job['records'][0]['name']='x.outside.invalid.';self.reject()
    def test_unknown_allocation(self):self.job['records'][0]['after']['values']=['192.0.2.11'];self.reject()
    def test_unowned_adoption(self):self.job['records'][0]['before']=copy.deepcopy(self.job['records'][0]['after']);self.reject()
    def test_unsigned_prior_marker(self):self.job['previous_marker']='Approved';self.reject()
    def test_empty_records(self):self.job['records']=[];self.reject()
    def test_ttl_zero(self):self.job['records'][0]['after']['ttl']=0;self.reject()
    def test_values_unsorted(self):self.job['records'][0]['after']['values']=['192.0.2.11','192.0.2.10'];self.reject()
    def test_secret_short(self):
        with self.assertRaises(d.DNSChangeError):d.Client('127.0.0.1',53,'key.fixture.invalid.',base64.b64encode(b'x').decode())
    def test_bad_base64(self):
        with self.assertRaises(d.DNSChangeError):d.Client('127.0.0.1',53,'key.fixture.invalid.','not-base64')
    def test_native_write_without_journal_stops_before_contact(self):
        job,scope=example(53,zone='hosting.internal.',name='app.hosting.internal.',value='10.10.0.7')
        for obj in (job,scope):obj['server']='10.10.0.53'
        with self.assertRaisesRegex(d.DNSChangeError,'journal'):
            d.change(job,scope,None,execute=True)
    def test_native_valid_exact_private_target(self):
        job,scope=example(53,zone='hosting.internal.',name='app.hosting.internal.',value='10.10.0.7')
        for obj in (job,scope):obj['server']='10.10.0.53'
        d.validate(job,scope)
    def test_ptr_exact_reverse_wire(self):
        secret=base64.b64encode(secrets.token_bytes(32)).decode()
        with Authority('2.0.192.in-addr.arpa.','owner.fixture.invalid.',secret) as server:
            job,scope=example(server.port,zone='2.0.192.in-addr.arpa.',name='10.2.0.192.in-addr.arpa.',rtype='PTR',value='app.fixture.invalid.')
            server.allow(d.marker_name(job),*d.name_markers(job),job['records'][0]['name'])
            result=d.change(job,scope,d.Client('127.0.0.1',server.port,job['key_name'],secret),execute=True,fixture=True)
            self.assertEqual(result['status'],'APPLIED_OBSERVED')
    def test_ptr_bad_reverse(self):
        job,scope=example(53,rtype='PTR',value='app.fixture.invalid.')
        with self.assertRaises(d.DNSChangeError):d.validate(job,scope,fixture=True)
    def test_marker_bound_to_owner_and_group(self):
        marker=d.marker_value(self.job)
        self.job['records'][0]['before']=copy.deepcopy(self.job['records'][0]['after'])
        self.job['previous_marker']=marker
        self.job['resource_id']=self.scope['resource_id']='another-resource'
        self.reject()


if __name__=='__main__': unittest.main()
