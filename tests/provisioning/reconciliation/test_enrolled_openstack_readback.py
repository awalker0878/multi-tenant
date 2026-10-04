"""Real loopback TLS Keystone/Nova/Cinder/Neutron protocol and identity checks.

Only B10 enrollment/persistence is a local fixture. The tests contact actual
HTTPS sockets and the actual one-use Vault consumer, but confer no site/native
qualification. Opt-in PostgreSQL owners cover authority persistence separately.
"""
from copy import deepcopy
from dataclasses import asdict,replace
from datetime import timedelta
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import ssl
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from provisioner.allocations.transactions import PoolDemand,ResourceBundle,ResourceUnits
from provisioner.controlplane.authority.model import PlanScope,WorkerGrant
from provisioner.controlplane.persistence import TenantContext
from provisioner.controlplane.reconciliation.adapters.openstack_readback import OpenStackNativeReadbackOwner
from provisioner.controlplane.reconciliation.planned import PlannedResourceLease,creation_request_digest,deployment_id
from provisioner.controlplane.reconciliation.read_enrollment import NativeReadEnrollment
from provisioner.controlplane.worker.grants import GrantDenied
from provisioner.controlplane.worker.vault import VaultDynamicRole,VaultDynamicCredentialIssuer
from provisioner.controlplane.worker.vault_consumer import VaultCredentialConsumer
from provisioner.controlplane.workflow.admitted_job import AdmittedInput
from provisioner.execution import readback_core as c
from provisioner.execution.run_files import encoded,load_private,utcnow,write_new
from tests.provisioning.worker.tls_fixtures import TestPki
from tests.test_capacity_demand import fixture

SERVER='10000000-0000-4000-8000-000000000001'
PORT='10000000-0000-4000-8000-000000000002'
VOLUME='10000000-0000-4000-8000-000000000003'


class NativeHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.server.contacts.append(('GET',self.path))
        if self.path=='/v1/platform/creds/project-reader':
            self.respond(200,{'data':None,'auth':None,'wrap_info':{'token':'single-use-local-wrap','ttl':90,
                'creation_path':'platform/creds/project-reader'}})
        elif self.path in self.server.rows:
            self.respond(200,self.server.rows[self.path],version=self.headers.get('OpenStack-API-Version'))
            if self.server.revoke_after==self.path: self.server.revoked=True
        else: self.respond(404,{'error':'not-found'})

    def do_POST(self):
        self.server.contacts.append(('POST',self.path))
        if self.path=='/v1/sys/wrapping/unwrap':
            self.respond(200,{'lease_id':'native-local-reader-lease','lease_duration':60,
                'data':self.server.credentials,'auth':None,'wrap_info':None})
        elif self.path=='/v3/auth/tokens': self.respond(201,{'token':self.server.token},token=True)
        else: self.respond(404,{})

    def respond(self,status,body,*,token=False,version=None):
        raw=encoded(body); self.send_response(status); self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(raw)))
        if token: self.send_header('X-Subject-Token','local-reader-token')
        if version and not self.server.bad_version: self.send_header('OpenStack-API-Version',version)
        self.end_headers(); self.wfile.write(raw)
    def log_message(self,*_): pass


