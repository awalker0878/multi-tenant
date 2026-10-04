"""Saved-plan closure plus real loopback TLS Vault/Keystone credential refresh.

Terraform processes, grant persistence and mTLS enrollment are synthetic here;
real PostgreSQL claim/revocation/expiry tests live in test_planned_creation. These
tests confer no native deployment or application qualification.
"""
import argparse
from dataclasses import replace
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import ssl
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from provisioner.allocations.transactions import PoolDemand, ResourceBundle
from provisioner.controlplane.authority.model import PlanScope, WorkerGrant
from provisioner.controlplane.persistence import NativeBinding, TenantContext
from provisioner.controlplane.reconciliation.planned import NativeCreationObservation, PlannedResourceLease, deployment_id
from provisioner.controlplane.reconciliation.registry import NativeObservation, RecoveryHeld
from provisioner.controlplane.reconciliation.planned_terraform import (
    EphemeralOpenStackApplyContext, PlannedTerraformRuntime, VaultOpenStackCredentialConsumer)
from provisioner.controlplane.worker.grants import CredentialBroker, GrantDenied, VerifiedWorkerIdentity
from provisioner.controlplane.worker.vault import VaultDynamicCredentialIssuer, VaultDynamicRole
from provisioner.controlplane.workflow.admitted_job import AdmittedInput
from provisioner.execution import delivery_steps, readback_core as c, terraform_run, terraform_apply
from provisioner.execution.run_files import digest, encoded, file_map, load_private, read_private, utcnow, write_new
from provisioner.compiler.wsd import STATE
from tests.provisioning.worker.tls_fixtures import TestPki
from tests.test_terraform_run import TerraformRunFixture


class _NativeHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.server.contacts.append(('GET',self.path))
        self.respond(200,{'data':None,'auth':None,'wrap_info':{
            'token':'single-use-test-wrap','ttl':90,'creation_path':'platform/creds/target-create'}})

    def do_POST(self):
        self.server.contacts.append(('POST',self.path))
        if self.path=='/v1/sys/wrapping/unwrap':
            self.respond(200,{'lease_id':'ephemeral-test-lease','lease_duration':60,
                'data':self.server.data,'auth':None,'wrap_info':None})
        elif self.path=='/v3/auth/tokens':
            self.respond(201,{'token':{'project':{'id':self.server.project},
                'application_credential':{'id':'fresh-test-app'},'methods':['application_credential'],
                'expires_at':(utcnow()+timedelta(hours=1)).isoformat(),
                'catalog':[{'type':'compute','endpoints':[{'interface':'internal','region':'region-1',
                    'url':self.server.compute}]}]}},token=True)
        else: self.respond(404,{})

    def respond(self,status,payload,*,token=False):
        body=encoded(payload); self.send_response(status)
        self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(body)))
        if token: self.send_header('X-Subject-Token','loopback-test-token')
        self.end_headers(); self.wfile.write(body)

    def log_message(self,*_): pass


class _FixtureVerifier:
    def __init__(self,identity): self.identity=identity
    def verify(self,_): return self.identity


class _FixtureGrants:
    def __init__(self,grant): self.grant=grant
    def with_authorized_reference(self,context,identity,grant_id,*,use,**_):
        if grant_id!=self.grant.grant_id: raise GrantDenied('Local-only grant differs')
        return use('vault:target-create',self.grant,self.grant.expires_at)


class _FixtureAuthority:
    def __init__(self): self.revoked=False; self.calls=0
    def require_current(self,*_,**__):
        self.calls+=1
        if self.revoked: raise GrantDenied('Local-only authority revoked')
    def require_packet(self,*_):
        if self.revoked: raise GrantDenied('Local-only authority revoked')


class _FixtureRegistry:
    """Only local composition tracing; actual owner tests use real PostgreSQL."""
    def __init__(self,directory):
        self.state='PREPARED'; self.claims=0; self.fail_readback=False; self.directory=directory
    def prepare(self,*_,**__): return SimpleNamespace(state=self.state)
    def claim_once(self,*_):
        if self.state!='PREPARED': return False
        self.claims+=1; self.state='IN_FLIGHT'; return True
    def get(self,*_): return SimpleNamespace(state=self.state)
    def mark_uncertain(self,*_): self.state='UNCERTAIN'
    def acknowledge_created(self,*_):
        if (self.directory/'owner-completion.json').exists(): raise AssertionError('Premature delivery marker')
        if self.fail_readback: raise RecoveryHeld('Local independent readback is unavailable')
        self.state='RESOLVED'


