"""Actual psycopg conversion, local custody and conservative fleet fault paths.

Rows here are protocol fixtures. Actual isolation/concurrency/SQL transitions are
verified separately by test_fleet_budget_postgres, never inferred from these rows.
"""
from dataclasses import replace
from datetime import datetime,timezone,timedelta
import hashlib
import json
from pathlib import Path
import io
import http.client
from contextlib import redirect_stdout,redirect_stderr
import tempfile
from threading import Event
import time
import unittest
from unittest.mock import patch

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from psycopg.adapt import Transformer
from psycopg._queries import PostgresQuery

from provisioner.controlplane.discovery import fleet_read_budget as module
from provisioner.controlplane.discovery import service_enrollment as service
from provisioner.controlplane.discovery.model import _json
from provisioner.controlplane.discovery.read_budget import EndpointReadPolicy,NativeReadAdmissionHeld
from tests.provisioning.controlplane.test_ahv_discovery import campaign
from tests.provisioning.discovery import test_ahv_https as ahv_fixture


class Connection:
    autocommit=False
    def __init__(self,database):self.db=database
    def __enter__(self):return self
    def __exit__(self,kind,value,trace):
        if kind is None and self.db.lose_commit:raise OSError('synthetic commit receipt loss')
    def execute(self,sql,args=None):
        query=PostgresQuery(Transformer());query.convert(sql,args)
        self.db.calls.append((sql,args));self.result=None
        if 'session_user,current_user' in sql:self.result=(self.db.role,self.db.role,False,False,False,False,False)
        elif 'is_site_worker_role' in sql:self.result=(False,)
        elif 'has_table_privilege' in sql:self.result=(self.db.unrelated_privilege,)
        elif 'has_column_privilege' in sql or 'pg_has_role' in sql:self.result=(False,)
        elif 'has_database_privilege' in sql:self.result=(False,False)
        elif 'has_function_privilege' in sql:self.result=(True,True,True,self.db.fencer_privilege)
        elif 'discovery_fleet_inspect' in sql:self.result=({'policyDigest':self.db.policy,'enabled':True,'leases':[]},)
        elif 'discovery_fleet_admit' in sql:
            doc=json.loads(args[3]);self.db.starts.append(doc)
            if self.db.lose_execute:raise OSError('synthetic lost admission response')
            self.result=('THROTTLED',None,None,None) if self.db.throttle else (
                'LEASE_STARTED',doc['leaseId'],datetime.now(timezone.utc),datetime.fromisoformat(doc['expiresAt']))
        elif 'discovery_fleet_close' in sql:
            self.db.closes.append(args);self.result=('LOCAL_SOCKET_CLOSED',)
        elif 'discovery_fleet_fenced_close' in sql:self.result=('INDEPENDENT_WORKER_FENCED',)
        else:raise AssertionError(sql)
        return self
    def fetchone(self):return self.result


class Database:
    role='hosting_fleet';policy='a'*64
    unrelated_privilege=False;fencer_privilege=False;lose_execute=False;lose_commit=False;throttle=False
    def __init__(self):self.calls=[];self.starts=[];self.closes=[]
    def connect(self):return Connection(self)


class FleetFixture:
    def setup_fleet(self,root):
        self.root=root
        self.package={'name':'hosting-provisioner','version':'unit-protocol-only','root':'/unit-protocol',
                      'contentDigest':'b'*64}
        self.package_patch=patch.object(service,'package_facts',return_value=self.package)
        self.package_patch.start();self.addCleanup(self.package_patch.stop)
        interpreter_patch=patch.object(service,'interpreter_facts',return_value={
            'path':'/unit-protocol/python','contentDigest':'c'*64,'version':'unit-protocol-only'})
        interpreter_patch.start();self.addCleanup(interpreter_patch.stop)
        self.store=root/'retained';self.store.mkdir(mode=0o700)
        self.manifest=root/'service.json'
        self.document=service.capture_service_facts('collector-service',{'outbox':self.store})
        raw=_json(self.document).encode('ascii');self.manifest.write_bytes(raw);self.manifest.chmod(0o600)
        self.enrollment=service.ServiceEnrollment.from_file(self.manifest,hashlib.sha256(raw).hexdigest())
        self.dsn=root/'fleet.dsn';self.dsn.write_text('host=database.example user=hosting_fleet sslmode=verify-full');self.dsn.chmod(0o600)
        self.config=root/'fleet.json'
        self.config.write_text(_json({'format':'hosting-discovery-fleet-budget/1','fleetId':'fleet-1',
            'workerId':'worker-1','databaseRole':'hosting_fleet','policyDigest':'a'*64,'databaseCaDigest':'d'*64,'dsnFile':str(self.dsn),
            'serviceEnrollmentFile':str(self.manifest),'serviceEnrollmentDigest':self.enrollment.digest}))
        self.config.chmod(0o600)
        self.settings=module.FleetBudgetSettings.from_file(self.config)
        self.db=Database();self.budget=module.PostgresFleetBudget(self.settings,connect=self.db.connect)

    def gate(self,selected=None,**kwargs):
        if selected is None:
            now=datetime.now(timezone.utc)
            selected=replace(campaign(),issued_at=now-timedelta(seconds=5),expires_at=now+timedelta(minutes=5))
        policy=EndpointReadPolicy(selected.scope.organization_id,selected.scope.site_id,
            selected.scope.platform_family,selected.scope.endpoint_id,1,1)
        return module.FleetNativeReadGate(policy,budget=self.budget,**kwargs).bind_campaign(selected,'environment-1')


