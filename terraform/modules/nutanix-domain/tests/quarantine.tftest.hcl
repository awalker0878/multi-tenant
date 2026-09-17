# NOT EXECUTED IN THIS RELEASE. Requires Terraform >= 1.7 and the pinned provider.
mock_provider "nutanix" {}

variables {
  tenant_key = "tenant-01"
  domain_key = "D01O"
  allow_restricted_build = true
  test_authorization_ref = "MOCK-ONLY-NO-REAL-AUTHORITY"
  ipv4_cidr = "192.0.2.0/27"
  gateway_host_number = 1
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
