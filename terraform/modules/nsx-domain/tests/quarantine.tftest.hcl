# NOT EXECUTED IN THIS RELEASE. Requires Terraform >= 1.7 and the pinned provider.
mock_provider "nsxt" {}

variables {
  tenant_key = "tenant-01"
  domain_key = "D01O"
  allow_restricted_build = true
  test_authorization_ref = "MOCK-ONLY-NO-REAL-AUTHORITY"
  ipv4_cidr = "192.0.2.0/27"
  gateway_host_number = 1
  transport_zone_path = "/infra/sites/default/enforcement-points/default/transport-zones/mock"
  quarantine_sequence = 100
}

run "bootstrap_exact_service_then_terminal_drop" {
  command = plan
  variables {
    lifecycle_stage = "bootstrap"
    bootstrap_acceptance_ref = "MOCK-ONLY-NOT-ACCEPTED"
    bootstrap_rules = {
      dns = { direction = "egress", protocol = "udp", port = 53, remote_ipv4 = "10.42.0.53" }
      ssh = { direction = "ingress", protocol = "tcp", port = 22, remote_ipv4 = "10.42.0.22" }
    }
  }
  assert {
    condition = nsxt_policy_segment.domain.advanced_config[0].connectivity == "ON" && length(nsxt_policy_security_policy.quarantine.rule) == 3
    error_message = "Bootstrap must connect only the owned segment and add exact service rules."
  }
  assert {
    condition = nsxt_policy_security_policy.quarantine.rule[0].action == "ALLOW" && nsxt_policy_security_policy.quarantine.rule[2].action == "DROP" && nsxt_policy_security_policy.quarantine.rule[2].ip_version == "IPV4_IPV6"
    error_message = "The terminal dual-family drop must follow all reviewed exceptions."
  }
  assert {
    condition = one(nsxt_policy_security_policy.quarantine.rule[0].destination_groups) == "10.42.0.53/32" && one(one(one(nsxt_policy_security_policy.quarantine.rule[0].service_entries).l4_port_set_entry).destination_ports) == "53"
    error_message = "A service rule must contain one exact peer and port."
  }
}

run "withdraw_retains_inputs_but_removes_exceptions" {
  command = plan
  variables {
    lifecycle_stage = "prepared"
    bootstrap_rules = { dns = { direction = "egress", protocol = "udp", port = 53, remote_ipv4 = "10.42.0.53" } }
  }
  assert {
    condition = length(nsxt_policy_security_policy.quarantine.rule) == 1 && nsxt_policy_security_policy.quarantine.rule[0].action == "DROP" && nsxt_policy_segment.domain.advanced_config[0].connectivity == "OFF"
    error_message = "Withdrawal must restore sole deny and disconnect the segment."
  }
}

run "unaccepted_bootstrap_rejected" {
  command = plan
  variables { lifecycle_stage = "bootstrap" }
  expect_failures = [nsxt_policy_tier1_gateway.domain]
}

run "quarantine_configuration" {
  command = plan
  assert {
    condition = output.delivery_state == "PREPARED_NOT_QUALIFIED_NOT_SERVICE_READY"
    error_message = "A module must not label preparation as service readiness."
  }
  assert {
    condition = nsxt_policy_tier1_gateway.domain.ha_mode == "NONE"
    error_message = "This increment has no service-router or external attachment."
  }
  assert {
    condition = nsxt_policy_segment.domain.advanced_config[0].connectivity == "OFF"
    error_message = "Segment must stay disconnected."
  }
  assert {
    condition = nsxt_policy_security_policy.quarantine.rule[0].action == "DROP"
    error_message = "Quarantine must not permit user traffic."
  }
}
