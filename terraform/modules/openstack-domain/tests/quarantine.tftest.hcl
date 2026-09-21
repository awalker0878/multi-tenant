# Plan-only provider mocks; actual native execution needs separate qualification.
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

run "restricted_bootstrap_paths" {
  command = plan
  variables {
    lifecycle_stage = "bootstrap"
    bootstrap_acceptance_ref = "MOCK-ONLY-NOT-ACCEPTED"
    bootstrap_rules = {
      resolver = { direction = "egress", protocol = "udp", port = 53, remote_ipv4 = "192.0.2.130" }
      operator = { direction = "ingress", protocol = "tcp", port = 22, remote_ipv4 = "192.0.2.140" }
    }
  }
  assert {
    condition = openstack_networking_network_v2.domain.admin_state_up && openstack_networking_router_v2.domain.admin_state_up
    error_message = "Explicit bootstrap enables the owned network and router."
  }
  assert {
    condition = length(openstack_networking_secgroup_rule_v2.bootstrap) == 2 && openstack_networking_secgroup_rule_v2.bootstrap["resolver"].remote_ip_prefix == "192.0.2.130/32" && openstack_networking_secgroup_rule_v2.bootstrap["resolver"].port_range_min == 53 && openstack_networking_secgroup_rule_v2.bootstrap["resolver"].port_range_max == 53
    error_message = "Bootstrap rules must preserve exact endpoint and port scope."
  }
}

run "withdraw_preserves_data_and_rules" {
  command = plan
  variables {
    lifecycle_stage = "prepared"
    bootstrap_acceptance_ref = "MOCK-ONLY-NOT-ACCEPTED"
    bootstrap_rules = { resolver = { direction = "egress", protocol = "udp", port = 53, remote_ipv4 = "192.0.2.130" } }
  }
  assert {
    condition = !openstack_networking_network_v2.domain.admin_state_up && !openstack_networking_router_v2.domain.admin_state_up && length(openstack_networking_secgroup_rule_v2.bootstrap) == 1
    error_message = "Withdrawal disables links without deleting owned rule identities."
  }
}

run "broad_bootstrap_rule_rejected" {
  command = plan
  variables {
    bootstrap_rules = { unsafe = { direction = "egress", protocol = "tcp", port = 443, remote_ipv4 = "0.0.0.0/0" } }
  }
  expect_failures = [var.bootstrap_rules]
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
