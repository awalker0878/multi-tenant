import copy,json,tempfile,unittest
from pathlib import Path
from tools.route_audit import ModelError,Topology,load_json
ROOT=Path(__file__).resolve().parents[1]

def fixture():return json.loads((ROOT/'examples/wd14-routing.json').read_text())

class Routes(unittest.TestCase):
 def setUp(self):self.d=fixture();self.t=Topology(self.d)
 def test_reference_has_exact_four_domains(self):self.assertEqual(sorted(n for n in self.d['nodes'] if n.startswith('NG-')),['NG-D01O','NG-D01R','NG-D02O','NG-D02R'])
 def test_full_reference_checks(self):self.assertEqual(self.t.audit()['failed'],0)
 def test_primary_forward_ipv4(self):self.assertEqual(self.t.trace('processor-01','data-01',4)['path'],['processor-01','NG-D01O','EC-01','NG-D01R','data-01'])
 def test_primary_reverse_ipv6(self):self.assertEqual(self.t.trace('data-01','processor-01',6)['path'],['data-01','NG-D01R','EC-01','NG-D01O','processor-01'])
 def test_service_reply_owner(self):self.assertEqual(self.t.trace('resolver','processor-02',4)['path'],['resolver','SE-02','EC-02','NG-D02O','processor-02'])
 def test_unsolicited_reverse_denied(self):self.assertEqual(self.t.session('data-01','processor-01','tcp',443,4)['outcome'],'MODEL_POLICY_DENY')
 def test_tcp_dns_declared(self):self.assertEqual(self.t.session('processor-01','resolver','tcp',53,4)['outcome'],'MODEL_PATH_AND_INTENT_MATCH')
 def test_udp_dns_declared(self):self.assertEqual(self.t.session('data-02','resolver','udp',53,6)['outcome'],'MODEL_PATH_AND_INTENT_MATCH')
 def test_wrong_service_port_denied(self):self.assertEqual(self.t.session('processor-01','resolver','tcp',443,4)['outcome'],'MODEL_POLICY_DENY')
 def test_unselected_time_protocol_not_guessed(self):self.assertEqual(self.t.session('processor-01','time','udp',123,4)['outcome'],'MODEL_POLICY_DENY')
 def test_unselected_log_protocol_not_guessed(self):self.assertEqual(self.t.session('processor-01','logs','tcp',6514,6)['outcome'],'MODEL_POLICY_DENY')
 def test_wrong_service_return_detected(self):
  self.d['nodes']['resolver']['routes'][0]['next_hop']='203.0.113.130'
  self.assertGreater(Topology(self.d).audit()['failed'],0)
 def test_missing_service_return_detected(self):
  del self.d['nodes']['resolver']['routes'][0]
  self.assertGreater(Topology(self.d).audit()['failed'],0)
 def test_missing_ec_route_detected(self):
  del self.d['nodes']['EC-01']['routes'][0]
  self.assertGreater(Topology(self.d).audit()['failed'],0)
 def test_route_loop_detected(self):
  self.d['nodes']['EC-01']['routes'][2]['next_hop']='198.51.100.2'
  self.assertEqual(Topology(self.d).trace('processor-01','data-01',4)['outcome'],'LOOP')
 def test_equal_route_ambiguity_rejected(self):
  self.d['nodes']['EC-01']['routes'].append(copy.deepcopy(self.d['nodes']['EC-01']['routes'][0]))
  with self.assertRaises(ModelError):Topology(self.d)
 def test_undefined_next_hop_rejected(self):
  self.d['nodes']['NG-D01O']['routes'][0]['next_hop']='198.51.100.30'
  with self.assertRaises(ModelError):Topology(self.d)
 def test_nonconnected_next_hop_rejected(self):
  self.d['nodes']['NG-D01O']['routes'][0]['next_hop']='198.51.100.5'
  with self.assertRaises(ModelError):Topology(self.d)
 def test_cross_family_next_hop_rejected(self):
  self.d['nodes']['NG-D01O']['routes'][0]['next_hop']='2001:db8:200:1::1'
  with self.assertRaises(ModelError):Topology(self.d)
 def test_router_default_rejected(self):
  self.d['nodes']['NG-D01O']['routes'].append({'destination':'0.0.0.0/0','next_hop':'198.51.100.1'})
  with self.assertRaises(ModelError):Topology(self.d)
 def test_duplicate_interface_ip_rejected(self):
  self.d['nodes']['processor-01']['interfaces'][0]['address']='192.0.2.1/27'
  with self.assertRaises(ModelError):Topology(self.d)
 def test_inconsistent_segment_prefix_rejected(self):
  self.d['nodes']['processor-01']['interfaces'][0]['address']='192.0.2.10/28'
  with self.assertRaises(ModelError):Topology(self.d)
 def test_cross_tenant_permission_rejected(self):
  self.d['approved_flows'][0]['destination']='data-02'
  with self.assertRaises(ModelError):Topology(self.d)
 def test_path_without_edge_rejected(self):
  self.d['approved_flows'][0]['via']=['NG-D01O','NG-D01R']
  with self.assertRaises(ModelError):Topology(self.d)
 def test_foreign_edge_rejected(self):
  self.d['approved_flows'][0]['via']=['NG-D01O','EC-02','NG-D01R']
  with self.assertRaises(ModelError):Topology(self.d)
 def test_duplicate_flow_id_rejected(self):
  self.d['approved_flows'].append(copy.deepcopy(self.d['approved_flows'][0]))
  with self.assertRaises(ModelError):Topology(self.d)
 def test_empty_model_rejected(self):
  with self.assertRaises(ModelError):Topology({})
 def test_unknown_route_mechanism_rejected(self):
  self.d['nodes']['EC-01']['routes'][0]['pbr']='anything'
  with self.assertRaises(ModelError):Topology(self.d)
 def test_malformed_node_rejected(self):
  self.d['nodes']['x']=None
  with self.assertRaises(ModelError):Topology(self.d)
 def test_bool_port_rejected(self):
  self.d['approved_flows'][0]['port']=True
  with self.assertRaises(ModelError):Topology(self.d)
 def test_duplicate_json_property_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'a.json';p.write_text('{"a":1,"a":2}')
   with self.assertRaises(ModelError):load_json(p)

# Independent cross-tenant direction and family checks are separately named.
for fam in (4,6):
 for src,dst in [('processor-01','processor-02'),('processor-01','data-02'),('data-01','processor-02'),('data-01','data-02'),('processor-02','processor-01'),('data-02','data-01')]:
  def test(self,s=src,d=dst,f=fam):self.assertEqual(self.t.trace(s,d,f)['outcome'],'NO_ROUTE')
  setattr(Routes,f'test_no_cross_tenant_{src}_{dst}_ipv{fam}'.replace('-','_'),test)
