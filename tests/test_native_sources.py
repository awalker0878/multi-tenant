"""Source-structure checks only. These do NOT run the Terraform parser/provider."""
import json,re,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(name):return json.loads((ROOT/'terraform/modules'/name/'main.tf.json').read_text())
class NativeSources(unittest.TestCase):
 def test_ten_nonempty_native_modules(self):
  mods=list((ROOT/'terraform/modules').glob('*/main.tf.json'));self.assertEqual(len(mods),10)
  for p in mods:self.assertTrue(json.loads(p.read_text()).get('resource'))
 def test_no_placeholder_actuators(self):
  for p in (ROOT/'terraform/modules').glob('*/main.tf.json'):
   j=json.loads(p.read_text());self.assertFalse(set(j['resource'])&{'terraform_data','null_resource'});self.assertNotIn('local-exec',p.read_text());self.assertNotIn('remote-exec',p.read_text())
 def test_every_resource_has_destruction_guard(self):
  for p in (ROOT/'terraform/modules').glob('*/main.tf.json'):
   for types in json.loads(p.read_text())['resource'].values():
    for config in types.values():self.assertIs(config['lifecycle']['prevent_destroy'],True)
 def test_every_resource_has_restricted_opt_in_precondition(self):
  for p in (ROOT/'terraform/modules').glob('*/main.tf.json'):
   for types in json.loads(p.read_text())['resource'].values():
    for config in types.values():self.assertIn('var.allow_restricted_build',config['lifecycle']['precondition'][0]['condition'])
 def test_roots_child_variable_parity(self):
  for p in (ROOT/'terraform/roots').glob('*/main.tf.json'):
   root=json.loads(p.read_text());child=load(p.parent.name);call=root['module']['owned'];args=set(call)-{'source','providers'};self.assertEqual(args,set(child['variable']))
 def test_no_provider_config_in_children(self):
  for p in (ROOT/'terraform/modules').glob('*/main.tf.json'):self.assertNotIn('provider',json.loads(p.read_text()))
 def test_explicit_provider_in_roots(self):
  for p in (ROOT/'terraform/roots').glob('*/main.tf.json'):
   root=json.loads(p.read_text());self.assertEqual(len(root['provider']),1)
   for conf in root['provider'].values():
    self.assertFalse(conf.get('insecure',False));self.assertFalse(conf.get('allow_unverified_ssl',False))
 def test_no_silent_local_state_backend(self):
  for p in (ROOT/'terraform/roots').glob('*/main.tf.json'):self.assertEqual(json.loads(p.read_text())['terraform']['backend'],{'http':{}})
 def test_pins_consistent(self):
  for p in (ROOT/'terraform/roots').glob('*/main.tf.json'):
   self.assertEqual(json.loads(p.read_text())['terraform']['required_providers'],load(p.parent.name)['terraform']['required_providers'])
 def test_no_active_examples_or_credentials(self):
  for p in (ROOT/'terraform/roots').glob('*/inputs.tfvars.json.example'):
   j=json.loads(p.read_text());self.assertIs(j['allow_restricted_build'],False);self.assertNotIn('platform_password',j)
 def test_nutanix_vpc_no_external_attachment(self):self.assertNotIn('external_subnets',load('nutanix-domain')['resource']['nutanix_vpc_v2']['domain'])
 def test_nutanix_policy_enforced_scoped(self):
  p=load('nutanix-domain')['resource']['nutanix_network_security_policy_v2']['quarantine'];self.assertEqual(p['state'],'ENFORCE');self.assertEqual(p['scope'],'VPC_LIST');self.assertEqual(len(p['vpc_reference']),1)
 def test_nutanix_category_uses_documented_id(self):self.assertIn('nutanix_category_v2.domain.id',json.dumps(load('nutanix-domain')));self.assertNotIn('nutanix_category_v2.domain.ext_id',json.dumps(load('nutanix-domain')))
 def test_nsx_tier0_not_bound(self):self.assertNotIn('tier0_path',load('nsx-domain')['resource']['nsxt_policy_tier1_gateway']['domain'])
 def test_nsx_drop_is_explicit_and_bounded(self):
  p=load('nsx-domain')['resource']['nsxt_policy_security_policy']['quarantine'];self.assertEqual(len(p['scope']),1);self.assertEqual(p['rule'][0]['action'],'DROP');self.assertIs(p['rule'][0]['logged'],True)
 def test_nsx_off_gateway_configuration(self):self.assertEqual(load('nsx-domain')['resource']['nsxt_policy_segment']['domain']['advanced_config'][0]['connectivity'],'OFF')
 def test_openstack_no_external_router(self):
  r=load('openstack-domain')['resource']['openstack_networking_router_v2']['domain'];self.assertNotIn('external_network_id',r);self.assertNotIn('enable_snat',r);self.assertIs(r['admin_state_up'],False)
 def test_openstack_own_empty_group(self):self.assertIs(load('openstack-domain')['resource']['openstack_networking_secgroup_v2']['quarantine']['delete_default_rules'],True)
 def test_openstack_group_on_port_not_server(self):
  r=load('openstack-workload')['resource'];self.assertNotIn('security_groups',r['openstack_compute_instance_v2']['workload']);self.assertEqual(len(r['openstack_networking_port_v2']['workload']['security_group_ids']),1)
 def test_openstack_retains_boot_volume(self):self.assertIs(load('openstack-workload')['resource']['openstack_compute_instance_v2']['workload']['block_device'][0]['delete_on_termination'],False)
 def test_openstack_flavor_not_unused_cpu_knob(self):
  j=load('openstack-workload');self.assertNotIn('vcpu',j['variable']);self.assertNotIn('memory_gib',j['variable']);self.assertIn('flavor_id',j['variable'])
 def test_nutanix_actual_nic_disconnected(self):
  vm=load('nutanix-workload')['resource']['nutanix_virtual_machine_v2']['workload'];self.assertEqual(vm['power_state'],'OFF');self.assertIs(vm['nics'][0]['nic_backing_info'][0]['virtual_ethernet_nic'][0]['is_connected'],False)
 def test_vsphere_no_invented_power_switch(self):
  vm=load('vsphere-workload')['resource']['vsphere_virtual_machine']['workload'];self.assertNotIn('power_state',vm);self.assertNotIn('start_connected',vm['network_interface'][0])
 def test_vsphere_disk_policy_applied_to_disks(self):
  vm=load('vsphere-workload')['resource']['vsphere_virtual_machine']['workload'];self.assertEqual(vm['disk'][0]['storage_policy_id'],'${var.storage_policy_id}');self.assertEqual(vm['dynamic']['disk']['content']['storage_policy_id'],'${var.storage_policy_id}')
 def test_variable_references_declared(self):
  for p in (ROOT/'terraform/modules').glob('*/main.tf.json'):
   j=json.loads(p.read_text());names=set(re.findall(r'var\.([A-Za-z0-9_]+)',p.read_text()));self.assertLessEqual(names,set(j['variable']),p.parent.name)
 def test_no_native_ipv6_promise_in_ipv4_modules(self):
  for name in ('nutanix-domain','nsx-domain','openstack-domain'):self.assertNotIn('ipv6_cidr',load(name)['variable'])
 def test_mock_tests_present_not_live(self):
  for p in (ROOT/'terraform/modules').glob('*/tests/*.tftest.hcl'):
   self.assertIn('mock_provider',p.read_text());self.assertNotIn('command = apply',p.read_text())
