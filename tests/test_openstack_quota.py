"""Real TLS quota writes with strict identity, usage and interrupted recovery."""
from copy import deepcopy
from datetime import timedelta
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import fcntl
import json
import os
from pathlib import Path
import ssl
import tempfile
import threading
import unittest
from unittest.mock import patch

from lab.native_readback_fixture import credentials
from tools import openstack_quota as d,readback_core as c
from tools.run_files import digest,encoded,load_private,utcnow

PROJECT='1'*32
CALLER='2'*32
USER='3'*32
ROLE='4'*32


class QuotaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(); cls.base=Path(cls.temp.name); credentials(cls.base)
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def reply(self,value):
                raw=encoded(value); self.send_response(302 if cls.redirect else 200)
                self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(raw)))
                version=self.headers.get('OpenStack-API-Version')
                if version: self.send_header('OpenStack-API-Version','wrong 1.0' if cls.wrong_version else version)
                if cls.redirect: self.send_header('Location','https://never-contacted.invalid/')
                self.end_headers(); self.wfile.write(raw)
            def remember(self):
                cls.calls.append((self.command,self.path,dict(self.headers)))
            def do_GET(self):
                self.remember(); r=cls.request; prefix=d.endpoint(r['endpoint']).path
                if self.path=='/identity/v3/auth/tokens': return self.reply({'token':cls.identity})
                if self.path=='/identity/v3/projects/'+PROJECT: return self.reply({'project':cls.project})
                if self.path==prefix+d.quota_path(r,True):
                    cls.reads+=1
                    if cls.drift_at==cls.reads: cls.quotas[next(iter(r['before']))]['limit']+=1
                    return self.reply({d.PROFILES[r['service']][1]:cls.quotas})
                self.send_error(404)
            def do_PUT(self):
                self.remember(); r=cls.request; expected=d.endpoint(r['endpoint']).path+d.quota_path(r)
                if self.path!=expected: self.send_error(404); return
                cls.payload=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                envelope=d.PROFILES[r['service']][1]
                for name,value in cls.payload[envelope].items(): cls.quotas[name]['limit']=value
                return self.reply({envelope:{name:row['limit'] for name,row in cls.quotas.items() if name!='id'}})
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); context.load_cert_chain(cls.base/'server.pem',cls.base/'server.key')
        cls.server.socket=context.wrap_socket(cls.server.socket,server_side=True)
        cls.thread=threading.Thread(target=cls.server.serve_forever,kwargs={'poll_interval':.02},daemon=True); cls.thread.start()
        cls.origin=f'https://127.0.0.1:{cls.server.server_port}'
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join(); cls.temp.cleanup()
    def setUp(self):
        temporary=tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup); self.ledger=Path(temporary.name)
        self.token=b'fixture-quota-token'; self.ca=(self.base/'ca.pem').read_bytes()
        self.request=dict(format='hosting-openstack-quota/1',enabled=True,source_commit='a'*40,operation_id='quota-01',generation=1,
            scope=dict(environment_key='lab',site_key='site-01',platform='openstack',tenant_key='tenant-a'),service='compute',
            identity_endpoint=self.origin+'/identity/v3',endpoint=self.origin+'/compute/v2.1/'+CALLER,
            project=dict(id=PROJECT,domain_id='default',parent_id='default',name='tenant-a'),
            caller=dict(user_id=USER,user_domain_id='default',project_id=CALLER,project_domain_id='default',
                role_ids=[ROLE],region='RegionOne',interface='internal'),
            before={'cores':4,'instances':2},after={'cores':8,'instances':4},
            entitlement_ref='TEST-ACCEPTED-ALLOCATION',enforcement_ref='TEST-LEGACY-QUOTA-DRIVER')
        self.configure()
        check=patch.object(d,'verify',return_value={'status':'HASHES_MATCH','commit':'a'*40})
        check.start(); self.addCleanup(check.stop)
    def configure(self):
        cls=type(self); cls.calls=[]; cls.reads=0; cls.payload=None; cls.redirect=False; cls.wrong_version=False; cls.drift_at=None
        cls.request=self.request; used=d.PROFILES[self.request['service']][2]
        cls.quotas={name:{'limit':value,used:0,'reserved':0} for name,value in self.request['before'].items()}
        cls.quotas['unowned']={'limit':999,used:0,'reserved':0}
        if self.request['service']!='network': cls.quotas['id']=PROJECT
        cls.project=self.request['project']|{'enabled':True,'is_domain':False}
        cls.identity=dict(user={'id':USER,'domain':{'id':'default'}},project={'id':CALLER,'domain':{'id':'default'}},
            roles=[{'id':ROLE,'name':'accepted-quota-owner'}],issued_at=(utcnow()-timedelta(minutes=1)).isoformat(),
            expires_at=(utcnow()+timedelta(minutes=10)).isoformat(),
            catalog=[{'type':{'compute':'compute','volume':'volumev3','network':'network'}[self.request['service']],
                'endpoints':[{'interface':'internal','region_id':'RegionOne','url':self.request['endpoint']}]}])
    def authority(self,action='apply'):
        return dict(format='hosting-openstack-quota-authority/1',request_sha256=c.digest(self.request),action=action,
            token_sha256=digest(self.token),ca_sha256=digest(self.ca),valid_from=(utcnow()-timedelta(minutes=1)).isoformat(),
            valid_until=(utcnow()+timedelta(minutes=5)).isoformat(),change_ref='TEST-CHANGE',writer_exclusion_ref='TEST-INDEPENDENT-FENCE')
    def run_action(self,action='apply',client=None):
        return d.operate(self.request,self.authority(action),self.token,self.ca,self.ledger,client=client)
    def puts(self): return sum(method=='PUT' for method,_,_ in type(self).calls)
    def client(self,action='apply'): return d.Client(self.request,self.authority(action),self.token,self.ca)

    def test_all_three_native_profiles_write_exact_fields_and_recover_without_repeat(self):
        for service,fields,path in [('compute',{'cores':4,'instances':2},'/compute/v2.1/'+CALLER),
            ('volume',{'volumes':2,'gigabytes':20},'/volume/v3/'+CALLER),
            ('network',{'port':4,'floatingip':0},'/network/v2.0')]:
            with self.subTest(service=service):
                self.request.update(service=service,endpoint=self.origin+path,before=fields,after={k:v+2 for k,v in fields.items()})
                self.configure(); result=self.run_action(); repeated=self.run_action('observe')
                self.assertEqual(result['quotas'],repeated['quotas']); self.assertEqual(self.puts(),1)
                self.assertEqual(type(self).payload,{d.PROFILES[service][1]:self.request['after']})
                self.assertEqual(type(self).quotas['unowned']['limit'],999)
                self.assertFalse(result['native_fencing'] or result['capacity_reserved'] or result['production_activation'])
                self.assertTrue(all(headers.get('X-Auth-Token')=='fixture-quota-token' for _,_,headers in self.calls))
                auth_headers=next(headers for _,url,headers in self.calls if url.endswith('/auth/tokens'))
                self.assertEqual(auth_headers['X-Subject-Token'],'fixture-quota-token')

    def test_lost_put_reply_requires_observation_and_retains_one_native_write(self):
        client=self.client(); original=client.call
        def lost(operation):
            result=original(operation)
            if operation=='write': raise TimeoutError('Synthetic lost quota response')
            return result
        with patch.object(client,'call',side_effect=lost),self.assertRaises(TimeoutError): self.run_action(client=client)
        with self.assertRaisesRegex(ValueError,'read-only recovery'): self.run_action()
        result=self.run_action('observe'); self.assertEqual(result['quotas']['cores']['limit'],8); self.assertEqual(self.puts(),1)
        events=[load_private(path)['kind'] for path in sorted(self.ledger.glob('*/*.json'))]
        self.assertEqual(events,['QUOTA_CHANGE_STARTED','QUOTA_CHANGE_OBSERVED'])

    def test_unknown_unsent_put_and_new_generation_cannot_hide_pending_write(self):
        client=self.client(); original=client.call
        def lost(operation):
            if operation=='write': raise TimeoutError('Synthetic pre-send interruption')
            return original(operation)
        with patch.object(client,'call',side_effect=lost),self.assertRaises(TimeoutError): self.run_action(client=client)
        with self.assertRaisesRegex(ValueError,'limit or usage differs'): self.run_action('observe')
        self.request.update(operation_id='quota-02',generation=2)
        with self.assertRaisesRegex(ValueError,'pending native outcome'): self.run_action()
        self.assertEqual(self.puts(),0)

    def test_changed_administration_project_uses_same_native_quota_ledger(self):
        client=self.client(); original=client.call
        def lost(operation):
            if operation=='write': raise TimeoutError
            return original(operation)
        with patch.object(client,'call',side_effect=lost),self.assertRaises(TimeoutError): self.run_action(client=client)
        old=d.owner_scope(self.request)
        self.request['caller']['project_id']='5'*32; self.request['endpoint']=self.origin+'/compute/v2.1/'+'5'*32
        self.request.update(operation_id='renamed',generation=2)
        self.assertEqual(d.owner_scope(self.request),old)
        with self.assertRaisesRegex(ValueError,'pending native outcome'): self.run_action()
        self.assertEqual(self.puts(),0)

    def test_usage_and_reserved_charges_prevent_unsafe_shrink(self):
        self.request['after']={'cores':2,'instances':1}; type(self).quotas['cores'].update(in_use=2,reserved=1)
        with self.assertRaisesRegex(ValueError,'below allocated'): self.run_action()
        self.assertEqual(self.puts(),0); self.assertEqual(list(self.ledger.glob('*/*.json')),[])

    def test_wrong_project_domain_disabled_target_and_credential_scope_never_write(self):
        original=deepcopy(type(self).project)
        for values in ({'id':'5'*32},{'domain_id':'6'*32},{'enabled':False},{'is_domain':True}):
            with self.subTest(values=values):
                type(self).project=original|values
                with self.assertRaisesRegex(ValueError,'Target project'): self.run_action()
        type(self).project=original; type(self).identity['project']['id']='7'*32
        with self.assertRaisesRegex(ValueError,'credential scope'): self.run_action()
        self.assertEqual(self.puts(),0)

    def test_role_catalog_and_expired_token_hold(self):
        type(self).identity['roles']=[{'id':'8'*32}]
        with self.assertRaisesRegex(ValueError,'role identities'): self.run_action()
        self.configure(); type(self).identity['catalog'][0]['endpoints'][0]['url']='https://wrong.invalid/compute/v2.1/'+CALLER
        with self.assertRaisesRegex(ValueError,'catalog'): self.run_action()
        self.configure(); type(self).identity['expires_at']=(utcnow()-timedelta(seconds=1)).isoformat()
        with self.assertRaisesRegex(ValueError,'expired'): self.run_action()
        self.assertEqual(self.puts(),0)

    def test_preflight_drift_and_wrong_microversion_redirect_are_not_retried(self):
        type(self).drift_at=2
        with self.assertRaises(ValueError): self.run_action()
        self.assertEqual(self.puts(),0)
        self.configure(); type(self).wrong_version=True
        with self.assertRaisesRegex(ValueError,'microversion'): self.run_action()
        self.configure(); type(self).redirect=True
        with self.assertRaisesRegex(ValueError,'response rejected'): self.run_action()
        self.assertEqual(self.puts(),0); self.assertEqual(len(type(self).calls),1)

    def test_completed_generation_changed_native_state_and_superseded_request_hold(self):
        original=deepcopy(self.request); self.run_action()
        type(self).quotas['cores']['limit']=9
        with self.assertRaisesRegex(ValueError,'limit or usage differs'): self.run_action('observe')
        type(self).quotas['cores']['limit']=8
        self.request.update(operation_id='quota-02',generation=2,before=dict(self.request['after']),after={'cores':10,'instances':5})
        self.run_action(); self.assertEqual(self.puts(),2)
        self.request=original
        with self.assertRaisesRegex(ValueError,'superseded'): self.run_action('observe')

    def test_noop_generation_records_observation_without_mutation(self):
        self.request['after']=dict(self.request['before'])
        result=self.run_action(); self.assertEqual(self.puts(),0); self.assertEqual(result['quotas']['cores']['limit'],4)
        self.run_action('observe'); self.assertEqual(self.puts(),0)

    def test_competing_lock_and_failed_durable_intent_prevent_native_put(self):
        with d.journal.locked(self.ledger,d.owner_scope(self.request)):
            with self.assertRaises(BlockingIOError): self.run_action()
        with patch.object(d.journal.Journal,'append',side_effect=OSError),self.assertRaises(OSError): self.run_action()
        self.assertEqual(self.puts(),0)

    def test_failed_observation_publication_recovers_existing_write(self):
        original=d.journal.Journal.append
        def fail(log,kind,data):
            if kind=='QUOTA_CHANGE_OBSERVED': raise InterruptedError
            return original(log,kind,data)
        with patch.object(d.journal.Journal,'append',new=fail),self.assertRaises(InterruptedError): self.run_action()
        self.run_action('observe'); self.assertEqual(self.puts(),1)

    def test_bad_input_unlimited_target_and_credentials_fail_before_contact(self):
        for update in ({'after':{'cores':-1,'instances':4}},{'after':{'cores':True,'instances':4}},
            {'endpoint':'http://wrong.invalid/v2.1'},{'generation':True}):
            with self.subTest(update=update),self.assertRaises(ValueError): d.validate(self.request|update)
        authority=self.authority(); authority['token_sha256']='0'*64
        with self.assertRaises(ValueError): d.operate(self.request,authority,self.token,self.ca,self.ledger)
        authority=self.authority(); authority['valid_until']=(utcnow()-timedelta(seconds=1)).isoformat()
        with self.assertRaises(ValueError): d.operate(self.request,authority,self.token,self.ca,self.ledger)
        self.assertEqual(type(self).calls,[])


if __name__=='__main__': unittest.main()
