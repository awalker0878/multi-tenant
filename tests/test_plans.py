import copy,json,unittest
from tools.plan_review import PlanError,review

def plan(kind='openstack_networking_network_v2',after=None,actions=None):
 return {'format_version':'1.2','terraform_version':'synthetic','resource_changes':[{'address':'module.owned.'+kind+'.domain','mode':'managed','type':kind,'provider_name':'registry.terraform.io/terraform-provider-openstack/openstack',
 'change':{'actions':actions or ['create'],'before':None,'after':after or {'admin_state_up':False,'shared':False,'external':False,'port_security_enabled':True},'after_unknown':{}}}]}
def codes(result):return {x['code'] for x in result['findings']}

class Plans(unittest.TestCase):
 def test_no_static_violation_is_not_authorization(self):
  r=review(plan());self.assertEqual(r['status'],'NO_STATIC_VIOLATIONS');self.assertEqual(r['authorization'],'NOT_EVALUATED')
 def test_deletion_blocked(self):self.assertEqual(review(plan(actions=['delete']))['status'],'BLOCKED')
 def test_create_then_destroy_blocked(self):self.assertEqual(review(plan(actions=['create','delete']))['status'],'BLOCKED')
 def test_destroy_then_create_blocked(self):self.assertEqual(review(plan(actions=['delete','create']))['status'],'BLOCKED')
 def test_update_requires_review(self):self.assertIn('UPDATE_REQUIRES_CHANGE_AND_DATA_REVIEW',codes(review(plan(actions=['update']))))
 def test_unknown_action_blocked(self):self.assertEqual(review(plan(actions=['forget']))['status'],'BLOCKED')
 def test_external_network_blocked(self):
  p=plan();p['resource_changes'][0]['change']['after']['external']=True;self.assertEqual(review(p)['status'],'BLOCKED')
 def test_admin_up_blocked(self):
  p=plan();p['resource_changes'][0]['change']['after']['admin_state_up']=True;self.assertEqual(review(p)['status'],'BLOCKED')
 def test_port_security_disabled_blocked(self):
  p=plan();p['resource_changes'][0]['change']['after']['port_security_enabled']=False;self.assertEqual(review(p)['status'],'BLOCKED')
 def test_string_false_not_false(self):
  p=plan();p['resource_changes'][0]['change']['after']['external']='false';self.assertEqual(review(p)['status'],'BLOCKED')
 def test_unknown_external_not_pass(self):
  p=plan();p['resource_changes'][0]['change']['after_unknown']['external']=True;self.assertEqual(review(p)['status'],'REVIEW_REQUIRED')
 def test_nested_unknown_not_pass(self):
  p=plan();p['resource_changes'][0]['change']['after_unknown']['binding']=[{'profile':True}];self.assertEqual(review(p)['status'],'REVIEW_REQUIRED')
 def test_computed_id_only_can_be_unknown(self):
  p=plan();p['resource_changes'][0]['change']['after_unknown']['id']=True;self.assertEqual(review(p)['status'],'NO_STATIC_VIOLATIONS')
 def test_whole_unknown_review(self):
  p=plan();p['resource_changes'][0]['change']['after_unknown']=True;self.assertEqual(review(p)['status'],'REVIEW_REQUIRED')
 def test_false_unknown_mask_supported(self):
  p=plan();p['resource_changes'][0]['change']['after_unknown']=False;self.assertEqual(review(p)['status'],'NO_STATIC_VIOLATIONS')
 def test_unexpected_provider_blocked(self):
  p=plan();p['resource_changes'][0]['provider_name']='registry.terraform.io/foreign/openstack';self.assertEqual(review(p)['status'],'BLOCKED')
 def test_unexpected_resource_blocked(self):self.assertEqual(review(plan('openstack_networking_floatingip_v2'))['status'],'BLOCKED')
 def test_empty_plan_review(self):
  p=plan();p['resource_changes']=[];self.assertEqual(review(p)['status'],'REVIEW_REQUIRED')
 def test_errored_plan_blocked(self):
  p=plan();p['errored']=True;self.assertEqual(review(p)['status'],'BLOCKED')
 def test_incomplete_plan_review(self):
  p=plan();p['complete']=False;self.assertEqual(review(p)['status'],'REVIEW_REQUIRED')
 def test_native_drift_review(self):
  p=plan();p['resource_drift']=[{}];self.assertEqual(review(p)['status'],'REVIEW_REQUIRED')
 def test_provisioner_in_child_blocked(self):
  p=plan();p['configuration']={'root_module':{'module_calls':{'x':{'module':{'resources':[{'provisioners':[{'type':'local-exec'}]}]}}}}};self.assertEqual(review(p)['status'],'BLOCKED')
 def test_state_file_not_plan(self):
  with self.assertRaises(PlanError):review({'format_version':'1.0','values':{}})
 def test_unknown_major_rejected(self):
  p=plan();p['format_version']='2.0'
  with self.assertRaises(PlanError):review(p)
 def test_duplicate_resource_rejected(self):
  p=plan();p['resource_changes']*=2
  with self.assertRaises(PlanError):review(p)
 def test_nonobject_resource_rejected(self):
  p=plan();p['resource_changes']=[None]
  with self.assertRaises(PlanError):review(p)
 def test_wrong_project_binding_blocked(self):
  p=plan();p['resource_changes'][0]['change']['after']['tenant_id']='foreign';self.assertEqual(review(p,{'tenant_id':['accepted']})['status'],'BLOCKED')
 def test_missing_project_binding_review(self):
  p=plan();p['resource_changes'][0]['change']['after']['tenant_id']='accepted';self.assertEqual(review(p)['status'],'REVIEW_REQUIRED')
 def test_bound_project_shape_ok(self):
  p=plan();p['resource_changes'][0]['change']['after']['tenant_id']='accepted';self.assertEqual(review(p,{'tenant_id':['accepted']})['status'],'NO_STATIC_VIOLATIONS')
 def test_old_import_review(self):
  p=plan();p['resource_changes'][0]['change']['importing']={'id':'known'};self.assertIn('OWNERSHIP_ADOPTION_OR_DEPOSED_OBJECT',codes(review(p)))
 def test_failed_check_blocks(self):
  p=plan();p['checks']=[{'status':'fail'}];self.assertEqual(review(p)['status'],'BLOCKED')
 def test_missing_security_field_review(self):
  p=plan();del p['resource_changes'][0]['change']['after']['external'];self.assertEqual(review(p)['status'],'REVIEW_REQUIRED')
 def test_secret_values_not_emitted(self):
  p=plan();p['variables']={'password':{'value':'SENTINEL-PRIVATE-SECRET'}};p['resource_changes'][0]['change']['after']['admin_pass']='SENTINEL-PRIVATE-SECRET';self.assertNotIn('SENTINEL',json.dumps(review(p)))
 def test_missing_after_rejected(self):
  p=plan();p['resource_changes'][0]['change']['after']=None
  with self.assertRaises(PlanError):review(p)

 def test_malformed_segment_block_is_diagnostic(self):
  p=plan('nsxt_policy_segment',{'advanced_config':['invalid']})
  with self.assertRaises(PlanError):review(p)
 def test_malformed_boot_block_is_diagnostic(self):
  p=plan('openstack_compute_instance_v2',{'power_state':'shutoff','block_device':['invalid']})
  with self.assertRaises(PlanError):review(p)
 def test_malformed_vmware_nic_is_diagnostic(self):
  p=plan('vsphere_virtual_machine',{'network_interface':['invalid'],'disk':[]})
  with self.assertRaises(PlanError):review(p)
 def test_malformed_vmware_disk_list_is_diagnostic(self):
  p=plan('vsphere_virtual_machine',{'network_interface':[{'network_id':'accepted'}],'disk':None})
  with self.assertRaises(PlanError):review(p)
