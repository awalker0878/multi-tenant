"""Real mTLS/Unix/TLS boundaries; synthetic grant/native command persistence.

These exercise revocation between commands, not native RBAC commissioning or
PostgreSQL authority. Those owners retain their independent hosted campaigns.
"""
from dataclasses import replace
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
import os
from pathlib import Path
import queue
import socket
import ssl
import sys
import tempfile
import threading
from types import SimpleNamespace
from uuid import uuid4
import unittest
import errno
from unittest.mock import patch

from provisioner.controlplane.authority.model import PlanScope, WorkerGrant
from provisioner.controlplane.authority.service import AuthorityService
from provisioner.controlplane.persistence import NativeBinding, TenantContext
from provisioner.controlplane.persistence.store import OwnerLease
from provisioner.controlplane.reconciliation.registry import NativeOperationRegistry
from provisioner.controlplane.reconciliation.read_enrollment import NativeReadEnrollment
from provisioner.controlplane.jobs.repository import _digest
from provisioner.controlplane.reconciliation.planned_terraform import VaultOpenStackCredentialConsumer
from provisioner.controlplane.worker.command_runtime import WorkerCommandRuntime
from provisioner.controlplane.worker.grants import CredentialBroker, GrantDenied, PostgresWorkerGrants
from provisioner.controlplane.worker.guest_commands import GuestCommandRuntime, GuestExecutionContext, GuestReadCredentialProfile
from provisioner.controlplane.worker.vault_consumer import VaultCredentialConsumer
from provisioner.controlplane.worker.pki import MutualTlsWorkerVerifier
from provisioner.controlplane.worker.adapters.openstack_planning import ScopedOpenStackPlanningRuntime, EphemeralOpenStackPlanningContext
from provisioner.controlplane.worker.vault import VaultDynamicCredentialIssuer, VaultDynamicRole
from provisioner.controlplane.workflow.admitted_job import AdmittedInput
from provisioner.controlplane.workflow.execution_selection import PostgresExecutionAuthority
from provisioner.execution import guest_apply, guest_run, guest_command_client, terraform_run
from provisioner.execution.run_files import digest, encoded, load_private, read_private, utcnow, write_new
from tests.provisioning.worker.tls_fixtures import TestPki
from tests.test_guest_apply import configured
from provisioner.migration.provisioning import ObservedProvisioningGuard, ObservedProvisioningRuntime
from provisioner.migration.lifecycle import LifecycleWorkerRuntime
from tests.test_application_lifecycle import lifecycle_fixture

ROOT = Path(__file__).resolve().parents[3]


def _unix_socket_available():
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM): pass
        return True
    except PermissionError as error:
        if error.errno != errno.EPERM: raise
        return False


UNIX_AVAILABLE = _unix_socket_available()


class _Grants(PostgresWorkerGrants):
    def __init__(self, grant):
        self.grant, self.revoked, self.calls = grant, False, []

    def with_authorized_reference(self, context, identity, grant_id, *, use, **arguments):
        self.calls.append(arguments)
        if self.revoked: raise GrantDenied('Synthetic authority revoked between commands')
        if (grant_id != self.grant.grant_id or identity.subject != self.grant.worker_subject
                or arguments['step_id'] != self.grant.step_id or arguments['operation_id'] != self.grant.operation_id
                or arguments['operation_scope'] != self.grant.operation_scope):
            raise GrantDenied('Synthetic bound grant changed')
        return use('vault:target-read', self.grant, self.grant.expires_at)


class _Execution(PostgresExecutionAuthority):
    def __init__(self, plan, selection):
        self.plan, self.selected, self.revoked = plan, selection, False
        self.calls = []

    def require_current(self, admitted, selection_digest, operation, **keywords):
        self.calls.append((admitted, selection_digest, operation, keywords))
        if self.revoked: raise GrantDenied('Synthetic original admission revoked')
        return self.plan, self.selected

    def require_observation(self, admitted, selection_digest, operation):
        self.calls.append((admitted,selection_digest,operation,{'purpose':'OBSERVATION'}))
        if self.revoked: raise GrantDenied('Synthetic independent observation revoked')
        return self.plan, self.selected


class _CurrentWorkerAuthority(AuthorityService):
    def __init__(self, fixture): self.fixture=fixture
    def require_worker_step_window(self,credential,grant_id,**arguments):
        fixture=self.fixture
        if credential is not fixture.peer: raise GrantDenied('Original synthetic worker credential switched')
        values=fixture.runtime.grant_arguments(fixture.admitted) | arguments
        return fixture.grants.with_authorized_reference(fixture.context,fixture.identity,grant_id,
            **values,use=lambda _reference,grant,deadline:(grant,deadline))


class _NativeRegistry(NativeOperationRegistry):
    def __init__(self): self.claimed=False; self.calls=[]
    def prepare(self,context,lease,scope,**arguments): self.calls.append(('prepare',arguments))
    def claim_once(self,context,lease,scope,operation,identity):
        self.calls.append(('claim',operation))
        if self.claimed: return False
        self.claimed=True; return True


