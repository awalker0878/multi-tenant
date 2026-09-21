# Plan-only provider mocks; no native Flow enforcement qualification.
mock_provider "nutanix" {}

variables {
  tenant_key = "tenant-01"
  domain_key = "D01O"
  allow_restricted_build = true
  test_authorization_ref = "MOCK-ONLY-NO-REAL-AUTHORITY"
  ipv4_cidr = "192.0.2.0/27"
  gateway_host_number = 1
}

run "scoped_service_bootstrap" {
  command = plan
  variables {
    lifecycle_stage = "bootstrap"
    bootstrap_acceptance_ref = "MOCK-NATIVE-BOUNDARY"
    bootstrap_rules = {
      dns = { direction = "egress", protocol = "udp", port = 53, remote_ipv4 = "192.0.2.130" }
      ssh = { direction = "ingress", protocol = "tcp", port = 22, remote_ipv4 = "192.0.2.131" }
    }
  }
  assert {
    condition = length(nutanix_network_security_policy_v2.quarantine.rules) == 4 && nutanix_network_security_policy_v2.quarantine.rules[0].spec[0].application_rule_spec[0].src_allow_spec == "NONE" && nutanix_network_security_policy_v2.quarantine.rules[1].spec[0].intra_entity_group_rule_spec[0].secured_group_action == "DENY"
    error_message = "Existing deny rules must remain ahead of the service entries."
  }
  assert {
    condition = nutanix_network_security_policy_v2.quarantine.rules[2].spec[0].application_rule_spec[0].dest_subnet[0].value == "192.0.2.130" && nutanix_network_security_policy_v2.quarantine.rules[2].spec[0].application_rule_spec[0].dest_subnet[0].prefix_length == 32 && nutanix_network_security_policy_v2.quarantine.rules[2].spec[0].application_rule_spec[0].udp_services[0].start_port == 53 && nutanix_network_security_policy_v2.quarantine.rules[2].spec[0].application_rule_spec[0].udp_services[0].end_port == 53
    error_message = "DNS must retain its exact peer and single UDP port."
  }
  assert {
    condition = nutanix_network_security_policy_v2.quarantine.rules[3].spec[0].application_rule_spec[0].src_subnet[0].value == "192.0.2.131" && nutanix_network_security_policy_v2.quarantine.rules[3].spec[0].application_rule_spec[0].tcp_services[0].start_port == 22 && nutanix_network_security_policy_v2.quarantine.rules[3].spec[0].application_rule_spec[0].is_all_protocol_allowed == false && output.lifecycle_stage == "bootstrap"
    error_message = "SSH must be an exact incoming service with no all-protocol expansion."
  }
}

run "withdraw_keeps_only_denies" {
  command = plan
  variables {
    lifecycle_stage = "prepared"
    bootstrap_rules = { ssh = { direction = "ingress", protocol = "tcp", port = 22, remote_ipv4 = "192.0.2.131" } }
  }
  assert {
    condition = length(nutanix_network_security_policy_v2.quarantine.rules) == 2 && nutanix_network_security_policy_v2.quarantine.state == "ENFORCE" && nutanix_network_security_policy_v2.quarantine.is_ipv6_traffic_allowed == false
    error_message = "Withdrawal must remove exceptions and retain the enforced deny boundary."
  }
}

run "bootstrap_needs_acceptance" {
  command = plan
  variables { lifecycle_stage = "bootstrap" }
  expect_failures = [nutanix_network_security_policy_v2.quarantine]
}

run "quarantine_configuration" {
  command = plan
  assert {
    condition = output.delivery_state == "PREPARED_NOT_QUALIFIED_NOT_SERVICE_READY"
    error_message = "A module must not label preparation as service readiness."
  }
  assert {
    condition = nutanix_vpc_v2.domain.vpc_type == "REGULAR"
    error_message = "VPC must not become transit."
  }
  assert {
    condition = nutanix_subnet_v2.domain.is_external == false
    error_message = "Domain subnet must not become external."
  }
  assert {
    condition = nutanix_network_security_policy_v2.quarantine.state == "ENFORCE"
    error_message = "A saved policy is not quarantine."
  }
}
