"""Real pinned TLS Vault/Keystone/native cleanup, explicit authority fixtures.

Only current enrollment/journal persistence below is synthetic. The native
protocol sockets, single-use unwrap, DELETE and independent hard-delete action
inspection are real. This is not a native installation or a qualified campaign.
"""
from copy import deepcopy
from dataclasses import asdict,replace
from datetime import timedelta
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from provisioner.allocations.transactions import PoolDemand,ResourceBundle
from provisioner.controlplane.discovery.adapters.openstack import OpenStackServiceEndpoints
from provisioner.controlplane.persistence import NativeBinding
from provisioner.controlplane.reconciliation.adapters.openstack_cleanup import (
    OriginalOpenStackChild,OpenStackCleanupReadbackOwner,EnrolledOpenStackCleanupRuntime,
    OpenStackCleanupGuard,NativeCleanupPending,_CleanupReader,_CleanupWriter)
from provisioner.controlplane.reconciliation.registry import NativeOperation,NativeObservation
from provisioner.controlplane.worker.grants import GrantDenied
from provisioner.controlplane.worker.vault import VaultDynamicRole,VaultDynamicCredentialIssuer
from provisioner.controlplane.worker.vault_consumer import VaultCredentialConsumer
from provisioner.execution import readback_core as c
from provisioner.execution.run_files import encoded,load_private,utcnow
import tests.provisioning.reconciliation.test_enrolled_openstack_readback as fixture


PROJECT='20000000-0000-4000-8000-000000000001'
REQUEST_ID='req-20000000-0000-4000-8000-000000000002'
SERVER,PORT,VOLUME=fixture.SERVER,fixture.PORT,fixture.VOLUME


class CleanupHandler(fixture.NativeHandler):
    def do_GET(self):
        self.server.contacts.append(('GET',self.path))
        role={'/v1/platform/creds/project-reader':'project-reader','/v1/platform/creds/cleanup':'cleanup'}.get(self.path)
        if role:
            self.respond(200,{'data':None,'auth':None,'wrap_info':{'token':'wrap-'+role,'ttl':90,
                'creation_path':'platform/creds/'+role}})
            return
        if self.path in self.server.rows:
            self.respond(200,self.server.rows[self.path],version=self.headers.get('OpenStack-API-Version'))
            if self.server.revoke_after==self.path: self.server.revoked=True
            return
        if self.server.generic_absence:
            self.respond(404,{'error':'unmatched-route'},version=self.headers.get('OpenStack-API-Version'))
        elif self.path.startswith('/v2.0/ports/'):
            self.respond(404,{'NeutronError':{'type':'PortNotFound','message':'Native port absent'}},
                         version=self.headers.get('OpenStack-API-Version'))
        else:
            self.respond(404,{'itemNotFound':{'code':404,'message':'Native object absent'}},
                         version=self.headers.get('OpenStack-API-Version'))

    def do_POST(self):
        self.server.contacts.append(('POST',self.path))
        raw=self.rfile.read(int(self.headers.get('Content-Length',0)))
        if self.path=='/v1/sys/wrapping/unwrap':
            role='cleanup' if self.headers['X-Vault-Token']=='wrap-cleanup' else 'project-reader'
            self.respond(200,{'lease_id':'local-'+role+'-lease','lease_duration':60,
                'data':self.server.writer_credentials if role=='cleanup' else self.server.credentials,
                'auth':None,'wrap_info':None})
        elif self.path=='/v3/auth/tokens':
            document=c.strict_loads(raw)
            cleanup=document['auth']['identity']['application_credential']['id']=='local-cleanup-app'
            token=deepcopy(self.server.token)
            if cleanup:
                token['roles']=[{'name':self.server.writer_role}]
                token['application_credential']={'id':'local-cleanup-app'}
            self.respond(201,{'token':token},token=True)
        else:self.respond(404,{})

    def do_DELETE(self):
        self.server.contacts.append(('DELETE',self.path))
        self.server.delete_count+=1
        self.server.rows.pop(self.path,None)
        self.send_response(204); self.send_header('Content-Length','0')
        version=self.headers.get('OpenStack-API-Version')
        if version:self.send_header('OpenStack-API-Version',version)
        self.send_header('X-Openstack-Request-Id',REQUEST_ID); self.end_headers()


