"""Real local unit/HTTPS integration tests; no cloud credentials or vendor endpoint."""
from __future__ import annotations
import copy
from datetime import datetime,timezone
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
import os
from pathlib import Path
import socket
import ssl
import struct
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch

from tools import neutron_observe as no
from tools.route_record_review import review,COMMON,FIELDS
from lab.run_namespace_lab import validate_fixture,rules_for,endpoint
from lab.worker import dns_question,dns_answer,validate_dns_answer,fixture_ip
from lab.link_config import attribute,set_forwarding

ROOT=Path(__file__).resolve().parents[1]
RID='35769012-aaaa-4bbb-8ccc-123456789012'
PROJECT='c04f2571cf1447c59409d2786fe61cab'


def network_manifest():
 return {'project_id':PROJECT,'engineering_record_ref':'ENG-2026-0042',
         'resources':[{'kind':'network','id':RID,'expected':{'admin_state_up':False,'shared':False,
          'router:external':False,'port_security_enabled':True}}]}


def network_actual():
 return dict(id=RID,project_id=PROJECT,revision_number=5,**network_manifest()['resources'][0]['expected'])


class FixtureTests(unittest.TestCase):
 def setUp(self):self.fixture=json.loads((ROOT/'examples/wd14-routing.json').read_text())
 def test_original_fixture_valid(self):validate_fixture(self.fixture)
 def test_external_address_rejected(self):
  self.fixture['nodes']['resolver']['interfaces'][0]['address']='8.8.8.8/24'
  with self.assertRaises(ValueError):validate_fixture(self.fixture)
 def test_unknown_node_rejected(self):
  self.fixture['nodes']['unknown']={}
  with self.assertRaises(ValueError):validate_fixture(self.fixture)
 def test_external_next_hop_rejected(self):
  self.fixture['nodes']['resolver']['routes'][0]['next_hop']='10.0.0.1'
  with self.assertRaises(ValueError):validate_fixture(self.fixture)
 def test_flow_protocol_not_guessed(self):
  self.fixture['approved_flows'][0]['protocol']='other'
  with self.assertRaises(ValueError):validate_fixture(self.fixture)
 def test_native_fixture_preserves_tcp443(self):
  rules=rules_for(self.fixture,'EC-01');self.assertIn('192.0.2.10 192.0.2.42 443',rules)
  self.assertNotIn(' 5432 ',rules);self.assertNotIn('192.0.2.74',rules)
 def test_service_rules_only_dns(self):
  rules=rules_for(self.fixture,'SE-01');self.assertNotIn(' 443 ',rules);self.assertIn(' 53 ',rules)
  self.assertNotIn('203.0.113.139',rules)
 def test_containment_bidirectional_before_allows(self):
  rules=rules_for(self.fixture,'EC-01',('processor-01','data-01'))
  self.assertLess(rules.index('block any'),rules.index('allow tcp'))
  self.assertIn('block any 192.0.2.42 192.0.2.10',rules)
 def test_endpoint_values_unchanged(self):self.assertEqual(endpoint(self.fixture,'processor-01'),'192.0.2.10')
 def test_worker_refuses_nonfixture_address(self):
  for address in ('127.0.0.1','10.0.0.1','::1'):
   with self.subTest(address=address),self.assertRaises(ValueError):fixture_ip(address)
 def test_forward_helper_refuses_original_namespace(self):
  with patch.dict(os.environ,{'HOSTING_LAB_ORIGINAL_NETNS':os.readlink('/proc/self/ns/net'),
                              'HOSTING_LAB_MASTER_NETNS':'net:[0]' }):
   with self.assertRaises(RuntimeError):set_forwarding(True)
 def test_netlink_attributes_aligned(self):
  data=attribute(1,b'abc',True);self.assertEqual(len(data)%4,0);self.assertEqual(struct.unpack('HH',data[:4]),(7,32769))
 def test_no_execute_is_inert(self):
  result=subprocess.run([os.sys.executable,str(ROOT/'lab/run_namespace_lab.py')],capture_output=True,text=True,timeout=5)
  self.assertNotEqual(result.returncode,0);self.assertIn('No changes made',result.stderr)
 def test_dns_small_udp(self):
  q=dns_question('small.fixture.invalid',42);self.assertTrue(validate_dns_answer(dns_answer(q,False),q))
 def test_dns_large_truncates_only_udp(self):
  q=dns_question('large.fixture.invalid',42);self.assertFalse(validate_dns_answer(dns_answer(q,False),q));self.assertTrue(validate_dns_answer(dns_answer(q,True),q))
 def test_dns_unknown_name_not_recursive(self):
  q=dns_question('unknown.fixture.invalid',42)
  with self.assertRaises(ValueError):validate_dns_answer(dns_answer(q,True),q)
 def test_dns_wrong_transaction_rejected(self):
  q=dns_question('small.fixture.invalid',42);a=dns_answer(q,True)
  with self.assertRaises(ValueError):validate_dns_answer(b'\0\x01'+a[2:],q)
 def test_dns_malformed_question_rejected(self):
  with self.assertRaises(ValueError):dns_answer(b'bad',False)