class _Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.pki = TestPki(); self.addCleanup(self.pki.close)
        self.pki.issue('server')
        self.pki.issue('worker', client=True,
            uri='spiffe://workers.example/org/org-01/tenant/tenant-01/site/site-01/worker/worker-01')
        self.verifier = MutualTlsWorkerVerifier(server_certificate=self.pki.root/'server.pem',
            server_key=self.pki.root/'server.key', trust_bundle=self.pki.root/'ca.pem',
            crl_bundle=self.pki.root/'crl.pem', trust_domain='workers.example')
        listener = socket.socket(); listener.bind(('127.0.0.1', 0)); listener.listen(1)
        peers = queue.Queue(); finished = threading.Event()
        def accept():
            try:
                raw, _ = listener.accept()
                peer = self.verifier.context.wrap_socket(raw, server_side=True)
                peers.put(peer); finished.wait(15); peer.close()
            except Exception as exc: peers.put(exc)
        thread = threading.Thread(target=accept, daemon=True); thread.start()
        tls = ssl.create_default_context(cafile=str(self.pki.root/'ca.pem'))
        tls.load_cert_chain(str(self.pki.root/'worker.pem'), str(self.pki.root/'worker.key'))
        self.client = tls.wrap_socket(socket.create_connection(listener.getsockname()), server_hostname='localhost')
        self.peer = peers.get(timeout=5)
        self.assertIsInstance(self.peer, ssl.SSLSocket)
        self.addCleanup(listener.close); self.addCleanup(self.client.close)
        self.addCleanup(lambda: (finished.set(), thread.join(timeout=3)))
        self.identity = self.verifier.verify(self.peer)
        self.source = PlanScope('org-01','tenant-01','site-01','wsd-01','vmware-01','source-01','vmware')
        self.destination = PlanScope('org-01','tenant-01','site-01','wsd-01','openstack-01','project-01','openstack')
        now = utcnow()
        self.grant = WorkerGrant('grant-01','org-01','tenant-01','plan-01',1,'a'*64,self.source,
            self.destination,'worker-01','stage-01','operation-01','DISCOVER_READ',self.destination,
            'lease-01',1,('approval-01',),0,now-timedelta(seconds=1),now+timedelta(minutes=4))
        self.admitted = AdmittedInput('job-01','org-01','tenant-01','plan-01',1,'a'*64,0,'b'*64)
        self.context = TenantContext('org-01','tenant-01')
        self.patches = [patch('provisioner.controlplane.worker.command_runtime.verify',
                             return_value={'status':'HASHES_MATCH','commit':'a'*40}),
                        patch('provisioner.controlplane.worker.command_runtime.verify_runtime',
                              return_value={'status':'RUNTIME_SOURCES_MATCH'})]
        for value in self.patches: value.start(); self.addCleanup(value.stop)

    def select(self, *, kind='terraform_plan', parameters=None, files=None):
        self.step = {'id':'stage-01','kind':kind,'needs':[]}
        self.scope = {'environment_key':'env-01','site_key':'site-01','platform':self.destination.platform_family,
                      'tenant_key':'tenant-01','wsd_key':'wsd-01'}
        self.scope = getattr(self, 'selection_scope', self.scope)
        self.delivery = {'source_commit':'a'*40,'scope':self.scope,'steps':[self.step]}
        self.packet = {'step_id':'stage-01','plan_sha256':_digest(self.delivery),
                       'parameters':parameters or {},'files':files or {}}
        self.selection = {'sourceCommit':'a'*40,'workloadId':'workload-01',
            'executionScope':self.scope,'deliveryPlanDigest':_digest(self.delivery),
            'stageBindings':{'stage-01':{'kind':kind,'parametersDigest':_digest(self.packet['parameters']),
                'inputDigests':{name:asset['sha256'] for name,asset in self.packet['files'].items()
                               if name not in {'environment','cloud','authority','approval','ssh_key','ssh_certificate'}}}}}
        def record(scope):
            return dict(zip(('organizationId','tenantId','locationId','securityDomainId',
                             'endpointId','nativeScopeId','platformFamily'),vars(scope).values()))
        self.plan = {'spec':{'source':record(self.source),'destination':record(self.destination)}}
        self.grants = _Grants(self.grant); self.execution = _Execution(self.plan,self.selection)
        self.runtime = WorkerCommandRuntime(self.execution,self.grants,self.verifier,self.peer,
                                            self.context,self.identity,self.grant)
        return self.runtime.select(self.admitted,self.selection,self.delivery,self.step,self.packet,ROOT)


    def additional_peer(self):
        self.pki.issue('writer',client=True,
            uri='spiffe://workers.example/org/org-01/tenant/tenant-01/site/site-01/worker/writer-01')
        listener=socket.socket(); listener.bind(('127.0.0.1',0)); listener.listen(1)
        peers=queue.Queue(); finished=threading.Event()
        def accept():
            try:
                raw,_=listener.accept(); peer=self.verifier.context.wrap_socket(raw,server_side=True)
                peers.put(peer); finished.wait(15); peer.close()
            except Exception as exc: peers.put(exc)
        thread=threading.Thread(target=accept,daemon=True); thread.start()
        tls=ssl.create_default_context(cafile=str(self.pki.root/'ca.pem'))
        tls.load_cert_chain(str(self.pki.root/'writer.pem'),str(self.pki.root/'writer.key'))
        client=tls.wrap_socket(socket.create_connection(listener.getsockname()),server_hostname='localhost')
        peer=peers.get(timeout=5); self.assertIsInstance(peer,ssl.SSLSocket)
        self.addCleanup(listener.close); self.addCleanup(client.close)
        self.addCleanup(lambda:(finished.set(),thread.join(timeout=3)))
        return self.verifier.verify(peer),peer


class SelectedCommandTests(_Fixture):
    def test_current_actual_mtls_and_original_grant_rechecked_between_commands(self):
        authority = self.select(); authority.require_current()
        self.grants.revoked = True
        with self.assertRaises(GrantDenied): authority.require_current()
        self.assertEqual(self.grants.calls[-1]['job_id'], self.admitted.job_id)
        self.assertEqual(self.grants.calls[-1]['operation_kind'], 'DISCOVER_READ')

    def test_switched_certificate_context_is_rejected_without_next_database_use(self):
        authority = self.select(); before = len(self.grants.calls)
        self.verifier.reload_trust()
        with self.assertRaises(GrantDenied): authority.require_current()
        self.assertEqual(len(self.grants.calls), before)

    def test_selected_inputs_and_purpose_cannot_be_rehashed_or_switched(self):
        path = self.root/'input'; write_new(path,b'original')
        authority = self.select(files={'inputs':{'path':str(path),'sha256':digest(b'original')}})
        path.write_bytes(b'replacement')
        with self.assertRaisesRegex(ValueError,'originally bound'): authority.require_current()
        path.write_bytes(b'original'); authority.packet['parameters']['purpose']='other'
        with self.assertRaisesRegex(ValueError,'purpose or packet'): authority.require_current()

    def test_json_peer_or_callback_cannot_construct_a_command_runtime(self):
        authority = self.select()
        with self.assertRaises(ValueError):
            replace(self.runtime, transport_evidence={'certificate':self.identity.certificate_sha256})
        with self.assertRaises(ValueError):
            self.runtime.select(self.admitted,self.selection,self.delivery,self.step,self.packet,ROOT,
                                intent_guard=lambda: True)

    def test_project_read_planning_grant_cannot_borrow_guest_mutation_or_probe_purpose(self):
        authority=self.select()
        commands=GuestCommandRuntime(self.runtime)
        binding=NativeBinding(self.destination.platform_family,self.destination.endpoint_id,
                              self.destination.native_scope_id,'vm','server-01')
        for action in ('start','show'):
            with self.subTest(action=action),self.assertRaisesRegex(ValueError,'claimed before remote contact'):
                commands.exchange(authority,target={},binding=binding,runtime={},key=None,certificate=None,
                    remote_argv=('/usr/bin/systemctl',action,'hosting-application.service'),input_bytes=b'',output=self.root)


