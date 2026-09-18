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
