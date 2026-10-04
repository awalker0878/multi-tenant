"""Actual fleet SQL role, cross-tenant ceilings, immutable starts and lost work.

These disposable DB campaigns qualify coordinator software only. They are not
native platform scale, deployed service enrollment or independent fence proof.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime,timezone,timedelta
import hashlib
import json
import os
import threading
import time
import unittest
from uuid import uuid4

from provisioner.controlplane.authority.model import PlanScope
from provisioner.controlplane.discovery.fleet_read_budget import bucket_ids
from provisioner.controlplane.discovery.model import _json


@unittest.skipUnless(os.environ.get('HOSTING_TEST_POSTGRES_FLEET_DSN') and
                     os.environ.get('HOSTING_TEST_POSTGRES_MIGRATION_DSN') and
                     os.environ.get('HOSTING_TEST_POSTGRES_ISOLATED')=='1',
                     'Requires isolated PostgreSQL enrolled fleet admission role')
class FleetBudgetPostgresTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import psycopg
        cls.psycopg=psycopg
        cls.dsn=os.environ['HOSTING_TEST_POSTGRES_FLEET_DSN']
        cls.owner_dsn=os.environ['HOSTING_TEST_POSTGRES_MIGRATION_DSN']
        from psycopg.conninfo import conninfo_to_dict
        cls.role=conninfo_to_dict(cls.dsn)['user']

    def setUp(self):
        self.fleet='fleet-'+uuid4().hex;self.worker='worker-1';self.service='a'*64;self.policy='b'*64
        self.scope=PlanScope('org-'+uuid4().hex,'tenant-1','site-1','wsd-1','endpoint-1','native-1','vmware')
        self.instance=uuid4().hex;self.fence='c'*64

    def commission(self,scopes=None,limits=None):
        scopes=[self.scope] if scopes is None else scopes
        limits={} if limits is None else limits
        until=datetime.now(timezone.utc)+timedelta(minutes=10)
        with self.psycopg.connect(self.owner_dsn) as con:
            con.execute('INSERT INTO hosting_controlplane.discovery_fleets VALUES(%s,%s,%s,true,%s)',
                        (self.fleet,self.policy,self.fence,until))
            con.execute('INSERT INTO hosting_controlplane.discovery_fleet_workers VALUES(%s,%s,%s,%s,true,%s)',
                        (self.fleet,self.worker,self.role,self.service,until))
            seen=set()
            for index,scope in enumerate(scopes):
                buckets=bucket_ids(scope)
                for kind,key in zip(('TOTAL','ORGANIZATION','TENANT','WSD','ENDPOINT'),buckets):
                    if key in seen:continue
                    seen.add(key)
                    cap,interval,maximum=limits.get(kind,(16,1,1000))
                    con.execute('INSERT INTO hosting_controlplane.discovery_fleet_limits VALUES(%s,%s,%s,%s,%s,%s)',
                                (self.fleet,key,kind,cap,interval,maximum))
                con.execute('INSERT INTO hosting_controlplane.discovery_fleet_scopes VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
                            (self.fleet,self.worker,scope.organization_id,scope.tenant_id,scope.site_id,
                             scope.security_domain_id,scope.endpoint_id,scope.native_scope_id,scope.platform_family,
                             'environment-'+str(index),'collector-1',list(buckets)))

    def request(self,scope=None,environment='environment-0',duration=10):
        scope=self.scope if scope is None else scope
        return {'format':'hosting-discovery-fleet-read/1','leaseId':uuid4().hex,'instanceId':self.instance,
            'organizationId':scope.organization_id,'tenantId':scope.tenant_id,'siteId':scope.site_id,
            'securityDomainId':scope.security_domain_id,'endpointId':scope.endpoint_id,'nativeScopeId':scope.native_scope_id,
            'platformFamily':scope.platform_family,'environmentId':environment,'collectorId':'collector-1',
            'campaignDigest':'d'*64,'expiresAt':(datetime.now(timezone.utc)+timedelta(seconds=duration)).isoformat()}

    def admit(self,doc,dsn=None,service=None):
        raw=_json(doc);digest=hashlib.sha256(raw.encode('ascii')).hexdigest()
        with self.psycopg.connect(self.dsn if dsn is None else dsn) as con:
            row=con.execute('SELECT * FROM hosting_controlplane.discovery_fleet_admit(%s,%s,%s,%s,%s)',
                (self.fleet,self.worker,self.service if service is None else service,raw,digest)).fetchone()
        return row

    def close(self,doc,**changed):
        raw=_json(doc);args={'worker':self.worker,'service':self.service,'instance':doc['instanceId'],
                            'lease':doc['leaseId'],'digest':hashlib.sha256(raw.encode('ascii')).hexdigest()}
        args.update(changed)
        with self.psycopg.connect(self.dsn) as con:
            return con.execute('SELECT hosting_controlplane.discovery_fleet_close(%s,%s,%s,%s,%s,%s)',
                               (self.fleet,*args.values())).fetchone()[0]

    def test_actual_enrolled_role_cannot_read_write_tables_fence_or_alias_unrelated_logins(self):
        self.commission();doc=self.request();self.assertEqual(self.admit(doc)[0],'LEASE_STARTED')
        with self.psycopg.connect(self.dsn) as con:
            for table in ('discovery_fleets','discovery_fleet_limits','discovery_fleet_workers','discovery_fleet_leases','discovery_fleet_closes'):
                with self.subTest(table=table),self.assertRaises(self.psycopg.Error),con.transaction():
                    con.execute('SELECT * FROM hosting_controlplane.'+table)
            with self.assertRaises(self.psycopg.Error),con.transaction():
                con.execute('SELECT hosting_controlplane.discovery_fleet_fenced_close(%s,%s,%s,%s)',(self.fleet,'{}',self.fence,self.service))
        with self.assertRaises(self.psycopg.Error):self.admit(self.request(),dsn=self.owner_dsn)
        with self.assertRaises(self.psycopg.Error):self.admit(self.request(),service='f'*64)

    def test_each_global_dimension_limits_separate_instances_and_exact_native_scopes(self):
        variants={
            'TOTAL':replace(self.scope,organization_id='other-org',tenant_id='other-tenant',endpoint_id='other-endpoint'),
            'ORGANIZATION':replace(self.scope,tenant_id='other-tenant',endpoint_id='other-endpoint'),
            'TENANT':replace(self.scope,security_domain_id='other-wsd',endpoint_id='other-endpoint'),
            'WSD':replace(self.scope,endpoint_id='other-endpoint'),
            'ENDPOINT':replace(self.scope,tenant_id='other-tenant',native_scope_id='other-native'),
        }
        for dimension,scope in variants.items():
            self.fleet='fleet-'+uuid4().hex
            self.commission([self.scope,scope],{dimension:(1,1,1000)})
            first=self.request();self.assertEqual(self.admit(first)[0],'LEASE_STARTED')
            time.sleep(.01)
            second=self.request(scope,'environment-1');second['instanceId']=uuid4().hex
            with self.subTest(dimension=dimension):
                self.assertEqual(self.admit(second)[0],'THROTTLED')
                self.assertEqual(self.close(first),'LOCAL_SOCKET_CLOSED')
                self.assertEqual(self.admit(second)[0],'LEASE_STARTED')

    def test_concurrent_admission_counts_all_tenants_under_one_committed_lock(self):
        other=replace(self.scope,tenant_id='other-tenant',native_scope_id='other-native')
        self.commission([self.scope,other],{'ENDPOINT':(1,1,1000)})
        barrier=threading.Barrier(2)
        def read(index):
            barrier.wait(timeout=5)
            return self.admit(self.request(self.scope if index==0 else other,'environment-'+str(index)))[0]
        with ThreadPoolExecutor(max_workers=2) as pool:
            result=list(pool.map(read,range(2)))
        self.assertEqual(sorted(result),['LEASE_STARTED','THROTTLED'])
        with self.psycopg.connect(self.owner_dsn) as con:
            self.assertEqual(con.execute('SELECT count(*) FROM hosting_controlplane.discovery_fleet_leases WHERE fleet_id=%s',(self.fleet,)).fetchone(),(1,))

    def test_expiry_disconnect_and_duplicate_intent_never_release_unknown_work(self):
        self.commission(limits={'TOTAL':(1,1,1000)})
        doc=self.request(duration=.1);self.assertEqual(self.admit(doc)[0],'LEASE_STARTED')
        time.sleep(.15)
        self.assertEqual(self.admit(self.request())[0],'THROTTLED')
        doc['expiresAt']=(datetime.now(timezone.utc)+timedelta(seconds=10)).isoformat()
        self.assertEqual(self.admit(doc)[0],'LEASE_OUTCOME_UNKNOWN')
        with self.psycopg.connect(self.dsn) as con:
            history=con.execute('SELECT hosting_controlplane.discovery_fleet_inspect(%s,%s,%s)',(self.fleet,self.worker,self.service)).fetchone()[0]
        self.assertEqual(history['leases'][0]['status'],'EXPIRED_OUTCOME_UNKNOWN')

    def test_observed_close_requires_original_instance_request_and_is_immutable(self):
        self.commission();doc=self.request();self.admit(doc)
        for changed in ({'instance':uuid4().hex},{'digest':'f'*64},{'service':'f'*64},{'worker':'other-worker'}):
            with self.subTest(changed=changed),self.assertRaises(self.psycopg.Error):self.close(doc,**changed)
        self.assertEqual(self.close(doc),'LOCAL_SOCKET_CLOSED');self.assertEqual(self.close(doc),'ALREADY_CLOSED')
        with self.psycopg.connect(self.owner_dsn) as con:
            with self.assertRaises(self.psycopg.Error),con.transaction():
                con.execute('DELETE FROM hosting_controlplane.discovery_fleet_closes WHERE fleet_id=%s',(self.fleet,))

    def test_rate_and_lifetime_start_ceiling_survive_closes_and_restarts_without_refund(self):
        self.commission(limits={'TOTAL':(16,200,2)})
        first=self.request();self.assertEqual(self.admit(first)[0],'LEASE_STARTED');self.close(first)
        self.assertEqual(self.admit(self.request())[0],'THROTTLED')
        time.sleep(.21)
        second=self.request();self.assertEqual(self.admit(second)[0],'LEASE_STARTED');self.close(second)
        time.sleep(.21)
        self.assertEqual(self.admit(self.request())[0],'THROTTLED')

    def test_current_worker_revocation_scope_change_and_policy_reset_are_denied(self):
        self.commission();doc=self.request();self.admit(doc)
        wrong=self.request();wrong['nativeScopeId']='wrong'
        with self.assertRaises(self.psycopg.Error):self.admit(wrong)
        with self.psycopg.connect(self.owner_dsn) as con:
            with self.assertRaises(self.psycopg.Error),con.transaction():
                con.execute('UPDATE hosting_controlplane.discovery_fleet_limits SET max_started=2000 WHERE fleet_id=%s',(self.fleet,))
            con.execute('UPDATE hosting_controlplane.discovery_fleet_workers SET enabled=false WHERE fleet_id=%s',(self.fleet,))
        with self.assertRaises(self.psycopg.Error):self.admit(self.request())
        with self.assertRaises(self.psycopg.Error):self.close(doc)

    def test_independent_fence_receiver_is_exact_and_does_not_bypass_worker_identity(self):
        # The separate migration-owner connection stands in only as this
        # disposable campaign's explicitly enrolled fence receiver. Production
        # uses a dedicated receiver login and independently signed host proof.
        self.commission();doc=self.request();self.admit(doc)
        with self.psycopg.connect(self.owner_dsn) as con:
            role=con.execute('SELECT session_user').fetchone()[0]
            con.execute('INSERT INTO hosting_controlplane.discovery_fleet_fencers VALUES(%s,%s,%s,%s,true,%s)',
                        (self.fleet,role,self.fence,'e'*64,datetime.now(timezone.utc)+timedelta(minutes=10)))
        now=datetime.now(timezone.utc)
        receipt={'format':'hosting-discovery-fleet-fence-receipt/1','fleetId':self.fleet,'leaseId':doc['leaseId'],
            'workerId':self.worker,'instanceId':doc['instanceId'],'serviceDigest':self.service,
            'requestDigest':hashlib.sha256(_json(doc).encode('ascii')).hexdigest(),'oldProcessExcluded':True,
            'oldSocketsClosed':True,'observerId':'test-independent-fence','observationId':'test-observation',
            'observedAt':now.isoformat(),'expiresAt':(now+timedelta(minutes=1)).isoformat()}
        with self.psycopg.connect(self.owner_dsn) as con:
            invalid={**receipt,'instanceId':uuid4().hex}
            with self.assertRaises(self.psycopg.Error),con.transaction():
                con.execute('SELECT hosting_controlplane.discovery_fleet_fenced_close(%s,%s,%s,%s)',(self.fleet,_json({'receipt':invalid,'signature':'test-sql-transition-only'}),self.fence,'e'*64))
            for invalid in ({**receipt,'observedAt':None},{**receipt,'expiresAt':None}):
                with self.assertRaises(self.psycopg.Error),con.transaction():
                    con.execute('SELECT hosting_controlplane.discovery_fleet_fenced_close(%s,%s,%s,%s)',
                        (self.fleet,_json({'receipt':invalid,'signature':'test-sql-transition-only'}),self.fence,'e'*64))
            with self.assertRaises(self.psycopg.Error),con.transaction():
                con.execute('SELECT hosting_controlplane.discovery_fleet_fenced_close(%s,%s,%s,%s)',
                    (self.fleet,_json({'receipt':receipt,'signature':'test-sql-transition-only'}),self.fence,'f'*64))
            proof=_json({'receipt':receipt,'signature':'test-sql-transition-only'})
            self.assertEqual(con.execute('SELECT hosting_controlplane.discovery_fleet_fenced_close(%s,%s,%s,%s)',
                (self.fleet,proof,self.fence,'e'*64)).fetchone(),('INDEPENDENT_WORKER_FENCED',))
            self.assertEqual(con.execute('SELECT hosting_controlplane.discovery_fleet_fenced_close(%s,%s,%s,%s)',
                (self.fleet,proof,self.fence,'e'*64)).fetchone(),('INDEPENDENT_WORKER_FENCED',))
            with self.assertRaises(self.psycopg.Error),con.transaction():
                con.execute('SELECT hosting_controlplane.discovery_fleet_fenced_close(%s,%s,%s,%s)',
                    (self.fleet,_json({'receipt':{**receipt,'observationId':'another'},'signature':'test-sql-transition-only'}),self.fence,'e'*64))
        self.assertEqual(self.admit(self.request())[0],'LEASE_STARTED')


if __name__=='__main__':unittest.main()