class _Native(BaseHTTPRequestHandler):
    def do_GET(self):
        self.server.contacts.append(('GET',self.path))
        self.respond(200, {'data':None,'auth':None,'wrap_info':{
            'token':'test-single-use-wrap-'+str(len(self.server.contacts)), 'ttl':30,
            'creation_path':'platform/creds/target-read'}})

    def do_POST(self):
        self.server.contacts.append(('POST',self.path))
        if self.path == '/v1/sys/wrapping/unwrap':
            self.respond(200,{'lease_id':'test-lease-'+str(len(self.server.contacts)),
                             'lease_duration':30,'data':self.server.data,'auth':None,'wrap_info':None})
        elif self.path == '/v3/auth/tokens':
            self.respond(201,{'token':{'project':{'id':self.server.project},
                'application_credential':{'id':'fresh-app'}, 'methods':['application_credential'],
                'roles':[{'name':name} for name in self.server.roles],
                'expires_at':(utcnow()+timedelta(minutes=2)).isoformat(),
                'catalog':[{'type':'compute','endpoints':[{'interface':'internal','region':'region-01',
                                                         'url':self.server.origin+'/v2.1/project-01'}]}]}}, token=True)
        else: self.respond(404,{})

    def respond(self, status, payload, token=False):
        body=encoded(payload); self.send_response(status)
        self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(body)))
        if token: self.send_header('X-Subject-Token','synthetic-native-token')
        self.end_headers(); self.wfile.write(body)

    def log_message(self,*_): pass


class PlanningCredentialTests(_Fixture):
    def setUp(self):
        super().setUp()
        self.server=ThreadingHTTPServer(('127.0.0.1',0),_Native)
        tls=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls.load_cert_chain(str(self.pki.root/'server.pem'),str(self.pki.root/'server.key'))
        self.server.socket=tls.wrap_socket(self.server.socket,server_side=True)
        thread=threading.Thread(target=self.server.serve_forever,daemon=True); thread.start()
        self.addCleanup(self.server.server_close); self.addCleanup(self.server.shutdown)
        self.origin=f'https://localhost:{self.server.server_port}'
        self.server.origin=self.origin; self.server.roles=['reader']; self.server.project='project-01'; self.server.contacts=[]
        self.binary=self.root/'terraform'; write_new(self.binary,b'fixture executable'); self.binary.chmod(0o700)
        path=self.root/'inputs'; write_new(path,encoded({'openstack_cloud':'test-cloud'}))
        self.entry={'id':'openstack-wsd-workloads','platform':'openstack','root':'terraform/stacks/wsd/openstack/workloads'}
        self.authority=self.select(parameters={'catalog_id':self.entry['id'],'terraform':str(self.binary),
            'terraform_sha256':digest(self.binary.read_bytes())}, files={'inputs':{'path':str(path),'sha256':digest(path.read_bytes())}})
        cloud={'clouds':{'test-cloud':{'auth_type':'v3applicationcredential','verify':True,
            'region_name':'region-01','interface':'internal','auth':{'auth_url':self.origin+'/v3',
            'application_credential_id':'fresh-app','application_credential_secret':'short-lived-native-secret'}}}}
        self.server.data={'cloud':cloud,'environment':{'TF_HTTP_USERNAME':'fresh-user','TF_HTTP_PASSWORD':'fresh-backend-secret'}}
        token=self.root/'agent-token'; write_new(token,b'test-only-agent-token')
        issuer=VaultDynamicCredentialIssuer(vault_url=self.origin,ca_bundle=self.pki.root/'ca.pem',
            agent_token_file=token,roles=(VaultDynamicRole('vault:target-read','platform/creds/target-read',
                self.destination,'DISCOVER_READ',timedelta(minutes=1)),))
        broker=CredentialBroker(self.verifier,self.grants,issuer)
        owner=ScopedOpenStackPlanningRuntime(self.runtime,broker,VaultOpenStackCredentialConsumer(issuer),('reader',),self.origin)
        self.credentials=EphemeralOpenStackPlanningContext(owner,self.authority)
        self.operation=self.root/'prepared'; self.operation.mkdir(mode=0o700)
        self.directory=self.operation/'source'/self.entry['root']; self.directory.mkdir(parents=True,mode=0o700)
        for folder in self.directory.parents:
            if folder==self.root: break
            folder.chmod(0o700)
        (self.operation/'tmp').mkdir(mode=0o700)
        write_new(self.operation/'terraform.rc',b'disable_checkpoint=true\n')
        write_new(self.operation/'ca.pem',(self.pki.root/'ca.pem').read_bytes())
        args=SimpleNamespace(inputs=path,terraform=self.binary,output=self.operation)
        self.credentials.bind_prepare(args,self.entry,self.scope|{'phase':'workloads'},
            {'TF_HTTP_USERNAME':'historical-user','TF_HTTP_PASSWORD':'historical-unused-secret'},cloud,
            (self.pki.root/'ca.pem').read_bytes())
        self.contact={'valid_from':(utcnow()-timedelta(seconds=1)).isoformat(),
                      'valid_until':(utcnow()+timedelta(minutes=2)).isoformat()}

    def command(self, name):
        commands = {
            'version':(['version','-json'],'version.json'),
            'init':(['init','-input=false','-no-color','-lockfile=readonly','-reconfigure',
                     '-backend-config='+str(self.operation/'backend.hcl')],'init.log'),
            'plan':(['plan','-input=false','-no-color','-lock=true','-lock-timeout=60s','-detailed-exitcode',
                     '-var-file='+str(self.operation/'inputs.json'),'-out='+str(self.operation/'saved.tfplan')],'plan.log'),
            'show':(['show','-json',str(self.operation/'saved.tfplan')],'plan.json')}
        argv,output = commands[name]
        return terraform_run.authorized_command(self.contact,self.binary,self.directory,argv,
            {'TF_HTTP_PASSWORD':'historical-unused-secret'},self.operation/output,
            planning_context=self.credentials)

    def test_each_command_consumes_fresh_scoped_credentials_and_cleans_native_secrets(self):
        observed=[]
        def command(_binary,_directory,_argv,environment,_output,**_):
            path=Path(environment['OS_CLIENT_CONFIG_FILE'])
            observed.append(path)
            self.assertEqual(load_private(path)['clouds']['test-cloud']['auth']['application_credential_secret'],
                             'short-lived-native-secret')
            self.assertEqual(environment['TF_HTTP_PASSWORD'],'fresh-backend-secret')
            return 0
        with patch.object(terraform_run,'command',side_effect=command):
            self.command('version'); self.command('init')
        self.assertEqual(len(self.server.contacts),6)
        self.assertEqual(len(set(observed)),2)
        self.assertTrue(all(not path.exists() for path in observed))

    def test_revocation_after_first_command_blocks_the_next_credential_and_subprocess(self):
        with patch.object(terraform_run,'command',return_value=0) as command:
            self.command('version'); before=len(self.server.contacts)
            self.grants.revoked=True
            with self.assertRaises(GrantDenied): self.command('init')
        self.assertEqual(command.call_count,1); self.assertEqual(len(self.server.contacts),before)

    def test_native_write_role_or_cross_project_identity_blocks_the_first_plan_command(self):
        for fault in ('roles','project'):
            with self.subTest(fault=fault):
                self.server.roles=['admin'] if fault=='roles' else ['reader']
                self.server.project='foreign-project' if fault=='project' else 'project-01'
                with patch.object(terraform_run,'command') as command, self.assertRaisesRegex(ValueError,'project-reader'):
                    self.command('version')
                command.assert_not_called()

    def test_executable_or_prepared_source_change_between_commands_denies_next_issuance(self):
        write_new(self.directory/'owned.tf.json',encoded({'owned':'source'}))
        with patch.object(terraform_run,'command',return_value=0) as command:
            self.command('version'); before=len(self.server.contacts)
            (self.directory/'owned.tf.json').write_bytes(encoded({'changed':'source'}))
            with self.assertRaisesRegex(ValueError,'prepared source'): self.command('init')
            self.assertEqual(len(self.server.contacts),before)
            (self.directory/'owned.tf.json').write_bytes(encoded({'owned':'source'}))
            self.binary.write_bytes(b'changed executable')
            with self.assertRaisesRegex(ValueError,'executable'): self.command('init')
        self.assertEqual(command.call_count,1); self.assertEqual(len(self.server.contacts),before)

    def test_caller_cannot_change_fixed_plan_arguments_or_output_purpose(self):
        with patch.object(terraform_run,'command') as command:
            with self.assertRaisesRegex(ValueError,'exact arguments'):
                terraform_run.authorized_command(self.contact,self.binary,self.directory,['version','-json','-other'],
                    {},self.operation/'version.json',planning_context=self.credentials)
        command.assert_not_called(); self.assertEqual(self.server.contacts,[])