class EnrolledOpenStackReadbackTests(unittest.TestCase):
    def setUp(self):
        self.pki=TestPki(); self.addCleanup(self.pki.close); self.pki.issue('server')
        self.server=ThreadingHTTPServer(('127.0.0.1',0),NativeHandler)
        tls=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls.load_cert_chain(str(self.pki.root/'server.pem'),str(self.pki.root/'server.key'))
        self.server.socket=tls.wrap_socket(self.server.socket,server_side=True)
        thread=threading.Thread(target=self.server.serve_forever,daemon=True); thread.start()
        self.addCleanup(self.server.server_close); self.addCleanup(self.server.shutdown)
        self.server.contacts=[]; self.server.bad_version=False; self.server.revoked=False; self.server.revoke_after=None
        self.origin=f'https://localhost:{self.server.server_port}'
        self.temporary=tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        self.root=Path(self.temporary.name); self.root.chmod(0o700)
        self.ca=self.root/'ca.pem'; write_new(self.ca,(self.pki.root/'ca.pem').read_bytes())
        self.scope=PlanScope('org-01','tenant-01','site-01','wsd-01','openstack-01','project-01','openstack')
        labels=dict(environment_key='lab',site_key='site-01',tenant_key='tenant-01',wsd_key='wsd-01',platform='openstack')
        inputs,catalog=fixture('openstack',labels); catalog.update(origin=self.origin,native_id='project-01')
        self.inputs=inputs; self.member=inputs['members']['processor-01']
        zero=dict(vcpu=0,memory_mb=0,storage_gb=0)
        pool=PoolDemand.from_workload(scope=self.scope,catalog=catalog,inputs=inputs,envelope_sha256='e'*64,
            budgets={key:zero for key in ('staging','snapshots','retained-source')},capabilities=('internal-ipv4',))
        self.admitted=AdmittedInput('job-01','org-01','tenant-01','plan-01',1,'b'*64,0,'c'*64)
        self.bundle=ResourceBundle(self.admitted,'d'*64,'workload-01',1,(pool,))
        at=utcnow()
        self.grant=WorkerGrant('read-grant','org-01','tenant-01','read-plan',1,'a'*64,self.scope,self.scope,
            'independent-reader','read-step','read-operation','DISCOVER_READ',self.scope,'read-lease',1,
            ('read-approval',),0,at,at+timedelta(minutes=2))
        agent=self.root/'agent-token'; write_new(agent,b'local-only-agent-token')
        self.issuer=VaultDynamicCredentialIssuer(vault_url=self.origin,ca_bundle=self.ca,
            agent_token_file=agent,roles=(VaultDynamicRole('vault:project-reader','platform/creds/project-reader',
                self.scope,'DISCOVER_READ',timedelta(minutes=2)),))
        self.consumer=VaultCredentialConsumer(self.issuer)
        cloud={'clouds':{inputs['openstack_cloud']:{'auth_type':'v3applicationcredential','verify':True,
            'region_name':'region-1','interface':'internal','auth':{'auth_url':self.origin+'/v3',
                'application_credential_id':'local-reader-app','application_credential_secret':'local-only-secret'}}}}
        self.server.credentials={'environment':{},'cloud':cloud}
        self.server.token={'project':{'id':'project-01'},'roles':[{'name':'reader'}],
            'methods':['application_credential'],'application_credential':{'id':'local-reader-app'},
            'expires_at':(at+timedelta(minutes=3)).isoformat(),'catalog':[
                {'type':name,'endpoints':[{'interface':'internal','region_id':'region-1','url':self.origin+path}]}
                for name,path in [('compute','/v2.1/project-01'),('volumev3','/v3/project-01'),('network','/v2.0')]]}
        # Deliberately synthetic B10 persistence only; no production constructor
        # accepts these fixtures. The concrete reader and native TLS are real.
        self.enrollment=object.__new__(NativeReadEnrollment)
        object.__setattr__(self.enrollment,'command',SimpleNamespace(grant=self.grant,identity=SimpleNamespace(subject='independent-reader')))
        self.checks=0
        def current(*_,**__):
            self.checks+=1
            if self.server.revoked: raise GrantDenied('Local-only current read grant revoked')
            return self.grant,self.grant.expires_at
        def acquire(_):
            current(); return self.consumer.unwrap(self.issuer.issue('vault:project-reader',grant=self.grant,
                expires_at=self.grant.expires_at),self.grant)
        self.addCleanup(patch.stopall)
        patch.object(NativeReadEnrollment,'require_current',current).start()
        patch.object(NativeReadEnrollment,'acquire',acquire).start()
        self.owner=OpenStackNativeReadbackOwner(enrollment=self.enrollment,identity_endpoint=self.origin+'/v3',
            ca_bundle=self.ca,directory=self.root,bundles=lambda *_:self.bundle)
        self.outputs={'members':{'value':{'processor-01':{'server_id':SERVER,'port_id':PORT,
            'boot_volume_id':VOLUME,'data_volume_ids':[]}}}}
        metadata={'tenant_key':'tenant-01','domain_key':self.member['domain_key'],'workload_key':'processor-01'}
        self.server.rows={
            '/v2.1/project-01/servers/'+SERVER:{'server':{'id':SERVER,'tenant_id':'project-01','name':'processor-01',
                'status':'SHUTOFF','metadata':metadata,'flavor':{'id':self.member['flavor_id']},
                'OS-EXT-AZ:availability_zone':self.member['compute_availability_zone'],'OS-EXT-STS:task_state':None,
                'os-extended-volumes:volumes_attached':[{'id':VOLUME}]}},
            '/v2.1/project-01/servers/'+SERVER+'/os-interface':{'interfaceAttachments':[{'port_id':PORT}]},
            '/v2.1/project-01/flavors/'+self.member['flavor_id']:{'flavor':{'id':self.member['flavor_id'],
                'vcpus':2,'ram':4096,'disk':0,'OS-FLV-EXT-DATA:ephemeral':0,'swap':''}},
            '/v2.0/ports/'+PORT:{'port':{'id':PORT,'project_id':'project-01','device_id':SERVER,
                'network_id':self.member['network_id'],'port_security_enabled':True,'allowed_address_pairs':[],
                'security_groups':[self.member['security_group_id']],
                'fixed_ips':[{'subnet_id':self.member['subnet_id'],'ip_address':self.member['ipv4_address']}],
                'admin_state_up':False}},
            '/v2.0/security-groups/'+self.member['security_group_id']:{'security_group':{
                'id':self.member['security_group_id'],'project_id':'project-01'}},
            '/v3/project-01/volumes/'+VOLUME:{'volume':{'id':VOLUME,'os-vol-tenant-attr:tenant_id':'project-01',
                'status':'in-use','size':40,'availability_zone':self.member['storage_availability_zone'],
                'volume_type':self.member['volume_type'],'metadata':metadata,
                'attachments':[{'server_id':SERVER}],'volume_image_metadata':{'image_id':self.member['image_id']}}}}

    def read(self): return self.owner._read(self.bundle,self.scope,self.outputs)

    def test_real_native_identity_complete_attachments_and_decimal_occupancy(self):
        bindings,facts,units=self.read()
        self.assertEqual({(item.resource_kind,item.native_id) for item in bindings},
            {('vm',SERVER),('nic',PORT),('volume',VOLUME)})
        self.assertEqual(units,ResourceUnits(2,4295,43))
        self.assertGreater(self.checks,10)
        self.assertEqual([method for method,path in self.server.contacts].count('POST'),2)
        self.assertNotIn('local-only-secret',str(facts))

    def test_wrong_project_or_write_role_stops_before_native_object_reads(self):
        for change in (lambda: self.server.token['project'].update(id='foreign-project'),
                       lambda: self.server.token.update(roles=[{'name':'member'}])):
            original=deepcopy(self.server.token); change(); self.server.contacts.clear()
            with self.subTest(),self.assertRaisesRegex(ValueError,'identity'): self.read()
            self.assertFalse(any('/servers/' in path for method,path in self.server.contacts))
            self.server.token=original

    def test_current_occupancy_preserves_original_ids_and_charge_after_separate_power_or_port_transition(self):
        original_bindings, _facts, original_units = self.read()
        server = self.server.rows['/v2.1/project-01/servers/' + SERVER]['server']
        port = self.server.rows['/v2.0/ports/' + PORT]['port']
        server['status'] = 'ACTIVE'
        for enabled in (False, True):
            port['admin_state_up'] = enabled
            bindings, facts, units = self.owner._read(self.bundle, self.scope, self.outputs, occupancy=True)
            self.assertEqual((bindings, units), (original_bindings, original_units))
            self.assertIs(facts['processor-01']['port']['admin_state_up'], enabled)
            with self.assertRaises(ValueError): self.read()
        server['status'] = 'BUILD'
        with self.assertRaises(ValueError): self.owner._read(self.bundle, self.scope, self.outputs, occupancy=True)
        server['status'] = 'ACTIVE'; port['admin_state_up'] = None
        with self.assertRaises(ValueError): self.owner._read(self.bundle, self.scope, self.outputs, occupancy=True)

    def test_changed_scope_flavor_policy_or_unknown_native_attachment_keeps_charge(self):
        cases=[('/v2.1/project-01/servers/'+SERVER,'server','tenant_id','foreign-project'),
            ('/v2.1/project-01/servers/'+SERVER,'server','os-extended-volumes:volumes_attached',[{'id':VOLUME},{'id':'foreign'}]),
            ('/v2.1/project-01/flavors/'+self.member['flavor_id'],'flavor','vcpus',3),
            ('/v2.0/ports/'+PORT,'port','port_security_enabled',False),
            ('/v3/project-01/volumes/'+VOLUME,'volume','size',41),
            ('/v3/project-01/volumes/'+VOLUME,'volume','os-vol-tenant-attr:tenant_id','foreign')]
        for path,key,field,value in cases:
            original=deepcopy(self.server.rows); self.server.rows[path][key][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError): self.read()
            self.server.rows=original

    def test_missing_native_identity_protocol_or_midread_revocation_is_not_absence(self):
        original=deepcopy(self.outputs)
        del self.outputs['members']['value']['processor-01']['port_id']
        with self.assertRaises(ValueError): self.read()
        self.outputs=original; self.server.bad_version=True
        with self.assertRaisesRegex(ValueError,'protocol'): self.read()
        self.server.bad_version=False; self.server.revoke_after='/v2.1/project-01/servers/'+SERVER
        with self.assertRaises(GrantDenied): self.read()

    def test_actual_private_creation_custody_is_written_without_invented_task_receipt(self):
        prepared=self.root/'prepared'; prepared.mkdir(mode=0o700)
        write_new(prepared/'inputs.json',encoded(self.inputs)); write_new(prepared/'outputs.json',encoded(self.outputs))
        resource=deployment_id(self.bundle,self.scope)
        lease=PlannedResourceLease('org-01','tenant-01','job-01',resource,'deployment','d'*64,
            creation_request_digest(self.bundle,self.scope,resource),'e'*64,self.scope,'workload-01','writer-01',1,
            utcnow()+timedelta(minutes=2))
        proof=self.owner.observe_creation(TenantContext('org-01','tenant-01'),lease,'creation-op',self.bundle,prepared)
        self.assertIsNone(proof.observation.native_task_id)
        stored=load_private(self.root/(proof.observation.evidence_digest+'.json'))
        self.assertEqual(stored['units'],asdict(ResourceUnits(2,4295,43)))
        self.assertEqual(stored['operation_id'],'creation-op')
