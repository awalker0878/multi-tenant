import copy,json,unittest
from pathlib import Path
from tools.input_review import review_inputs
ROOT=Path(__file__).resolve().parents[1]

def config():return json.loads((ROOT/'terraform/roots/openstack-domain/main.tf.json').read_text())
def values():return {'tenant_key':'tenant-01','domain_key':'D01O','allow_restricted_build':True,'test_authorization_ref':'CHG-4714','ipv4_cidr':'10.240.0.0/27','project_id':'9d3a2f01-c428-4d0b-aedf-658a431f2203','openstack_cloud':'qualified-lab-project01'}
class Inputs(unittest.TestCase):
 def test_valid_shape_not_authorized(self):self.assertEqual(review_inputs(config(),values())['status'],'INPUT_SHAPE_CHECKED_NOT_AUTHORIZED')
 def test_all_shipped_examples_blocked(self):
  for root in (ROOT/'terraform/roots').iterdir():
   with self.subTest(root=root.name):self.assertEqual(review_inputs(json.loads((root/'main.tf.json').read_text()),json.loads((root/'inputs.tfvars.json.example').read_text()))['status'],'BLOCKED_INPUTS')
 def test_missing_project(self):
  v=values();del v['project_id'];self.assertEqual(review_inputs(config(),v)['status'],'BLOCKED_INPUTS')
 def test_unknown_property(self):
  v=values();v['public_ingress']=True;self.assertEqual(review_inputs(config(),v)['status'],'BLOCKED_INPUTS')
 def test_docs_prefix(self):
  v=values();v['ipv4_cidr']='192.0.2.0/27';self.assertEqual(review_inputs(config(),v)['status'],'BLOCKED_INPUTS')
 def test_second_docs_prefix(self):
  v=values();v['ipv4_cidr']='203.0.113.128/27';self.assertEqual(review_inputs(config(),v)['status'],'BLOCKED_INPUTS')
 def test_wrong_family(self):
  v=values();v['ipv4_cidr']='2001:db8:1::/64';self.assertEqual(review_inputs(config(),v)['status'],'BLOCKED_INPUTS')
 def test_noncanonical_prefix(self):
  v=values();v['ipv4_cidr']='10.240.0.1/27';self.assertEqual(review_inputs(config(),v)['status'],'BLOCKED_INPUTS')
 def test_no_opt_in(self):
  v=values();v['allow_restricted_build']=False;self.assertEqual(review_inputs(config(),v)['status'],'BLOCKED_INPUTS')
 def test_bool_not_string(self):
  v=values();v['allow_restricted_build']='true';self.assertEqual(review_inputs(config(),v)['status'],'BLOCKED_INPUTS')
 def test_gateway_network_address(self):
  v=values();v['gateway_host_number']=0;self.assertEqual(review_inputs(config(),v)['status'],'BLOCKED_INPUTS')
 def test_gateway_broadcast_address(self):
  v=values();v['gateway_host_number']=31;self.assertEqual(review_inputs(config(),v)['status'],'BLOCKED_INPUTS')
 def test_gateway_outside_prefix(self):
  v=values();v['gateway_host_number']=40;self.assertEqual(review_inputs(config(),v)['status'],'BLOCKED_INPUTS')
 def test_gateway_fraction(self):
  v=values();v['gateway_host_number']=1.5;self.assertEqual(review_inputs(config(),v)['status'],'BLOCKED_INPUTS')
 def test_gateway_bool(self):
  v=values();v['gateway_host_number']=True;self.assertEqual(review_inputs(config(),v)['status'],'BLOCKED_INPUTS')
 def test_placeholder_project(self):
  v=values();v['project_id']='11111111-1111-4111-8111-111111111111';self.assertEqual(review_inputs(config(),v)['status'],'BLOCKED_INPUTS')
 def test_empty_authorization_ref(self):
  v=values();v['test_authorization_ref']='';self.assertEqual(review_inputs(config(),v)['status'],'BLOCKED_INPUTS')
 def test_malformed(self):
  with self.assertRaises(ValueError):review_inputs([],None)
 def test_plaintext_secret_blocked_and_not_echoed(self):
  v=values();v['password']='SENTINEL-SECRET';r=review_inputs(config(),v);self.assertEqual(r['status'],'BLOCKED_INPUTS');self.assertNotIn('SENTINEL',json.dumps(r))
 def test_loopback_rejected(self):
  v=values();v['ipv4_cidr']='127.0.0.0/24';self.assertEqual(review_inputs(config(),v)['status'],'BLOCKED_INPUTS')