class FleetReadBudgetTests(FleetFixture,unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.setup_fleet(Path(self.temp.name))

    def test_start_is_committed_before_read_and_close_retains_exact_worker_instance_digest(self):
        calls=[]
        with self.gate().permit(time.monotonic()+1,lambda:calls.append(1)):
            self.assertEqual(len(self.db.starts),1);self.assertFalse(self.db.closes)
        self.assertEqual(len(self.db.closes),1)
        start=self.db.starts[0];close=self.db.closes[0]
        self.assertEqual(close[3],start['instanceId']);self.assertEqual(close[4],start['leaseId'])
        self.assertEqual(close[5],hashlib.sha256(_json(start).encode('ascii')).hexdigest())
        self.assertGreaterEqual(len(calls),4)

    def test_unbound_campaign_and_cross_endpoint_gate_never_admit(self):
        selected=campaign();gate=self.gate(selected)
        with self.assertRaises(NativeReadAdmissionHeld):gate.require_scope(replace(selected.scope,endpoint_id='other'))
        unbound=module.FleetNativeReadGate(gate.policy,budget=self.budget)
        with self.assertRaises(NativeReadAdmissionHeld):
            with unbound.permit(time.monotonic()+1,lambda:None):self.fail('unbound read')
        self.assertFalse(self.db.starts)

    def test_lost_admission_execute_or_commit_never_retries_or_refunds(self):
        for name in ('lose_execute','lose_commit'):
            self.db=Database();self.budget=module.PostgresFleetBudget(self.settings,connect=self.db.connect)
            setattr(self.db,name,True)
            with self.subTest(name=name),self.assertRaises(OSError):
                with self.gate().permit(time.monotonic()+1,lambda:None):self.fail('unknown read admitted')
            self.assertEqual(len(self.db.starts),1);self.assertFalse(self.db.closes)

    def test_failed_socket_cleanup_keeps_original_read_occupied(self):
        with self.assertRaises(OSError):
            with self.gate().permit(time.monotonic()+1,lambda:None):raise OSError('socket close unobserved')
        self.assertEqual(len(self.db.starts),1);self.assertFalse(self.db.closes)

    def test_revocation_before_or_after_admission_never_reads(self):
        count=0
        def authorize():
            nonlocal count
            count+=1
            if count==4:raise PermissionError('revoked before socket')
        with self.assertRaises(PermissionError):
            with self.gate().permit(time.monotonic()+1,authorize):self.fail('revoked read')
        self.assertEqual(len(self.db.starts),1);self.assertEqual(len(self.db.closes),1)
        self.db.starts=[];self.db.closes=[]
        with self.assertRaises(PermissionError):
            with self.gate().permit(time.monotonic()+1,lambda:(_ for _ in ()).throw(PermissionError())):pass
        self.assertFalse(self.db.starts)

    def test_throttled_deadline_stop_and_missing_current_policy_do_not_read(self):
        self.db.throttle=True
        with self.assertRaises(NativeReadAdmissionHeld):
            with self.gate().permit(time.monotonic()+.05,lambda:None):self.fail('throttled read')
        self.assertFalse(self.db.closes)
        stopped=Event();stopped.set()
        with self.assertRaises(NativeReadAdmissionHeld):
            with self.gate(stopped=stopped).permit(time.monotonic()+1,lambda:None):pass
        self.db.policy='c'*64
        with self.assertRaises(NativeReadAdmissionHeld):module.PostgresFleetBudget(self.settings,connect=self.db.connect)

    def test_login_cannot_be_a_direct_table_writer_or_independent_fencer(self):
        for name in ('unrelated_privilege','fencer_privilege'):
            self.db=Database();setattr(self.db,name,True)
            with self.subTest(name=name),self.assertRaises(NativeReadAdmissionHeld):
                module.PostgresFleetBudget(self.settings,connect=self.db.connect)

    def test_five_bucket_dimensions_share_endpoint_total_and_isolate_tenant_wsd(self):
        selected=campaign().scope;other=replace(selected,tenant_id='other',native_scope_id='other')
        first,second=module.bucket_ids(selected),module.bucket_ids(other)
        self.assertEqual(len(first),5);self.assertEqual(len(set(first)),5)
        self.assertEqual(first[0],second[0]);self.assertEqual(first[1],second[1]);self.assertEqual(first[4],second[4])
        self.assertNotEqual(first[2],second[2]);self.assertNotEqual(first[3],second[3])

    def test_manifest_store_move_replacement_package_or_private_permissions_hold(self):
        self.enrollment.require_current()
        self.store.rename(self.root/'old-retained');self.store.mkdir(mode=0o700)
        with self.assertRaises(PermissionError):self.settings.recheck()
        self.store.rmdir();(self.root/'old-retained').rename(self.store)
        self.package['version']='changed'
        with self.assertRaises(PermissionError):self.settings.recheck()
        self.package['version']='unit-protocol-only';self.manifest.chmod(0o644)
        with self.assertRaises(Exception):self.settings.recheck()

    def test_verified_tls_single_host_role_and_bounded_dsn_are_required(self):
        for dsn in ('host=database.example user=hosting_fleet sslmode=disable',
                    'host=database.example,other.example user=hosting_fleet sslmode=verify-full',
                    'host=database.example user=other sslmode=verify-full',
                    'host=database.example user=hosting_fleet sslmode=verify-full options=anything'):
            self.dsn.write_text(dsn)
            with self.subTest(dsn=dsn),self.assertRaises(NativeReadAdmissionHeld):self.settings.connect()

    def test_independent_signed_fence_is_exact_current_and_separate_from_worker_close(self):
        key=Ed25519PrivateKey.generate();now=datetime.now(timezone.utc)
        receipt={'format':'hosting-discovery-fleet-fence-receipt/1','fleetId':'fleet-1',
            'leaseId':'1'*32,'workerId':'worker-1','instanceId':'2'*32,'serviceDigest':'3'*64,
            'requestDigest':'4'*64,'observerId':'independent-host-fence','observationId':'observation-1',
            'observedAt':now.isoformat(),'expiresAt':(now+timedelta(minutes=1)).isoformat(),
            'oldProcessExcluded':True,'oldSocketsClosed':True}
        path=self.root/'fence.json'
        def write():
            path.write_text(_json({'receipt':receipt,'signature':ahv_fixture.encoded(key.sign(_json(receipt).encode('ascii')))}));path.chmod(0o600)
        write()
        result=module.reconcile_fenced_read(connect=self.db.connect,fleet_id='fleet-1',receipt_path=path,
            public_key=key.public_key().public_bytes_raw(),service_digest=self.enrollment.digest,recheck=self.settings.recheck)
        self.assertEqual(result['status'],'INDEPENDENT_WORKER_FENCED')
        receipt['oldSocketsClosed']=False;write()
        with self.assertRaises(NativeReadAdmissionHeld):module.reconcile_fenced_read(connect=self.db.connect,
            fleet_id='fleet-1',receipt_path=path,public_key=key.public_key().public_bytes_raw(),
            service_digest=self.enrollment.digest,recheck=self.settings.recheck)

    def test_installed_commands_capture_actual_stores_and_hold_uncommissioned_or_aliased_roles(self):
        output=self.root/'captured.json';stdout=io.StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(module.main(['service-facts','--service-id','collector-service',
                '--store','outbox='+str(self.store),'--output',str(output)]),0)
        result=json.loads(stdout.getvalue());self.assertFalse(result['enrollmentIssued'])
        service.ServiceEnrollment.from_file(output,result['digest']).require_current()
        with redirect_stderr(io.StringIO()):
            self.assertEqual(module.main(['service-facts','--service-id','collector-service',
                '--store','outbox='+str(self.store),'--store','outbox='+str(self.store),'--output',str(output)]),2)
        with redirect_stdout(io.StringIO()),patch.object(module.FleetBudgetSettings,'connect',self.db.connect):
            self.assertEqual(module.main(['inspect','--config',str(self.config)]),0)
        self.db.fencer_privilege=True
        with redirect_stderr(io.StringIO()),patch.object(module.FleetBudgetSettings,'connect',self.db.connect):
            self.assertEqual(module.main(['inspect','--config',str(self.config)]),2)

    def test_fence_receiver_config_is_independently_pinned_and_worker_capabilities_are_rejected(self):
        key=Ed25519PrivateKey.generate();path=self.root/'receiver.json'
        path.write_text(_json({'format':'hosting-discovery-fleet-fence-receiver/1','fleetId':'fleet-1',
            'databaseRole':'hosting_fencer','databaseCaDigest':'d'*64,'dsnFile':str(self.dsn),
            'fencePublicKey':ahv_fixture.encoded(key.public_key().public_bytes_raw()),
            'serviceEnrollmentFile':str(self.manifest),'serviceEnrollmentDigest':self.enrollment.digest}));path.chmod(0o600)
        selected=module.FleetFenceSettings.from_file(path)
        self.assertEqual(selected.public_key,key.public_key().public_bytes_raw())
        self.assertEqual(selected.enrollment.digest,self.enrollment.digest)
        with self.assertRaises(NativeReadAdmissionHeld):
            module._require_isolated_role(self.db.connect,self.db.role,(False,False,False,True))
        path.write_text(path.read_text().replace('hosting_fencer','hosting_fleet'))
        with self.assertRaises(PermissionError):selected.recheck()

    def test_package_capture_includes_actual_bytecode_metadata_and_rejects_unrecorded_source(self):
        # Actual retained package bytes and inventory, with a unit-only installed
        # distribution locator. This cannot qualify a deployed interpreter.
        root=self.root/'site-packages';package=root/'provisioner';info=root/'hosting_provisioner-1.dist-info'
        package.mkdir(parents=True);info.mkdir()
        (package/'__init__.py').write_text('')
        for name in ('METADATA','RECORD','WHEEL'):(info/name).write_text(name)
        class Distribution:
            version='unit-protocol-only'
            files=[Path('provisioner/__init__.py'),*[Path(info.name)/name for name in ('METADATA','RECORD','WHEEL')]]
            def locate_file(self,value):return root/value
        import provisioner
        self.package_patch.stop()
        with patch.object(service.metadata,'distribution',return_value=Distribution()),patch.object(provisioner,'__file__',str(package/'__init__.py')):
            first=service.package_facts();(package/'cached.pyc').write_bytes(b'actual-bytecode')
            second=service.package_facts();self.assertNotEqual(first['contentDigest'],second['contentDigest'])
            (info/'METADATA').write_text('changed-version-metadata')
            self.assertNotEqual(second['contentDigest'],service.package_facts()['contentDigest'])
            (package/'unrecorded.py').write_text('print("unrecorded")')
            with self.assertRaises(PermissionError):service.package_facts()


class FleetNativeTlsTests(FleetFixture,unittest.TestCase):
    def setUp(self):
        self.native=ahv_fixture.AhvHttpsTests();self.native.setUp();self.addCleanup(self.native.doCleanups)
        self.setup_fleet(self.native.root)

    def test_actual_native_tls_gets_use_original_authority_and_close_each_global_permit(self):
        gate=self.gate(self.native.campaign)
        transport=self.native.client(read_gate=gate)
        result=transport.collect()
        self.assertEqual(len(self.native.calls),2);self.assertEqual(len(self.db.starts),2);self.assertEqual(len(self.db.closes),2)
        self.assertTrue(all(page.scope==self.native.campaign.scope for page in result))

    def test_actual_native_transport_close_failure_does_not_publish_a_successful_close(self):
        original=http.client.HTTPResponse.close
        def failed_close(response):
            original(response);raise OSError('actual close acknowledgement unavailable')
        with patch.object(http.client.HTTPResponse,'close',failed_close):
            pages=self.native.client(read_gate=self.gate(self.native.campaign)).collect()
        self.assertEqual(pages[-1].terminal_completeness,'UNKNOWN')
        self.assertTrue(pages[-1].collection_errors)
        self.assertEqual(len(self.native.calls),1);self.assertEqual(len(self.db.starts),1);self.assertFalse(self.db.closes)


if __name__=='__main__':unittest.main()
