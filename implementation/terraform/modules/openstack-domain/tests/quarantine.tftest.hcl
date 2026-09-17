# NOT EXECUTED IN THIS RELEASE. Requires Terraform >= 1.7 and the pinned provider.
mock_provider "openstack" {}

variables {
  tenant_key = "tenant-01"
  domain_key = "D01O"
  allow_restricted_build = true
  test_authorization_ref = "MOCK-ONLY-NO-REAL-AUTHORITY"
  ipv4_cidr = "192.0.2.0/27"
  gateway_host_number = 1
  project_id = "11111111-1111-4111-8111-111111111111"
}

run "quarantine_configuration" {
  command = plan
  assert {
    condition = output.delivery_state == "PREPARED_NOT_QUALIFIED_NOT_SERVICE_READY"
    error_message = "A module must not label preparation as service readiness."
  }
  assert {
    condition = openstack_networking_network_v2.domain.admin_state_up == false
    error_message = "Network must remain down."
  }
  assert {
    condition = openstack_networking_secgroup_v2.quarantine.delete_default_rules == true
    error_message = "Group default user rules must be removed."
  }
  assert {
    condition = openstack_networking_router_v2.domain.admin_state_up == false
    error_message = "Router must remain down."
  }
}