class _ReadNative(_Native):
    def do_POST(self):
        self.server.contacts.append(('POST',self.path))
        if self.path != '/v1/sys/wrapping/unwrap':
            return self.respond(404,{})
        self.respond(200, {'lease_id':'read-lease-'+str(len(self.server.contacts)), 'lease_duration':30,
            'data':self.server.projection(), 'auth':None, 'wrap_info':None})


class ApplicationGuestReadTests(_Fixture):
    def setUp(self):
        super().setUp()
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        self.select()
        record=lambda scope: dict(zip(('organizationId','tenantId','locationId','securityDomainId',
            'endpointId','nativeScopeId','platformFamily'), vars(scope).values()))
        self.lifecycle=lifecycle_fixture(self.root,source_scope=record(self.source),destination_scope=record(self.destination))
        member=self.lifecycle.member('machine-1')
        row=member['phases']['VERIFY_READ']
        self.selection['applicationLifecycleSelectionDigest']=self.lifecycle.sha256
        self.grant=replace(self.grant,step_id=row['step_id'],operation_id=row['operation_id'])
        self.grants.grant=self.grant
        self.runtime=replace(self.runtime,grant=self.grant)
        self.server=ThreadingHTTPServer(('127.0.0.1',0),_ReadNative)
        tls=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls.load_cert_chain(str(self.pki.root/'server.pem'),str(self.pki.root/'server.key'))
        self.server.socket=tls.wrap_socket(self.server.socket,server_side=True)
        thread=threading.Thread(target=self.server.serve_forever,daemon=True); thread.start()
        self.addCleanup(self.server.server_close); self.addCleanup(self.server.shutdown)
        self.server.contacts=[]
        token=self.root/'read-agent'; write_new(token,b'synthetic-read-agent')
        issuer=VaultDynamicCredentialIssuer(vault_url=f'https://localhost:{self.server.server_port}',
            ca_bundle=self.pki.root/'ca.pem',agent_token_file=token,roles=(VaultDynamicRole(
                'vault:target-read','platform/creds/target-read',self.destination,'DISCOVER_READ',timedelta(minutes=1)),))
        self.enrollment=NativeReadEnrollment(self.runtime,self.admitted,_digest(self.selection),
            CredentialBroker(self.verifier,self.grants,issuer),VaultCredentialConsumer(issuer))
        writer_identity,writer_peer=self.additional_peer()
        binding=NativeBinding(self.destination.platform_family,self.destination.endpoint_id,
            self.destination.native_scope_id,'vm',member['target']['native_id'])
        self.writer=LifecycleWorkerRuntime(self.execution,_CurrentWorkerAuthority(self),_NativeRegistry(),self.context,
            OwnerLease(binding,'org-01','tenant-01','wsd-01','workload-01',writer_identity.subject,1,self.grant.expires_at),
            writer_identity,writer_peer,'writer-grant-01','writer-lease-01',self.destination)
        self.authority=self.runtime.select_application_reader(self.admitted,self.selection,self.lifecycle,
            'machine-1',ROOT,enrollment=self.enrollment,writer=self.writer,writer_native_user='hosting_writer')
        with patch.object(guest_run,'runtime_record',return_value={'ssh_path':'/usr/bin/ssh'}):
            self.args=configured(self.root)
        self.target=next(iter(load_private(self.args.bundle/'access.json')['targets'].values())) | {
            'native_id':binding.native_id,'machine_id':member['target']['machine_id'],'user':'hosting_reader'}
        self.ca=Ed25519PrivateKey.generate()
        self.profile=GuestReadCredentialProfile(self.ca.public_key().public_bytes(
            serialization.Encoding.OpenSSH,serialization.PublicFormat.OpenSSH),'hosting_reader','127.0.0.1/32')
        self.guest=GuestCommandRuntime(self.runtime,self.profile)
        self.certificates=[]
        self.server.projection=self.projection
        self.ssh=self.root/'read-ssh-transport-fixture'
        write_new(self.ssh,('#!/usr/bin/python3\nimport json,sys\n'
            'print(json.dumps({"argv":sys.argv[1:],"input":sys.stdin.buffer.read().decode()}))\n').encode())
        self.ssh.chmod(0o700)
        self.ssh_runtime={'python_path':'/usr/bin/python3','ssh_path':str(self.ssh),'ssh_sha256':digest(self.ssh.read_bytes())}


    def projection(self):
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        key=Ed25519PrivateKey.generate()
        certificate=(serialization.SSHCertificateBuilder().public_key(key.public_key())
            .serial(len(self.certificates)+1).type(serialization.SSHCertificateType.USER)
            .key_id(('hosting-read:'+self.grant.grant_id+':'+self.admitted.job_id+':'+self.lifecycle.sha256).encode())
            .valid_principals([self.profile.principal.encode()])
            .valid_after(int(utcnow().timestamp())-1).valid_before(int(utcnow().timestamp())+20)
            .add_critical_option(b'source-address',self.profile.source_range.encode()).sign(self.ca))
        self.certificates.append(certificate)
        return dict(format='hosting-application-ssh-read/1',grant_id=self.grant.grant_id,
            lifecycle_sha256=self.lifecycle.sha256,native_binding=list(self.authority.binding.key()),
            machine_id=self.authority.guest['machine_id'],user=self.target['user'],host_key=self.target['host_key'],
            private_key=key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.OpenSSH,
                serialization.NoEncryption()).decode(), certificate=certificate.public_bytes().decode())

    def forward_reader(self):
        from dataclasses import asdict
        from provisioner.migration.recovery import ApplicationRecoverySelection,DRIVER
        original=replace(self.admitted,job_id='original-application',plan_digest='c'*64)
        recovery=ApplicationRecoverySelection.from_record(dict(format='hosting-application-recovery-selection/1',
            mode='FORWARD_REPAIR',originalAdmitted=asdict(original),originalArtifactDigest='d'*64,
            originalLifecycleDigest='e'*64,currentLifecycleDigest=self.lifecycle.sha256,
            captures=[dict(memberId='machine-1',sourceFenceReceiptDigest='1'*64,
                           activationReceiptDigest='2'*64,captureReceiptDigest='3'*64)]))
        self.selection['driver']=DRIVER; self.selection['applicationRecoverySelectionDigest']=recovery.sha256
        self.plan['metadata']={'planDigest':self.admitted.plan_digest}
        self.plan['spec']['source']=dict(self.plan['spec']['destination'])
        self.plan['spec']['execution']={'driver':DRIVER,'artifactDigest':_digest(self.selection)}
        self.plan['spec']['selectedMachineIds']=['machine-1']
        self.plan['spec']['applicationRecovery']=recovery.plan_purpose()
        self.grant=replace(self.grant,source=self.destination); self.grants.grant=self.grant
        self.runtime=replace(self.runtime,grant=self.grant)
        self.enrollment=replace(self.enrollment,command=self.runtime,selection_digest=_digest(self.selection))
        self.guest=GuestCommandRuntime(self.runtime,self.profile)
        self.authority=self.runtime.select_application_reader(self.admitted,self.selection,self.lifecycle,'machine-1',ROOT,
            enrollment=self.enrollment,writer=self.writer,writer_native_user='hosting_writer',recovery=recovery)
        return recovery

    def test_exact_current_forward_repair_reader_can_observe_only_its_retained_target(self):
        recovery=self.forward_reader()
        result=json.loads(self.exchange('forward-target-health'))
        self.assertIn(self.authority.guest['native_uuid'],result['argv'][-1])
        self.assertEqual(self.writer.registry.calls,[])
        with self.assertRaisesRegex(ValueError,'retained-target repair reader'):
            self.runtime.select_application_reader(self.admitted,self.selection,self.lifecycle,'machine-1',ROOT,
                enrollment=self.enrollment,writer=self.writer,writer_native_user='hosting_writer',side='source',recovery=recovery)
        self.assertEqual(len(self.server.contacts),2)

    def test_forward_repair_read_cannot_ignore_changed_original_capture_or_scope_purpose(self):
        self.forward_reader()
        self.plan['spec']['applicationRecovery']['originalArtifactDigest']='f'*64
        with self.assertRaisesRegex(ValueError,'separately approved original purpose'):
            self.exchange('changed-forward-proof')
        self.assertEqual(self.server.contacts,[])

    def exchange(self, name, arguments=None, packet=None):
        output=self.root/name; output.mkdir(mode=0o700)
        if arguments is None:
            arguments=('/usr/bin/sudo','-n','--','/usr/bin/systemctl','show','--no-pager',
                       self.authority.guest['unit'],'--property=MainPID','--property=NoNewPrivileges')
        with patch.object(guest_run,'runtime_record',return_value=self.ssh_runtime):
            return self.guest.exchange(self.authority,target=self.target,binding=self.authority.binding,
                runtime=self.ssh_runtime,key=None,certificate=None,remote_argv=arguments,
                input_bytes=b'' if packet is None else encoded(packet),output=output)

    def test_independent_read_has_own_live_mtls_and_fresh_scoped_native_certificate_each_command(self):
        first=json.loads(self.exchange('first')); second=json.loads(self.exchange('second'))
        self.assertIn('hosting_reader',first['argv'])
        self.assertIn(self.authority.guest['native_uuid'],second['argv'][-1])
        self.assertEqual([cert.serial for cert in self.certificates],[1,2])
        self.assertEqual(len(self.server.contacts),4)
        self.assertEqual(self.writer.registry.calls,[])
        self.assertTrue(all(call[3]=={'purpose':'OBSERVATION'} for call in self.execution.calls[1:]))
        for name in ('first','second'):
            self.assertFalse((self.root/name/'ssh_key').exists())
            self.assertFalse((self.root/name/'ssh_key-cert.pub').exists())
            self.assertNotIn('BEGIN OPENSSH PRIVATE KEY',(self.root/name/'stdout').read_text())

    def test_read_revocation_blocks_next_native_credential_and_guest_command(self):
        self.exchange('first'); contacts=len(self.server.contacts)
        self.grants.revoked=True
        with self.assertRaises(GrantDenied): self.exchange('second')
        self.assertEqual(len(self.server.contacts),contacts)
        self.assertFalse((self.root/'second'/'stdout').exists())

    def test_read_cannot_dispatch_any_write_family_or_other_bootstrap_action(self):
        from provisioner.migration.remote_app import ACTION_BOOTSTRAP
        packet=dict(format='hosting-application-guest-action/1',job_id=self.admitted.job_id,
            operation_id=self.authority.operation_id,selection_sha256=self.lifecycle.sha256,
            guest=self.authority.guest,parameters={})
        commands=(('/usr/bin/systemctl','start',self.authority.guest['unit']),
            ('/usr/bin/systemd-run','--unit=foreign','/usr/bin/true'),('/usr/bin/restic','backup','/source'),
            ('/usr/bin/python3','-I','-S','-c',ACTION_BOOTSTRAP,encoded(self.authority.guest['action_runtime']).decode(),'REMOUNT_READWRITE'))
        for index,command in enumerate(commands):
            with self.subTest(command=command[0]),self.assertRaises(ValueError):
                self.exchange('refused-'+str(index),command,packet)
        self.assertEqual(self.server.contacts,[])

    def test_reader_does_not_borrow_writer_identity_native_account_or_activation_operation(self):
        with self.assertRaisesRegex(ValueError,'independently enrolled'):
            self.runtime.select_application_reader(self.admitted,self.selection,self.lifecycle,'machine-1',ROOT,
                enrollment=self.enrollment,writer=replace(self.writer,identity=self.identity,
                    lease=replace(self.writer.lease,worker_id=self.identity.subject)),writer_native_user='hosting_writer')
        self.guest=GuestCommandRuntime(self.runtime,replace(self.profile,principal='hosting_writer'))
        self.target=self.target | {'user':'hosting_writer'}
        with self.assertRaisesRegex(ValueError,'separate commissioned'): self.exchange('native-writer')
        self.grants.grant=replace(self.grant,operation_id=self.authority.member['phases']['ACTIVATE']['operation_id'])
        with self.assertRaises(GrantDenied): self.authority.require_current()

    def test_native_read_certificate_replay_wrong_ca_or_bound_resource_is_refused_before_ssh(self):
        original=self.projection()
        self.server.projection=lambda:original
        self.exchange('first')
        with self.assertRaisesRegex(ValueError,'replay state'): self.exchange('replay')
        self.server.projection=lambda: self.projection() | {'host_key':'foreign-host-key'}
        with self.assertRaisesRegex(ValueError,'original grant'): self.exchange('foreign-host')
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        self.guest=GuestCommandRuntime(self.runtime,replace(self.profile,ssh_ca_public=Ed25519PrivateKey.generate().public_key()
            .public_bytes(serialization.Encoding.OpenSSH,serialization.PublicFormat.OpenSSH)))
        self.server.projection=self.projection
        with self.assertRaisesRegex(ValueError,'certificate trust'): self.exchange('foreign-ca')
        for name in ('replay','foreign-host','foreign-ca'):
            self.assertFalse((self.root/name/'stdout').exists())
            self.assertFalse((self.root/name/'ssh_key').exists())

    def test_current_health_action_retains_own_read_operation_and_rejects_source_or_parameter_switch(self):
        from provisioner.migration.remote_app import ACTION_BOOTSTRAP
        command=('/usr/bin/sudo','-n','--','/usr/bin/python3','-I','-S','-c',ACTION_BOOTSTRAP,
                 encoded(self.authority.guest['action_runtime']).decode(),'HEALTH_PRODUCTION')
        packet=dict(format='hosting-application-guest-action/1',job_id=self.admitted.job_id,
            operation_id=self.authority.operation_id,selection_sha256=self.lifecycle.sha256,
            guest=self.authority.guest,parameters={'main_pid':42})
        result=json.loads(self.exchange('health',command,packet))
        self.assertEqual(json.loads(result['input'])['operation_id'],self.authority.operation_id)
        with self.assertRaisesRegex(ValueError,'bounded production process'):
            self.exchange('bad-process',command,packet | {'parameters':{'main_pid':True}})
        with self.assertRaisesRegex(ValueError,'original operation'):
            self.exchange('borrowed-write',command,packet | {'operation_id':self.authority.member['phases']['ACTIVATE']['operation_id']})
        self.authority.guest['action_runtime']['source_files']['provisioner/migration/guest_lifecycle.py']='f'*64
        with self.assertRaisesRegex(ValueError,'original independent application read|original deployed source'):
            self.exchange('switched-source',command,packet)

    def test_initial_target_dataset_read_cannot_change_approved_path_budget_or_side(self):
        from provisioner.migration.remote_app import ACTION_BOOTSTRAP
        command=('/usr/bin/python3','-I','-S','-c',ACTION_BOOTSTRAP,
                 encoded(self.authority.guest['action_runtime']).decode(),'DATA_OBSERVE')
        packet=dict(format='hosting-application-guest-action/1',job_id=self.admitted.job_id,
            operation_id=self.authority.operation_id,selection_sha256=self.lifecycle.sha256,guest=self.authority.guest,
            parameters={'path':self.authority.member['initial_target_path'],'max_bytes':self.authority.member['max_bytes']})
        self.exchange('initial-read',command,packet)
        contacts=len(self.server.contacts)
        for index,parameters in enumerate((packet['parameters'] | {'path':'/another-dataset'},
                                          packet['parameters'] | {'max_bytes':2**40})):
            with self.assertRaises(ValueError): self.exchange('switched-initial-'+str(index),command,packet | {'parameters':parameters})
        self.authority.side='source'
        with self.assertRaises(ValueError): self.exchange('source-initial',command,packet)
        self.assertEqual(len(self.server.contacts),contacts)