class ObservationTests(unittest.TestCase):
 def test_manifest_valid(self):no.validate_manifest(network_manifest())
 def test_manifest_empty_rejected(self):
  value=network_manifest();value['resources']=[]
  with self.assertRaises(ValueError):no.validate_manifest(value)
 def test_duplicate_selector_rejected(self):
  value=network_manifest();value['resources']*=2
  with self.assertRaises(ValueError):no.validate_manifest(value)
 def test_missing_security_expectation_rejected(self):
  value=network_manifest();del value['resources'][0]['expected']['router:external']
  with self.assertRaises(ValueError):no.validate_manifest(value)
 def test_credential_expectation_rejected(self):
  value=network_manifest();value['resources'][0]['expected']['password']='secret'
  with self.assertRaises(ValueError):no.validate_manifest(value)
 def test_path_injection_rejected(self):
  value=network_manifest();value['resources'][0]['id']='../../routers'
  with self.assertRaises(ValueError):no.validate_manifest(value)
 def test_exact_match_is_not_qualification(self):
  result=no.compare(network_manifest()['resources'][0],network_actual(),PROJECT)
  self.assertEqual(result['status'],'MATCH')
 def test_integer_does_not_satisfy_boolean(self):
  value=network_actual();value['admin_state_up']=0
  self.assertEqual(no.compare(network_manifest()['resources'][0],value,PROJECT)['status'],'DIFFERENT')
 def test_unknown_field_not_pass(self):
  value=network_actual();del value['port_security_enabled']
  self.assertEqual(no.compare(network_manifest()['resources'][0],value,PROJECT)['status'],'INCONCLUSIVE')
 def test_foreign_project_mismatch(self):
  self.assertEqual(no.compare(network_manifest()['resources'][0],network_actual(),'d'*32)['status'],'DIFFERENT')
 def test_conflicting_project_aliases(self):
  value=dict(network_actual(),tenant_id='d'*32)
  self.assertEqual(no.compare(network_manifest()['resources'][0],value,PROJECT)['status'],'DIFFERENT')
 def test_order_irrelevant_duplicate_visible(self):
  self.assertTrue(no.equal([{'x':1},{'x':2}],[{'x':2},{'x':1}]))
  self.assertFalse(no.equal([{'x':1},{'x':1}],[{'x':1}]))
 def test_duplicate_json_rejected(self):
  with self.assertRaises(ValueError):no.strict_loads('{"x":1,"x":2}')
 def test_nonfinite_json_rejected(self):
  with self.assertRaises(ValueError):no.strict_loads('{"x":NaN}')
 def test_http_and_foreign_origins_rejected(self):
  for endpoint,origin in [('http://127.0.0.1/v2.0','http://127.0.0.1'),('https://host/v2.0','https://other'),('https://user:pass@host/v2.0','https://host')]:
   with self.subTest(endpoint=endpoint),self.assertRaises(ValueError):no.Client(endpoint,origin,'sentinel')
 def test_missing_token_rejected(self):
  with self.assertRaises(ValueError):no.Client('https://host/v2.0','https://host','')
 def test_empty_collection_never_success(self):
  with self.assertRaises(ValueError):no.observe({'project_id':PROJECT,'engineering_record_ref':'ENG','resources':[]},None)
 def test_live_command_requires_opt_in(self):
  result=subprocess.run([os.sys.executable,str(ROOT/'tools/neutron_observe.py'),'does-not-exist',
    '--endpoint','https://invalid.example/v2.0','--expected-origin','https://invalid.example','--output','unused'],capture_output=True,text=True,timeout=5)
  self.assertNotEqual(result.returncode,0);self.assertIn('No target contacted',result.stderr)


class HttpsReadbackTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory(prefix='neutron-https-test-');base=Path(cls.temp.name)
  cls.cert,cls.key=base/'cert.pem',base/'key.pem'
  result=subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1','-subj','/CN=localhost',
    '-addext','subjectAltName=IP:127.0.0.1,DNS:localhost','-keyout',str(cls.key),'-out',str(cls.cert)],capture_output=True,timeout=15)
  if result.returncode:raise RuntimeError('Local test certificate generation failed')
  cls.count=0;cls.mode='good';cls.received=[]
  class Handler(BaseHTTPRequestHandler):
   def log_message(self,*args):pass
   def do_GET(self):
    cls.count+=1;cls.received.append((self.command,self.path,self.headers.get('X-Auth-Token')))
    mode=cls.mode
    if mode=='redirect':
     self.send_response(302);self.send_header('Location','https://not-contacted.invalid/');self.end_headers();return
    if mode=='missing':self.send_response(404);self.end_headers();return
    if mode=='wrong-type':body=b'<h1>unexpected</h1>'
    elif mode=='duplicate':body=b'{"network":{},"network":{}}'
    else:
     value=network_actual()
     if mode=='changing':value['revision_number']=cls.count
     if mode=='foreign':value['project_id']='d'*32
     value['password']='DO-NOT-EXPORT'
     body=json.dumps({'network':value}).encode()
    self.send_response(200);self.send_header('Content-Type','text/html' if mode=='wrong-type' else 'application/json')
    self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
  cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
  ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);ctx.load_cert_chain(str(cls.cert),str(cls.key))
  cls.server.socket=ctx.wrap_socket(cls.server.socket,server_side=True)
  cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
  cls.origin=f'https://127.0.0.1:{cls.server.server_port}'
 @classmethod
 def tearDownClass(cls):
  cls.server.shutdown();cls.server.server_close();cls.thread.join(3);cls.temp.cleanup()
 def setUp(self):type(self).mode='good';type(self).count=0;type(self).received=[]
 def client(self,trust=True):return no.Client(self.origin+'/v2.0',self.origin,'TEMP-TOKEN-SENTINEL',str(self.cert) if trust else None)
 def test_actual_verified_https_gets_only(self):
  r=no.observe(network_manifest(),self.client());self.assertEqual(r['status'],'OBSERVED_MATCH_NOT_QUALIFIED')
  self.assertEqual(type(self).count,2);self.assertTrue(all(x[0]=='GET' for x in type(self).received))
  self.assertNotIn('TEMP-TOKEN-SENTINEL',json.dumps(r));self.assertNotIn('DO-NOT-EXPORT',json.dumps(r))
 def test_ambient_sslkeylogfile_not_used(self):
  from unittest.mock import patch
  path=Path(self.temp.name)/'must-not-be-written.log'
  with patch.dict(os.environ,{'SSLKEYLOGFILE':str(path)}):
   r=no.observe(network_manifest(),self.client())
  self.assertEqual(r['status'],'OBSERVED_MATCH_NOT_QUALIFIED');self.assertFalse(path.exists())
 def test_untrusted_certificate_not_accepted(self):
  r=no.observe(network_manifest(),self.client(False));self.assertEqual(r['status'],'INCONCLUSIVE');self.assertEqual(type(self).count,0)
 def test_redirect_never_followed(self):
  type(self).mode='redirect';r=no.observe(network_manifest(),self.client());self.assertEqual(r['status'],'INCONCLUSIVE');self.assertEqual(type(self).count,1)
 def test_missing_resource_is_not_safe_deletion_proof(self):
  type(self).mode='missing';r=no.observe(network_manifest(),self.client());self.assertEqual(r['status'],'INCONCLUSIVE');self.assertEqual(r['captures'][0]['http_status'],404)
 def test_changed_reads_inconclusive(self):
  type(self).mode='changing';r=no.observe(network_manifest(),self.client());self.assertEqual(r['status'],'INCONCLUSIVE');self.assertFalse(r['captures'][0]['stable_two_reads'])
 def test_wrong_content_type(self):
  type(self).mode='wrong-type';self.assertEqual(no.observe(network_manifest(),self.client())['status'],'INCONCLUSIVE')
 def test_duplicate_key_response(self):
  type(self).mode='duplicate';self.assertEqual(no.observe(network_manifest(),self.client())['status'],'INCONCLUSIVE')
 def test_foreign_project_reported(self):
  type(self).mode='foreign';self.assertEqual(no.observe(network_manifest(),self.client())['status'],'DIFFERENCES_OBSERVED')