class _FixtureObserver:
    def observe_creation(self,context,lease,operation,bundle,prepared):
        actual=NativeBinding('openstack',lease.scope.endpoint_id,lease.scope.native_scope_id,'vm','synthetic-server-01')
        native=NativeObservation('local-observation','a'*64,'independent-reader',None,'EFFECT_PRESENT',True,utcnow())
        return NativeCreationObservation(native,(actual,))


class EphemeralSavedPlanTests(TerraformRunFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.pki=TestPki(); self.addCleanup(self.pki.close); self.pki.issue('server')
        self.server=ThreadingHTTPServer(('127.0.0.1',0),_NativeHandler)
        tls=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls.load_cert_chain(str(self.pki.root/'server.pem'),str(self.pki.root/'server.key'))
        self.server.socket=tls.wrap_socket(self.server.socket,server_side=True)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True); self.thread.start()
        self.addCleanup(self.server.server_close); self.addCleanup(self.server.shutdown)
        self.origin=f'https://localhost:{self.server.server_port}'
        self.server.contacts=[]; self.server.project='project-01'; self.server.compute=self.origin+'/v2.1/project-01'
        self.inputs=json.loads((terraform_run.ROOT/'terraform/stacks/wsd/openstack/workloads/inputs.tfvars.json.example').read_text())
        self.inputs.update(allow_restricted_build=True,test_authorization_ref='LOCAL-ONLY',openstack_cloud='test-cloud')
        self.args.catalog_id='openstack-wsd-workloads'
        self.entry,self.scope,self.state_key=terraform_run.select_scope(terraform_run.ROOT,self.args.catalog_id,self.inputs)
        self.backend['state_key']=self.state_key
        self.credentials={'TF_HTTP_USERNAME':'old-state-user','TF_HTTP_PASSWORD':'old-test-only-state-secret'}
        self.old_cloud={'clouds':{'test-cloud':{'auth_type':'v3applicationcredential','verify':True,
            'region_name':'region-1','interface':'internal','auth':{'auth_url':self.origin+'/v3',
            'application_credential_id':'old-test-app','application_credential_secret':'old-test-secret'}}}}
        self.args.cloud=self.base/'cloud.json'; self.args.ca_bundle=self.base/'ca.pem'
        write_new(self.args.cloud,encoded(self.old_cloud))
        write_new(self.args.ca_bundle,(self.pki.root/'ca.pem').read_bytes())
        self.authority.update(scope=self.scope,input_sha256=digest(encoded(self.inputs)),
            backend_sha256=digest(encoded(self.backend)),environment_sha256=digest(encoded(self.credentials)),
            cloud_sha256=digest(encoded(self.old_cloud)),ca_sha256=digest(read_private(self.args.ca_bundle)))
        for key,value in {'inputs':self.inputs,'backend':self.backend,'environment':self.credentials,
                          'authority':self.authority}.items(): (self.base/key).write_bytes(encoded(value))
        self.delivery_base=self.base
        for name in ('delivery-ledger','selected-plan','runs','original-run'):
            self.delivery_base=self.delivery_base/name; self.delivery_base.mkdir(mode=0o700)
        (self.delivery_base/'steps').mkdir(mode=0o700); (self.delivery_base/'steps'/'plan').mkdir(mode=0o700)
        self.args.output=self.delivery_base/'steps'/'plan'/'execution'
        self.prepare()
        self.saved=load_private(self.args.output/'bundle.json')
        now=utcnow(); self.context=TenantContext('org-01',self.scope['tenant_key'])
        native_scope=PlanScope('org-01',self.scope['tenant_key'],self.scope['site_key'],self.scope['wsd_key'],
                              'openstack-01','project-01','openstack')
        catalog={'format':'hosting-capacity-sizing/1','pool_id':'pool-01','origin':self.origin,
            'native_id':'project-01','platform':'openstack','site_key':self.scope['site_key'],
            'provider_selector':{'openstack_cloud':'test-cloud'},'cloud_sha256':self.authority['cloud_sha256'],
            'placements':[{key:member[key] for key in ('compute_availability_zone','storage_availability_zone','volume_type')}
                          for member in self.inputs['members'].values()],
            'flavors':{'mock-flavor':{'vcpu':2,'ram_mib':4096,'root_gib':0,'ephemeral_gib':0,'swap_mib':0}},
            'valid_from':(now-timedelta(minutes=1)).isoformat(),'valid_until':(now+timedelta(minutes=30)).isoformat(),
            'acceptance_ref':'LOCAL-ONLY'}
        zero={'vcpu':0,'memory_mb':0,'storage_gb':0}
        demand=PoolDemand.from_workload(scope=native_scope,catalog=catalog,inputs=self.inputs,
            envelope_sha256='e'*64,budgets={key:zero for key in ('staging','snapshots','retained-source')},
            capabilities=('internal-ipv4',))
        self.admitted=AdmittedInput('job-01','org-01',native_scope.tenant_id,'plan-01',1,'a'*64,0,'b'*64)
        self.bundle=ResourceBundle(self.admitted,'d'*64,'workload-01',1,(demand,))
        self.identity=VerifiedWorkerIdentity('org-01',native_scope.tenant_id,'worker-01',native_scope.site_id,
                                             'c'*64,now+timedelta(minutes=10))
        self.grant=WorkerGrant('grant-01','org-01',native_scope.tenant_id,'plan-01',1,'a'*64,native_scope,
            native_scope,'worker-01','apply','operation-01','VM_CREATE',native_scope,'lease-01',1,
            ('approval-01',),0,now,now+timedelta(minutes=2))
        self.lease=PlannedResourceLease('org-01',native_scope.tenant_id,'job-01',deployment_id(self.bundle,native_scope),
            'deployment','d'*64,'f'*64,'0'*64,native_scope,'workload-01','worker-01',1,now+timedelta(minutes=2))
        token_file=self.base/'vault-agent-token'; write_new(token_file,b'local-vault-agent-token')
        self.issuer=VaultDynamicCredentialIssuer(vault_url=self.origin,ca_bundle=self.args.ca_bundle,
            agent_token_file=token_file,roles=(VaultDynamicRole('vault:target-create','platform/creds/target-create',
                native_scope,'VM_CREATE',timedelta(minutes=2)),))
        fresh=json.loads(json.dumps(self.old_cloud)); fresh['clouds']['test-cloud']['auth'].update(
            application_credential_id='fresh-test-app',application_credential_secret='fresh-test-only-secret')
        self.server.data={'environment':{'TF_HTTP_USERNAME':'fresh-state-user','TF_HTTP_PASSWORD':'fresh-test-state-secret'},
                          'cloud':fresh}
        self.runtime=object.__new__(PlannedTerraformRuntime)  # synthetic owner; production constructor rejects these ports
        self.runtime.context,self.runtime.lease,self.runtime.identity,self.runtime.grant=self.context,self.lease,self.identity,self.grant
        self.runtime.broker=CredentialBroker(_FixtureVerifier(self.identity),_FixtureGrants(self.grant),self.issuer)
        self.runtime.consumer=VaultOpenStackCredentialConsumer(self.issuer); self.runtime.transport_evidence=object()
        self.runtime.authority=_FixtureAuthority()
        self.selection={'executionScope':{key:value for key,value in self.scope.items() if key!='phase'}}
        self.bundle=replace(self.bundle,selection_digest=c.digest(self.selection))
        self.runtime.lease=replace(self.lease,selection_digest=self.bundle.selection_digest)
        self.runtime.bundles=lambda *_:self.bundle
        self.approval={'format':'hosting-terraform-approval/1','bundle_sha256':digest(read_private(self.args.output/'bundle.json')),
            'review_sha256':digest(read_private(self.args.output/'review.json')),'operation_id':self.saved['operation_id'],
            'generation':self.saved['generation'],'valid_from':(now-timedelta(seconds=1)).isoformat(),
            'valid_until':(now+timedelta(minutes=10)).isoformat(),'change_ref':'LOCAL-ONLY'}
        self.approval_path=self.base/'apply-approval'; write_new(self.approval_path,encoded(self.approval))
        self.ledger=self.base/'owner-ledger'; self.ledger.mkdir(mode=0o700); self.applies=[]
        self.apply_directory=self.delivery_base/'steps'/'apply'; self.apply_directory.mkdir(mode=0o700)
        self.runtime.registry=_FixtureRegistry(self.apply_directory); self.runtime.observer=_FixtureObserver()
        # This suite's B10/persistence ports are explicit process doubles.
        # Exact custody/revoke protocol and PostgreSQL closure have their own
        # tests; still enforce their position before the completion marker.
        from provisioner.controlplane.worker.native_retirement import CompletedNativeGrantRetirement
        self.runtime.retirement=object.__new__(CompletedNativeGrantRetirement)
        self.retirements=[]
        def retired(*_):
            self.assertEqual(self.runtime.registry.state,'RESOLVED')
            self.assertFalse((self.apply_directory/'owner-completion.json').exists())
            self.retirements.append('sealed');return 'e'*64
        self.retirement_patch=patch.object(CompletedNativeGrantRetirement,'retire',side_effect=retired)
        self.retirement_patch.start();self.addCleanup(self.retirement_patch.stop)
        from provisioner.controlplane.reconciliation.application_accounting import ApplicationResourceAccounting
        self.runtime.resource_accounting=object.__new__(ApplicationResourceAccounting)
        self.confirmations=[]
        def confirmed(*_):
            self.assertEqual(self.retirements,['sealed'])
            self.assertFalse((self.apply_directory/'owner-completion.json').exists())
            self.confirmations.append('confirmed')
        self.accounting_patch=patch.object(ApplicationResourceAccounting,'confirm_creation',side_effect=confirmed)
        self.accounting_patch.start();self.addCleanup(self.accounting_patch.stop)
        self.delivery={'format':'hosting-delivery/2','source_commit':self.source,'operation_id':'delivery-01',
            'generation':1,'scope':self.selection['executionScope'],
            'steps':[{'id':'plan','kind':'terraform_plan','needs':[]},
                     {'id':'apply','kind':'terraform_apply','needs':['plan']}]}
        write_new(self.args.output.parent/'bundle.json',read_private(self.args.output/'bundle.json'))
        write_new(self.args.output.parent/'packet.json',encoded({'parameters':{'terraform':str(self.binary),
            'terraform_sha256':digest(self.binary.read_bytes())}}))
        self.packet={'parameters':{'prepared_step':'plan'},'files':{'approval':{
            'path':str(self.approval_path),'sha256':digest(read_private(self.approval_path))}}}

    def bind(self):
        return EphemeralOpenStackApplyContext(self.runtime,self.admitted,self.selection,self.bundle,self.args.output,self.saved)

    def engine_apply(self,binary,directory,argv,environment,output,**kwargs):
        self.applies.append((argv,environment,kwargs['timeout']))
        value={'scope':{'value':self.scope},'delivery_state':{'value':STATE},
            'members':{'value':{name:{'delivery_state':STATE} for name in self.inputs['members']}}}
        write_new(output,encoded(value) if argv[0]=='output' else b'local-engine-only')

    def apply(self,context):
        args=argparse.Namespace(bundle=self.args.output,approval=self.approval_path,terraform=self.binary,
                               ledger=self.ledger,execute_approved_change=True)
        with patch.object(terraform_apply,'verify',return_value={'status':'HASHES_MATCH','commit':self.source}),\
                patch.object(terraform_apply,'command',side_effect=self.engine_apply):
            return terraform_apply.apply(args,openstack_apply_context=context)

    def run_step(self):
        with patch.object(terraform_apply,'verify',return_value={'status':'HASHES_MATCH','commit':self.source}),\
                patch.object(terraform_apply,'command',side_effect=self.engine_apply):
            return self.runtime.run_step(self.admitted,self.selection,self.delivery,self.delivery['steps'][1],
                self.packet,self.apply_directory,self.delivery_base,terraform_run.ROOT)

    def test_fresh_secrets_keep_actual_saved_plan_source_input_and_cloud_projection_unchanged(self):
        before=file_map(self.args.output/'source'); saved=read_private(self.args.output/'saved.tfplan')
        context=self.bind(); result=self.apply(context)
        self.assertEqual(result['status'],'APPLIED_REQUIRES_NATIVE_ACCEPTANCE')
        self.assertEqual([row[0][0] for row in self.applies],['apply','output'])
        self.assertEqual(self.applies[0][0][-1],str(self.args.output/'saved.tfplan'))
        self.assertEqual(self.applies[0][1]['TF_HTTP_USERNAME'],'fresh-state-user')
        self.assertEqual(load_private(context.cloud_path)['clouds']['test-cloud']['auth']['application_credential_id'],'fresh-test-app')
        self.assertEqual(load_private(self.args.output/'source'/self.saved['root']/'clouds.yaml')['clouds']['test-cloud']['auth']['application_credential_id'],'old-test-app')
        self.assertEqual(file_map(self.args.output/'source'),before); self.assertEqual(read_private(self.args.output/'saved.tfplan'),saved)
        self.assertTrue(all(0<row[2]<=60 for row in self.applies)); self.assertGreaterEqual(self.runtime.authority.calls,5)
        self.assertNotIn('fresh-test-only-secret',read_private(context.directory/'binding.json').decode())

    def test_project_endpoint_and_nonsecret_profile_drift_stop_before_apply(self):
        for field,value in [('project','foreign-project'),('compute','https://foreign.example/v2.1')]:
            original=getattr(self.server,field); setattr(self.server,field,value)
            with self.subTest(field=field),self.assertRaises(GrantDenied): self.bind()
            setattr(self.server,field,original)
        self.server.data['cloud']['clouds']['test-cloud']['region_name']='foreign-region'
        with self.assertRaisesRegex(ValueError,'cannot change'): self.bind()
        self.assertEqual(self.applies,[])

    def test_revoked_grant_and_changed_private_overlay_hold_before_native_process(self):
        context=self.bind(); self.runtime.authority.revoked=True
        with self.assertRaises(GrantDenied): self.apply(context)
        self.runtime.authority.revoked=False
        context.cloud_path.write_bytes(encoded(self.old_cloud))
        with self.assertRaisesRegex(ValueError,'binding changed'): self.apply(context)
        self.assertEqual(self.applies,[])

    def test_changed_saved_plan_cannot_be_hidden_by_refreshed_credentials(self):
        context=self.bind(); (self.args.output/'saved.tfplan').write_bytes(b'FOREIGN BINARY PLAN')
        with self.assertRaisesRegex(ValueError,'artifact changed'): self.apply(context)
        self.assertEqual(self.applies,[])

    def test_native_creation_acknowledgement_precedes_delivery_completion(self):
        result,names=self.run_step()
        self.assertEqual(result['status'],'APPLIED_REQUIRES_NATIVE_ACCEPTANCE')
        self.assertEqual(self.runtime.registry.state,'RESOLVED')
        self.assertIn('owner-completion.json',names)
        self.assertEqual(self.retirements,['sealed'])
        self.assertEqual(self.confirmations,['confirmed'])
        with self.assertRaises(RecoveryHeld): self.run_step()
        self.assertEqual(self.runtime.registry.claims,1); self.assertEqual(len(self.applies),2)

    def test_failed_independent_readback_keeps_one_uncertain_claim_and_no_completion_marker(self):
        self.runtime.registry.fail_readback=True
        with self.assertRaises(RecoveryHeld): self.run_step()
        self.assertEqual(self.runtime.registry.state,'UNCERTAIN')
        self.assertFalse((self.apply_directory/'owner-completion.json').exists())
        with self.assertRaises(RecoveryHeld): self.run_step()
        self.assertEqual(self.runtime.registry.claims,1); self.assertEqual(len(self.applies),2)


if __name__=='__main__': unittest.main()
