"""Actual TLS/JSON state project creation, scope and interruption boundaries."""
from copy import deepcopy
from datetime import timedelta
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
from pathlib import Path
import ssl
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError,URLError

from lab.native_readback_fixture import credentials
from provisioner.execution import readback_core as c
from provisioner.execution import state_project as d
from provisioner.execution import execution_journal as j
from provisioner.execution.run_files import digest,encoded,utcnow,load_private
from provisioner.execution.service_http import JsonService


class StateProjectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(); cls.base=Path(cls.temp.name); credentials(cls.base)
        (cls.base/'ca.pem').chmod(0o600)
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def reply(self,value,status=200):
                body=encoded(value); self.send_response(status); self.send_header('Content-Type','application/json')
                self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
            def do_GET(self):
                cls.calls.append((self.command,self.path,self.headers.get('Authorization')))
                if cls.redirect:
                    self.send_response(302); self.send_header('Location','https://never-contacted.invalid/'); self.end_headers(); return
                if self.path=='/api/v4/version': return self.reply({'version':cls.version})
                if self.path=='/api/v4/user': return self.reply(cls.actor)
                if self.path=='/api/v4/groups/10?with_projects=false': return self.reply(cls.group)
                if '/members/all?' in self.path:
                    rows=cls.group_members if '/groups/' in self.path else cls.project_members
                    if cls.repeating_pages: rows=[{'id':i,'access_level':30,'state':'active','expires_at':None} for i in range(1,101)]
                    return self.reply(rows)
                if self.path in {'/api/v4/projects/state%2Ftenant-a','/api/v4/projects/20'}:
                    return self.reply(cls.project or {},200 if cls.project else 404)
                return self.reply({},404)
            def do_POST(self):
                cls.calls.append((self.command,self.path,self.headers.get('Authorization')))
                payload=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                if self.path!='/api/v4/projects' or cls.project is not None: return self.reply({},400)
                cls.payload=payload
                cls.project=payload|dict(id=20,namespace=dict(id=10,kind='group',full_path='state'),creator_id=1,
                    path_with_namespace='state/tenant-a',archived=False,marked_for_deletion_on=None,
                    shared_with_groups=[],forked_from_project=None,import_status='none')
                if cls.mutate_after_create: cls.project.update(cls.mutate_after_create)
                return self.reply(cls.project,201)
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); context.load_cert_chain(cls.base/'server.pem',cls.base/'server.key')
        cls.server.socket=context.wrap_socket(cls.server.socket,server_side=True)
        cls.thread=threading.Thread(target=cls.server.serve_forever,kwargs={'poll_interval':.02},daemon=True); cls.thread.start()
        cls.origin=f'https://127.0.0.1:{cls.server.server_port}'
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join(); cls.temp.cleanup()
    def setUp(self):
        cls=type(self); cls.project=None; cls.calls=[]; cls.payload=None; cls.redirect=False; cls.repeating_pages=False
        cls.version='18.10.4-ee'; cls.actor=dict(id=1,state='active'); cls.mutate_after_create=None
        cls.group=dict(id=10,full_path='state',visibility='private',shared_with_groups=[])
        cls.group_members=[dict(id=1,access_level=50,state='active',expires_at=None),dict(id=2,access_level=40,state='active',expires_at=None)]
        cls.project_members=deepcopy(cls.group_members)
        temporary=tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup); self.ledger=Path(temporary.name)
        scope=dict(environment_key='lab',site_key='site-01',platform='openstack',tenant_key='tenant-a',wsd_key='wsd-a')
        self.request=dict(format='hosting-state-project/1',enabled=True,source_commit='a'*40,operation_id='state-create-1',
            origin=self.origin,gitlab_version=cls.version,namespace_id=10,namespace_path='state',path='tenant-a',actor_id=1,
            members=[dict(id=1,access_level=50),dict(id=2,access_level=40)],
            scopes=[scope|{'phase':'domains'},scope|{'phase':'workloads'}],service_acceptance_ref='TEST-SERVICE',recovery_ref='TEST-RECOVERY')
        self.token=b'fixture-token'; self.ca=self.base/'ca.pem'; self.client=JsonService(self.origin,'Bearer fixture-token',self.ca)
        check=patch.object(d,'verify',return_value={'status':'HASHES_MATCH','commit':'a'*40}); check.start(); self.addCleanup(check.stop)
    def authority(self,action):
        return dict(format='hosting-state-project-authority/1',request_sha256=c.digest(self.request),action=action,
            valid_from=(utcnow()-timedelta(minutes=1)).isoformat(),valid_until=(utcnow()+timedelta(minutes=5)).isoformat(),
            change_ref='TEST-CHANGE',token_sha256=digest(self.token),ca_sha256=digest(self.ca.read_bytes()))
    def run_action(self,action='create',**kwargs):
        return d.operate(self.request,self.authority(action),self.token,self.ledger,action=action,ca_file=self.ca,client=self.client,**kwargs)
    def posts(self): return sum(method=='POST' for method,_,_ in type(self).calls)

    def test_create_then_observe_publishes_exact_backends_without_state_writes(self):
        result=self.run_action(); self.assertEqual(result['project']['id'],20); self.assertEqual(self.posts(),1)
        self.assertEqual(type(self).payload,d.payload(self.request)); self.assertFalse(result['state_written'])
        self.assertEqual(len(result['backends']),2)
        for key,backend in result['backends'].items():
            self.assertIn('/api/v4/projects/20/terraform/state/wsd-',backend['address']); self.assertEqual(key,backend['state_key'])
        self.assertEqual(self.run_action('observe')['project'],result['project']); self.assertEqual(self.posts(),1)
        self.assertTrue(all(auth=='Bearer fixture-token' for _,_,auth in self.calls))
        self.assertFalse(any('/terraform/state/' in path for _,path,_ in self.calls))
        self.assertEqual(len(list(self.ledger.glob('*/*.receipt'))),2)
        with self.assertRaisesRegex(ValueError,'read-only observation'): self.run_action()
        self.assertEqual(self.posts(),1)

    def test_lost_response_recovers_by_exact_path_without_another_post(self):
        original=self.client.request
        def lost(method,*args,**kw):
            result=original(method,*args,**kw)
            if method=='POST': raise TimeoutError('Synthetic lost creation reply')
            return result
        with patch.object(self.client,'request',side_effect=lost),self.assertRaises(TimeoutError): self.run_action()
        result=self.run_action('observe'); self.assertEqual(result['project']['id'],20); self.assertEqual(self.posts(),1)
        kinds=[load_private(p)['kind'] for p in sorted(self.ledger.glob('*/*.json'))]
        self.assertEqual(kinds,['CREATE_STARTED','PROJECT_IDENTIFIED','PROJECT_OBSERVED'])

    def test_absent_unknown_creation_and_renamed_operation_stay_held(self):
        original=self.client.request
        def lost(method,*args,**kw):
            if method=='POST': raise TimeoutError('Uncertain send')
            return original(method,*args,**kw)
        with patch.object(self.client,'request',side_effect=lost),self.assertRaises(TimeoutError): self.run_action()
        with self.assertRaisesRegex(ValueError,'remains absent'): self.run_action('observe')
        with self.assertRaisesRegex(ValueError,'read-only observation'): self.run_action()
        self.request['operation_id']='renamed'
        with self.assertRaisesRegex(ValueError,'identity changed'): self.run_action()
        self.assertEqual(self.posts(),0)

    def test_observation_without_intent_cannot_create_or_adopt(self):
        with self.assertRaisesRegex(ValueError,'cannot start'): self.run_action('observe')
        self.assertEqual(self.calls,[]); self.assertEqual(self.posts(),0)

    def test_preexisting_project_is_not_adopted_even_with_matching_fields(self):
        self.run_action(); other=tempfile.TemporaryDirectory(); self.addCleanup(other.cleanup); self.ledger=Path(other.name)
        with self.assertRaisesRegex(ValueError,'separate accepted adoption'): self.run_action()
        self.assertEqual(self.posts(),1); self.assertFalse(list(self.ledger.glob('*/*.json')))

    def test_wrong_namespace_actor_version_or_membership_prevents_post(self):
        cls=type(self)
        for field,change in [('group',{'id':99}),('group',{'visibility':'public'}),('actor',{'id':3}),('actor',{'is_admin':True})]:
            original=deepcopy(getattr(cls,field)); getattr(cls,field).update(change)
            with self.subTest(field=field,change=change),self.assertRaises(ValueError): self.run_action()
            setattr(cls,field,original)
        cls.version='18.10.5-ee'
        with self.assertRaisesRegex(ValueError,'version changed'): self.run_action()
        cls.version=self.request['gitlab_version']; cls.group_members.append(dict(id=3,access_level=30,state='active',expires_at=None))
        with self.assertRaisesRegex(ValueError,'membership differs'): self.run_action()
        self.assertEqual(self.posts(),0)

    def test_exposed_created_project_is_retained_held_without_cleanup(self):
        cls=type(self); cls.mutate_after_create={'visibility':'public'}
        with self.assertRaisesRegex(ValueError,'restrictions differ'): self.run_action()
        self.assertEqual(self.posts(),1); self.assertIsNotNone(cls.project)
        cls.project['visibility']='private'; self.assertEqual(self.run_action('observe')['project']['id'],20)
        cls.project['id']=21
        with self.assertRaisesRegex(ValueError,'native identity changed'): self.run_action('observe')
        self.assertEqual(self.posts(),1)

    def test_project_membership_sharing_or_marker_drift_cannot_be_hidden_by_old_receipt(self):
        self.run_action(); cls=type(self); original=deepcopy(cls.project)
        for changes in ({'description':'FOREIGN'},{'shared_with_groups':[{'group_id':22}]},{'group_runners_enabled':True},
                        {'archived':True},{'infrastructure_access_level':'enabled'}):
            cls.project=original|changes
            with self.subTest(changes=changes),self.assertRaises(ValueError): self.run_action('observe')
        cls.project=original; cls.project_members[1]['access_level']=50
        with self.assertRaisesRegex(ValueError,'membership differs'): self.run_action('observe')
        self.assertEqual(self.posts(),1)

    def test_membership_pagination_truncation_duplicate_and_expiring_roles_hold(self):
        cls=type(self); cls.repeating_pages=True
        with self.assertRaisesRegex(ValueError,'Duplicate'): self.run_action()
        cls.repeating_pages=False; cls.group_members[0]['expires_at']='2099-01-01'
        with self.assertRaisesRegex(ValueError,'Expiring'): self.run_action()
        cls.group_members[0]['expires_at']=None; cls.group_members[0]['member_role_id']=42
        with self.assertRaisesRegex(ValueError,'custom-role'): self.run_action()
        self.assertEqual(self.posts(),0)

    def test_credential_expiry_source_or_request_mismatch_prevents_contact(self):
        for changes in ({'token_sha256':'b'*64},{'ca_sha256':'c'*64},{'request_sha256':'d'*64},
                        {'valid_until':(utcnow()-timedelta(seconds=1)).isoformat()}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                d.operate(self.request,self.authority('create')|changes,self.token,self.ledger,action='create',ca_file=self.ca,client=self.client)
        with patch.object(d,'verify',return_value={'status':'FAILED_INTEGRITY_CHECK','commit':'a'*40}),self.assertRaises(ValueError):
            self.run_action()
        self.assertEqual(self.calls,[])

    def test_invalid_scope_duplicate_member_and_unsupported_profile_are_rejected(self):
        original=deepcopy(self.request)
        for changes in ({'scopes':original['scopes']+[original['scopes'][0]]},{'members':original['members']*2},
                        {'namespace_path':'../escape'},{'gitlab_version':'17.4.1'},{'enabled':'true'}):
            with self.subTest(changes=list(changes)),self.assertRaises(ValueError): d.validate(original|changes)
        wrong=deepcopy(original); wrong['scopes'][1]['tenant_key']='tenant-b'
        with self.assertRaisesRegex(ValueError,'credential boundaries'): d.validate(wrong)

    def test_redirect_and_untrusted_tls_do_not_reach_project_creation(self):
        type(self).redirect=True
        with self.assertRaisesRegex(ValueError,'Redirect refused'): self.run_action()
        self.assertEqual(self.posts(),0); type(self).redirect=False
        self.client=JsonService(self.origin,'Bearer fixture-token')
        with self.assertRaises(URLError): self.run_action()
        self.assertEqual(self.posts(),0)

    def test_writer_lock_and_failed_intent_write_prevent_mutation(self):
        scope={'owner':'gitlab-state-project','origin':self.origin,'namespace_path':'state','path':'tenant-a'}
        with j.locked(self.ledger,scope),self.assertRaises(BlockingIOError): self.run_action()
        with patch.object(j.Journal,'append',side_effect=OSError('Synthetic journal failure')),self.assertRaises(OSError): self.run_action()
        self.assertEqual(self.posts(),0)