class GuestCommandTests(_Fixture):
    def setUp(self):
        super().setUp()
        self.grant=replace(self.grant,operation_kind='GUEST_CONFIG',operation_id='guest-01')
        with patch.object(guest_run,'runtime_record',return_value={'ssh_path':'/usr/bin/ssh'}):
            self.args=configured(self.root)
        access=load_private(self.args.bundle/'access.json')
        self.target=next(iter(access['targets'].values()))
        self.selection_scope = {key:value for key,value in access['scope'].items() if key != 'phase'}
        self.destination=replace(self.destination,site_id=access['scope']['site_key'],
            tenant_id=access['scope']['tenant_key'],security_domain_id=access['scope']['wsd_key'])
        # These source fixtures use tenant/site labels; keep the actual TLS identity
        # fixed by selecting fixtures with matching immutable labels instead.
        self.destination=replace(self.grant.destination,platform_family=access['scope']['platform'])
        self.grant=replace(self.grant,operation_scope=self.destination,destination=self.destination)
        self.authority=self.select(kind='guest_apply')
        self.binding=NativeBinding(self.destination.platform_family,self.destination.endpoint_id,
                                  self.destination.native_scope_id,'vm',self.target['native_id'])
        self.guest=GuestCommandRuntime(self.runtime)
        lease=OwnerLease(self.binding,self.context.organization_id,self.context.tenant_id,
            self.destination.security_domain_id,'workload-01',self.identity.subject,1,self.grant.expires_at)
        self.registry=_NativeRegistry()
        self.native=ObservedProvisioningRuntime(self.execution,_CurrentWorkerAuthority(self),self.registry,
            self.context,lease,self.identity,self.peer,self.grant.grant_id,self.grant.lease_key,
            self.grant.operation_id,self.grant.operation_scope,guest_commands=self.guest)
        self.intent=ObservedProvisioningGuard(self.native,self.admitted,self.selection,self.step,'GUEST_CONFIG')
        self.authority=self.runtime.select(self.admitted,self.selection,self.delivery,self.step,self.packet,ROOT,
                                          intent_guard=self.intent)
        self.native._claim(self.intent,{'kind':'guest_apply','original_bundle':digest(read_private(self.args.bundle/'bundle.json'))})

    def guest_context(self):
        return GuestExecutionContext(self.guest,self.authority,self.args.bundle,self.binding,self.args.approval,ROOT)

    def test_unclaimed_original_guest_intent_cannot_start_remote_controller(self):
        self.intent.claimed=False
        with self.assertRaisesRegex(ValueError,'configuration authority'): self.guest_context()

    def _exchange(self, output, *, target=None, arguments=('/usr/bin/systemctl','show','--no-pager','hosting-test.service')):
        ssh = self.root/'ssh-native-transport-fixture'
        if not ssh.exists():
            write_new(ssh, ('#!/usr/bin/python3\nimport json,sys\n'
                'print(json.dumps({"argv":sys.argv[1:],"input_size":len(sys.stdin.buffer.read())}))\n').encode())
            ssh.chmod(0o700)
        key, certificate = self.root/'exchange-key', self.root/'exchange-cert'
        if not key.exists():
            write_new(key,b'synthetic transport key'); write_new(certificate,b'synthetic transport certificate')
        output.mkdir(mode=0o700)
        runtime={'python_path':'/usr/bin/python3','ssh_path':str(ssh),'ssh_sha256':digest(ssh.read_bytes())}
        with patch.object(guest_run,'runtime_record',return_value=runtime):
            return self.guest.exchange(self.authority,target=target or self.target,binding=self.binding,
                runtime=runtime,key=key,certificate=certificate,remote_argv=arguments,
                input_bytes=b'original-bounded-input',output=output)

    def test_actual_exchange_checks_native_target_and_dispatches_one_bounded_process(self):
        output=self.root/'exchange-first'
        result=json.loads(self._exchange(output))
        self.assertEqual(result['input_size'],len(b'original-bounded-input'))
        self.assertIn(self.target['machine_id'],result['argv'][-1])
        self.assertIn('/usr/bin/systemctl show',result['argv'][-1])
        self.assertIn('StrictHostKeyChecking=yes',result['argv'])
        self.assertFalse((output/'ssh_key').exists())
        self.assertFalse((output/'ssh_key-cert.pub').exists())
        self.assertEqual(self.grants.calls[-1]['operation_id'],'guest-01')

    def test_revocation_between_actual_guest_exchanges_stops_next_process(self):
        self._exchange(self.root/'exchange-first')
        self.grants.revoked=True
        output=self.root/'exchange-second'
        with self.assertRaises(GrantDenied): self._exchange(output)
        self.assertFalse((output/'stdout').exists())

    def test_changed_native_member_or_unclaimed_intent_stops_before_actual_exchange(self):
        with self.assertRaisesRegex(ValueError,'native resource'):
            self._exchange(self.root/'exchange-switched',target=self.target | {'native_id':'foreign-01'})
        self.intent.claimed=False
        with self.assertRaisesRegex(ValueError,'claimed'):
            self._exchange(self.root/'exchange-unclaimed')

    def plugin(self):
        source=ROOT/'ansible/connection_plugins/hosting_guarded_ssh.py'
        spec=importlib.util.spec_from_file_location('fixture_guarded_ssh',source)
        module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        connection=module.Connection.__new__(module.Connection)
        values={'host':self.target['address'],'port':self.target['port'],'remote_user':self.target['user']}
        connection.get_option=lambda name: values[name]
        session={'socket':'/not-contacted','binding_digest':'c'*64,'target':self.target,
                 'native':self.binding.key(),'ssh':'/usr/bin/ssh'}
        return module,connection,session

    def test_actual_connection_plugin_blocks_retry_after_between_command_revocation(self):
        from ansible.errors import AnsibleConnectionFailure
        from ansible.plugins.connection.ssh import Connection
        module,connection,session=self.plugin()
        checks=[]
        def authorize(_session,**request):
            checks.append(request); self.authority.require_current()
        def remote(*args,**_):
            self.assertIn(self.target['machine_id'],args[0][-1].decode())
            self.grants.revoked=True
            return 255,b'',b'disposable transport failed'
        argv=[b'/usr/bin/ssh',self.target['address'].encode(),b'/usr/bin/true']
        with patch.dict(os.environ,{'HOSTING_GUEST_COMMAND_SESSION':'/fixture-only'}), \
             patch.object(module.client,'load_session',return_value=session), \
             patch.object(module.client,'authorize',side_effect=authorize), \
             patch.object(Connection,'_bare_run',side_effect=remote) as native:
            with self.assertRaises(AnsibleConnectionFailure): connection._bare_run(argv,None)
            with self.assertRaises(AnsibleConnectionFailure): connection._bare_run(argv,None)
        self.assertEqual(native.call_count,1)
        self.assertEqual(len(checks),3)

    def test_connection_plugin_refuses_an_endpoint_switch_before_authorization_or_ssh(self):
        from ansible.errors import AnsibleConnectionFailure
        from ansible.plugins.connection.ssh import Connection
        module,connection,session=self.plugin()
        argv=[b'/usr/bin/ssh',b'192.0.2.99',b'/usr/bin/true']
        with patch.dict(os.environ,{'HOSTING_GUEST_COMMAND_SESSION':'/fixture-only'}), \
             patch.object(module.client,'load_session',return_value=session), \
             patch.object(module.client,'authorize') as authority, \
             patch.object(Connection,'_bare_run') as native:
            with self.assertRaises(AnsibleConnectionFailure): connection._bare_run(argv,None)
        authority.assert_not_called(); native.assert_not_called()

    @unittest.skipUnless(UNIX_AVAILABLE, 'Actual AF_UNIX creation denied by local container (EPERM); hosted check required')
    def test_private_authorizer_stops_next_guest_command_after_original_revocation(self):
        with patch.object(guest_apply,'validate_bundle',return_value=(
                {'operation_id':'guest-01','scope':self.scope|{'phase':'workloads'},'source_commit':'a'*40},
                {'targets':{'guest-01':self.target}}, {'ssh_path':'/usr/bin/ssh'})):
            context=self.guest_context()
            with self.assertRaises(GrantDenied), context.controller({'ssh_path':'/usr/bin/ssh'}) as bound:
                session=guest_command_client.load_session(bound['session'])
                guest_command_client.authorize(session,command=['owned-first-command'])
                self.grants.revoked=True
                with self.assertRaises(PermissionError):
                    guest_command_client.authorize(session,command=['owned-next-command'])

    @unittest.skipUnless(UNIX_AVAILABLE, 'Actual AF_UNIX creation denied by local container (EPERM); hosted check required')
    def test_listener_rejects_old_mtls_context_and_rehashed_service_or_guest_bundle(self):
        with patch.object(guest_apply,'validate_bundle',return_value=(
                {'operation_id':'guest-01','scope':self.scope|{'phase':'workloads'},'source_commit':'a'*40},
                {'targets':{'guest-01':self.target}}, {'ssh_path':'/usr/bin/ssh'})):
            context=self.guest_context()
            with self.assertRaises(GrantDenied), context.controller({'ssh_path':'/usr/bin/ssh'}) as bound:
                session=guest_command_client.load_session(bound['session'])
                self.verifier.reload_trust()
                with self.assertRaises(PermissionError):
                    guest_command_client.authorize(session,command=['owned-next-command'])

    @unittest.skipUnless(UNIX_AVAILABLE, 'Actual AF_UNIX creation denied by local container (EPERM); hosted check required')
    def test_listener_rejects_replayed_command_request_and_switched_private_session(self):
        with patch.object(guest_apply,'validate_bundle',return_value=(
                {'operation_id':'guest-01','scope':self.scope|{'phase':'workloads'},'source_commit':'a'*40},
                {'targets':{'guest-01':self.target}}, {'ssh_path':'/usr/bin/ssh'})):
            context=self.guest_context()
            with context.controller({'ssh_path':'/usr/bin/ssh'}) as bound:
                session=guest_command_client.load_session(bound['session'])
                request={'format':'hosting-guest-command-check/1','request_id':uuid4().hex,
                    'binding_digest':session['binding_digest'],'command_digest':digest(b'original'),
                    'input_digest':digest(b'original-input')}
                def send():
                    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as peer:
                        peer.settimeout(3); peer.connect(session['socket'])
                        peer.sendall(guest_command_client.encoded(request)+b'\n'); peer.shutdown(socket.SHUT_WR)
                        return json.loads(peer.recv(4096))
                self.assertEqual(send()['status'],'CURRENT_ORIGINAL_COMMAND')
                self.assertEqual(send()['status'],'HELD')
                replacement=session | {'target':session['target'] | {'address':'192.0.2.99'}}
                bound['session'].write_bytes(encoded(replacement))
                with self.assertRaises(PermissionError):
                    guest_command_client.authorize(session,command=['owned-next-command'])

    @unittest.skipUnless(UNIX_AVAILABLE, 'Actual AF_UNIX creation denied by local container (EPERM); hosted check required')
    def test_listener_rechecks_original_bundle_before_next_command(self):
        with patch.object(guest_apply,'validate_bundle',return_value=(
                {'operation_id':'guest-01','scope':self.scope|{'phase':'workloads'},'source_commit':'a'*40},
                {'targets':{'guest-01':self.target}}, {'ssh_path':'/usr/bin/ssh'})):
            context=self.guest_context()
            with self.assertRaisesRegex(ValueError,'guest bundle changed'), context.controller({'ssh_path':'/usr/bin/ssh'}) as bound:
                session=guest_command_client.load_session(bound['session'])
                guest_command_client.authorize(session,command=['owned-first-command'])
                (self.args.bundle/'bundle.json').write_bytes(encoded({'switched':'artifact'}))
                with self.assertRaises(PermissionError):
                    guest_command_client.authorize(session,command=['owned-next-command'])

    @unittest.skipUnless(UNIX_AVAILABLE, 'Actual AF_UNIX creation denied by local container (EPERM); hosted engine check required')
    def test_real_ansible_selects_guarded_connection_and_retains_unreachable_attempt(self):
        folder=self.root/'engine'; folder.mkdir(mode=0o700)
        ssh=folder/'ssh-fixture'; calls=folder/'ssh-argv.json'
        ssh.write_text('#!/usr/bin/python3\nimport json,sys\nfrom pathlib import Path\n'
            + 'Path('+repr(str(calls))+').write_text(json.dumps(sys.argv[1:]))\nraise SystemExit(255)\n')
        ssh.chmod(0o700)
        args=configured(folder,ssh=ssh)
        with patch.object(guest_run,'verify',return_value={'status':'HASHES_MATCH','commit':'a'*40}):
            context=GuestExecutionContext(self.guest,self.authority,args.bundle,self.binding,args.approval,ROOT)
            with self.assertRaises(ValueError):
                guest_apply.apply(args,root=ROOT,guest_context=context)
        self.assertTrue(calls.exists(),(args.bundle/'ansible.log').read_text())
        self.assertIn(self.target['machine_id'],json.loads(calls.read_text())[-1])
        result=load_private(args.bundle/'result.json')
        self.assertEqual(result['status'],'HOLD_RECONCILIATION_REQUIRED')
        self.assertFalse(result['native_acceptance'])
        self.assertFalse((args.bundle/'runtime/ssh_key').exists())


if __name__ == '__main__': unittest.main()