class OpenStackCleanupTests(unittest.TestCase):
    def setUp(self):
        fixture.EnrolledOpenStackReadbackTests.setUp(self)
        self.server.RequestHandlerClass=CleanupHandler
        self.server.generic_absence=False; self.server.delete_count=0; self.server.writer_role='hosting_cleanup'
        previous=self.bundle.pools[0]; self.scope=replace(self.scope,native_scope_id=PROJECT)
        catalog=previous.catalog|{'native_id':PROJECT}
        pool=PoolDemand.from_workload(scope=self.scope,catalog=catalog,inputs=self.inputs,envelope_sha256='e'*64,
            budgets={key:dict(vcpu=0,memory_mb=0,storage_gb=0) for key in ('staging','snapshots','retained-source')},
            capabilities=previous.capabilities)
        self.bundle=ResourceBundle(self.admitted,'d'*64,'workload-01',1,(pool,))
        self.grant=replace(self.grant,source=self.scope,destination=self.scope,operation_scope=self.scope)
        self.enrollment.command.grant=self.grant
        self.issuer._roles={key:replace(role,scope=self.scope) for key,role in self.issuer._roles.items()}
        self.server.token=c.strict_loads(encoded(self.server.token).decode().replace('project-01',PROJECT))
        self.server.rows={path.replace('project-01',PROJECT):c.strict_loads(encoded(row).decode().replace('project-01',PROJECT))
                          for path,row in self.server.rows.items()}
        self.endpoints=OpenStackServiceEndpoints(self.scope.endpoint_id,PROJECT,
            self.origin+'/v2.1/'+PROJECT,self.origin+'/v3/'+PROJECT,self.origin+'/v2.0',self.origin+'/v2')
        metadata={'tenant_key':'tenant-01','domain_key':self.member['domain_key'],'workload_key':'processor-01'}
        self.descriptor={'member':self.member,'metadata':metadata,'ids':self.outputs['members']['value']['processor-01'],
                         'pool_flavor':catalog['flavors'][self.member['flavor_id']]}
        self.binding=NativeBinding('openstack',self.scope.endpoint_id,PROJECT,'vm',SERVER)
        self.child=OriginalOpenStackChild(self.binding,'old-create','a'*64,'processor-01',encoded(self.descriptor).decode())
        self.reader=OpenStackCleanupReadbackOwner(enrollment=self.enrollment,bundle=self.bundle,
            identity_endpoint=self.origin+'/v3',ca_bundle=self.ca,endpoints=self.endpoints,
            directory=self.root,creation_owner=self.owner)
        at=utcnow()-timedelta(seconds=2)
        self.action={'instanceAction':{'action':'delete','instance_uuid':SERVER,'project_id':PROJECT,
            'request_id':REQUEST_ID,'message':None,'events':[{'event':'compute_delete_instance',
                'result':'Success','start_time':at.isoformat(),'finish_time':(at+timedelta(seconds=1)).isoformat()}]}}
        self.server.rows[self.action_path]=self.action
        self.server.rows['/v3/'+PROJECT+'/types']={'volume_types':[{'id':'local-type','name':self.member['volume_type']}]}
        for collection in ('snapshots','backups'):
            self.server.rows['/v3/'+PROJECT+'/'+collection+'/detail?limit=1000']={collection:[]}
        self.receipt={'http_status':204,'request_id':REQUEST_ID}

    @property
    def server_path(self):return '/v2.1/'+PROJECT+'/servers/'+SERVER

    @property
    def action_path(self):return self.server_path+'/os-instance-actions/'+REQUEST_ID

    def test_missing_lookup_is_insufficient_without_actual_successful_hard_delete(self):
        del self.server.rows[self.server_path]
        with self.assertRaisesRegex(ValueError,'response custody'):self.reader.state(self.child)
        state=self.reader.state(self.child,receipt=self.receipt)
        self.assertEqual(state['status'],'ABSENT')
        self.assertEqual(state['hard_delete_action_digest'],c.digest(self.action['instanceAction']))
        self.assertGreater(self.checks,10)
        for event in ({'event':'compute_soft_delete_instance'}, {'result':'Error'}, {'finish_time':None}):
            original=deepcopy(self.action); self.action['instanceAction']['events'][0].update(event)
            self.server.rows[self.action_path]=self.action
            with self.subTest(event=event),self.assertRaises(ValueError):self.reader.state(self.child,receipt=self.receipt)
            self.action=original; self.server.rows[self.action_path]=original

    def test_unknown_route_protocol_and_current_read_revocation_are_not_absence(self):
        del self.server.rows[self.server_path]; self.server.generic_absence=True
        with self.assertRaisesRegex(ValueError,'generic missing'):self.reader.state(self.child,receipt=self.receipt)
        self.server.generic_absence=False; self.server.bad_version=True
        with self.assertRaisesRegex(ValueError,'protocol'):self.reader.state(self.child,receipt=self.receipt)
        self.server.bad_version=False; self.server.revoke_after='/v2.1/'+PROJECT+'/flavors/'+self.member['flavor_id']
        with self.assertRaises(GrantDenied):self.reader.state(self.child,receipt=self.receipt)
        self.assertEqual(self.server.delete_count,0)

    def test_fixed_routes_and_foreign_or_changed_native_children_are_rejected(self):
        reader=_CleanupReader(self.reader,self.child)
        with self.assertRaisesRegex(ValueError,'compiled'):reader.native('compute','servers/'+SERVER+'/action')
        for field,value in (('tenant_id','foreign-project'),('metadata',{}),
                ('os-extended-volumes:volumes_attached',[{'id':VOLUME},{'id':'foreign-volume'}])):
            original=deepcopy(self.server.rows[self.server_path]); self.server.rows[self.server_path]['server'][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):self.reader.state(self.child)
            self.server.rows[self.server_path]=original

    def test_original_storage_requires_detachment_and_complete_native_dependency_absence(self):
        child=replace(self.child,binding=replace(self.binding,resource_kind='volume',native_id=VOLUME))
        path='/v3/'+PROJECT+'/volumes/'+VOLUME
        with self.assertRaisesRegex(ValueError,'attached'):self.reader.state(child)
        self.server.rows[path]['volume'].update(status='available',attachments=[])
        self.assertEqual(self.reader.state(child)['status'],'PRESENT')
        for document in ({'snapshots':[{'id':'remaining-snapshot','volume_id':VOLUME}]},
                {'snapshots':[],'snapshots_links':[{'rel':'next','href':'https://foreign.invalid'}]}):
            self.server.rows['/v3/'+PROJECT+'/snapshots/detail?limit=1000']=document
            with self.subTest(document=document),self.assertRaises(ValueError):self.reader.state(child)

    def writer(self):
        grant=replace(self.grant,operation_kind='NATIVE_CLEANUP',worker_subject='new-cleanup-worker',
            operation_id='new-delete',step_id='cleanup-vm')
        issuer=VaultDynamicCredentialIssuer(vault_url=self.origin,ca_bundle=self.ca,
            agent_token_file=self.root/'agent-token',roles=(VaultDynamicRole('vault:cleanup','platform/creds/cleanup',
                self.scope,'NATIVE_CLEANUP',timedelta(minutes=2)),))
        cloud=deepcopy(self.server.credentials['cloud'])
        cloud['clouds'][self.inputs['openstack_cloud']]['auth']['application_credential_id']='local-cleanup-app'
        request={'format':'local-test-original-delete/1','operation_id':'new-delete','binding':asdict(self.binding)}
        self.server.writer_credentials={'format':'hosting-openstack-native-cleanup-credential/1',
            'request_digest':c.digest(request),'cloud':cloud}
        runtime=object.__new__(EnrolledOpenStackCleanupRuntime)
        runtime.scope=self.scope; runtime.bundle=self.bundle; runtime.identity_endpoint=self.origin+'/v3'
        runtime.ca_bundle=self.ca; runtime.endpoints=self.endpoints; runtime.cleanup_role_names=('hosting_cleanup',)
        runtime.directory=self.root; runtime.consumer=VaultCredentialConsumer(issuer)
        runtime.command_runtime=SimpleNamespace(grant=grant,context=SimpleNamespace(organization_id='org-01',tenant_id='tenant-01'),
            identity=SimpleNamespace(subject=grant.worker_subject),transport_evidence=object(),grant_arguments=lambda *_:{})
        runtime.broker=SimpleNamespace(acquire=lambda *_,**__:issuer.issue('vault:cleanup',grant=grant,expires_at=grant.expires_at))
        guard=OpenStackCleanupGuard(runtime,self.admitted,{},request)
        self.current=patch.object(OpenStackCleanupGuard,'require_current',return_value=(grant,grant.expires_at))
        self.current.start(); self.addCleanup(self.current.stop)
        return runtime,guard,grant,request

    def test_real_scoped_single_delete_never_creates_native_task_from_http_reference(self):
        runtime,guard,grant,request=self.writer()
        native=_CleanupWriter(runtime,guard,self.child)
        receipt=native.delete()
        self.assertEqual(receipt,self.receipt)
        state=self.reader.state(self.child,receipt=receipt)
        self.assertEqual(state['status'],'ABSENT')
        operation=NativeOperation('new-delete',self.admitted.job_id,'new-grant','cleanup-vm','cleanup-lease',
            self.binding,'workload-01','wsd-01','new-cleanup-worker',2,'NATIVE_CLEANUP',c.digest(request),
            'IN_FLIGHT',None,None)
        observation=self.reader.observe_cleanup(runtime.command_runtime.context,operation,request,self.child,receipt)
        self.assertIsNone(observation.native_task_id)
        retained=load_private(self.root/(observation.evidence_digest+'.json'))
        self.assertEqual(retained['http_receipt']['request_id'],REQUEST_ID)
        self.assertNotIn('local-only-secret',str(retained))
        self.assertEqual(self.server.delete_count,1)

    def test_actual_wrong_native_write_role_stops_before_delete(self):
        runtime,guard,grant,request=self.writer(); self.server.writer_role='admin'
        with self.assertRaisesRegex(ValueError,'restricted project role'):_CleanupWriter(runtime,guard,self.child)
        self.assertEqual(self.server.delete_count,0)

    def test_lost_original_acknowledgement_never_repeats_the_claimed_delete(self):
        runtime,guard,grant,request=self.writer()
        operation=NativeOperation('new-delete',self.admitted.job_id,'new-grant','cleanup-vm','cleanup-lease',
            self.binding,'workload-01','wsd-01','new-cleanup-worker',2,'NATIVE_CLEANUP',c.digest(request),
            'PREPARED',None,None)
        state={'operation':operation,'claims':0}
        def claim(*_):
            state['claims']+=1; state['operation']=replace(operation,state='IN_FLIGHT');return True
        runtime.registry=SimpleNamespace(prepare=lambda *_,**__:state['operation'],claim_once=claim,
            get=lambda *_:state['operation'],acknowledge_current=lambda *_:(_ for _ in ()).throw(RuntimeError('lost PG ack')),
            mark_uncertain=lambda *_:state.update(operation=replace(operation,state='UNCERTAIN')))
        runtime.readback=self.reader;runtime.lease=object()
        with patch.object(EnrolledOpenStackCleanupRuntime,'request',return_value=(request,self.child)):
            with self.assertRaisesRegex(RuntimeError,'lost PG ack'):runtime.cleanup(self.admitted,{})
            with self.assertRaisesRegex(ValueError,'already claimed'):runtime.cleanup(self.admitted,{})
        self.assertEqual((self.server.delete_count,state['claims']),(1,1))