class RouteRecordTests(unittest.TestCase):
 def setUp(self):
  self.inputs={'tenant_key':'tenant-01','domain_key':'D01O','route_key':'dns','destination_cidr':'10.80.4.20/32',
   'engineering_record_ref':'ENG-0052','attachment_acceptance_ref':'EDGE-0027','router_id':RID,'next_hop_address':'10.80.0.1',
   'allow_restricted_build':True,'test_authorization_ref':'LAB-0017'}
  self.record={'module':'openstack-route','route':{k:v for k,v in self.inputs.items() if k in COMMON|FIELDS['openstack-route']},
    'valid_from':'2026-09-01T00:00:00Z','valid_until':'2026-10-01T00:00:00Z','attachment_cidr':'10.80.0.0/30'}
  self.now=datetime(2026,9,17,tzinfo=timezone.utc)
 def result(self):return review('openstack-route',self.inputs,self.record,self.now)
 def test_matching_record_not_authorization(self):self.assertEqual(self.result()['status'],'RECORD_MATCH_NOT_AUTHORIZED')
 def test_other_tenant_blocked(self):self.inputs['tenant_key']='tenant-02';self.assertEqual(self.result()['status'],'BLOCKED')
 def test_other_router_blocked(self):self.inputs['router_id']='different';self.assertEqual(self.result()['status'],'BLOCKED')
 def test_default_route_rejected(self):self.inputs['destination_cidr']='0.0.0.0/0';self.assertEqual(self.result()['status'],'BLOCKED')
 def test_noncanonical_prefix_rejected(self):self.inputs['destination_cidr']='10.80.4.20/24';self.assertEqual(self.result()['status'],'BLOCKED')
 def test_example_prefix_rejected(self):self.inputs['destination_cidr']='203.0.113.138/32';self.assertEqual(self.result()['status'],'BLOCKED')
 def test_offlink_hop_rejected(self):self.inputs['next_hop_address']='10.81.0.1';self.assertEqual(self.result()['status'],'BLOCKED')
 def test_broadcast_hop_rejected(self):self.inputs['next_hop_address']='10.80.0.3';self.assertEqual(self.result()['status'],'BLOCKED')
 def test_expired_record_rejected(self):self.record['valid_until']='2026-09-02T00:00:00Z';self.assertEqual(self.result()['status'],'BLOCKED')
 def test_naive_time_rejected(self):self.record['valid_until']='2026-10-02T00:00:00';self.assertEqual(self.result()['status'],'BLOCKED')
 def test_omitted_attachment_rejected(self):del self.record['attachment_cidr'];self.assertEqual(self.result()['status'],'BLOCKED')
 def test_no_optin(self):self.inputs['allow_restricted_build']=False;self.assertEqual(self.result()['status'],'BLOCKED')


class NewNativeSources(unittest.TestCase):
 def load(self,name):return json.loads((ROOT/'terraform/modules'/name/'main.tf.json').read_text())
 def test_three_native_routes_no_new_topology(self):
  for name,kind in [('nsx-route','nsxt_policy_static_route'),('openstack-route','openstack_networking_router_route_v2'),('nutanix-route','nutanix_routes_v2')]:
   self.assertEqual(set(self.load(name)['resource']),{kind})
 def test_nutanix_route_external_subnet_reference(self):
  r=self.load('nutanix-route')['resource']['nutanix_routes_v2']['owned']
  self.assertEqual(r['next_hop'][0]['next_hop_type'],'EXTERNAL_SUBNET');self.assertEqual(r['route_type'],'STATIC')
 def test_routes_reject_default_in_input_validation(self):
  for name in ('nsx-route','openstack-route','nutanix-route'):
   self.assertIn('> 0',self.load(name)['variable']['destination_cidr']['validation'][0]['condition'])
 def test_existing_context_not_created(self):
  for name in ('nsx-route','openstack-route','nutanix-route'):
   self.assertNotIn('0.0.0.0/0',json.dumps(self.load(name)))
 def test_gateway_policy_scoped_denies_both_families(self):
  p=self.load('nsx-gateway-quarantine')['resource']['nsxt_policy_gateway_policy']['owned']
  self.assertIs(p['stateful'],True);self.assertEqual(len(p['rule']),1)
  r=p['rule'][0];self.assertEqual(r['scope'],['${var.gateway_path}']);self.assertEqual(r['action'],'DROP');self.assertIs(r['logged'],True);self.assertFalse(r['disabled'])
 def test_new_guard_has_engineering_and_attachment_refs(self):
  for name in ('nsx-route','openstack-route','nutanix-route','nsx-gateway-quarantine'):
   for resources in self.load(name)['resource'].values():
    for r in resources.values():
     condition=r['lifecycle']['precondition'][0]['condition'];self.assertIn('var.engineering_record_ref',condition);self.assertIn('var.attachment_acceptance_ref',condition)

class ExtendedPlanTests(unittest.TestCase):
 def route_plan(self,destination='10.80.4.20/32',next_hop='10.80.0.1'):
  return {'format_version':'1.2','resource_changes':[{'address':'module.owned.openstack_networking_router_route_v2.owned',
   'mode':'managed','type':'openstack_networking_router_route_v2','provider_name':'registry.terraform.io/terraform-provider-openstack/openstack',
   'change':{'actions':['create'],'after':{'router_id':RID,'destination_cidr':destination,'next_hop':next_hop},'after_unknown':{}}}]}
 def test_route_always_requires_independent_review(self):
  from tools.plan_review import review
  result=review(self.route_plan(),{'router_id':[RID]});self.assertEqual(result['status'],'REVIEW_REQUIRED')
 def test_route_default_blocked(self):
  from tools.plan_review import review
  self.assertEqual(review(self.route_plan('0.0.0.0/0'))['status'],'BLOCKED')
 def test_route_ipv6_not_silently_enabled(self):
  from tools.plan_review import review
  self.assertEqual(review(self.route_plan('2001:db8::/64'))['status'],'BLOCKED')
 def test_route_bad_hop_blocked(self):
  from tools.plan_review import review
  self.assertEqual(review(self.route_plan(next_hop='not-an-ip'))['status'],'BLOCKED')
 def test_route_foreign_target_blocked(self):
  from tools.plan_review import review
  self.assertEqual(review(self.route_plan(),{'router_id':['other']})['status'],'BLOCKED')
 def test_all_mock_sources_plan_only(self):
  from tools.verify_terraform import plan_only_mock_tests
  for directory in (ROOT/'terraform/modules').iterdir():self.assertTrue(plan_only_mock_tests(directory),directory.name)
 def test_apply_test_source_rejected(self):
  from tools.verify_terraform import plan_only_mock_tests
  with tempfile.TemporaryDirectory() as temporary:
   p=Path(temporary);(p/'tests').mkdir();(p/'main.tf.json').write_text('{"terraform":{"required_providers":{"nsxt":{}}}}')
   (p/'tests/x.tftest.hcl').write_text('mock_provider "nsxt" {}\nrun "x" { command = apply }')
   self.assertFalse(plan_only_mock_tests(p))
