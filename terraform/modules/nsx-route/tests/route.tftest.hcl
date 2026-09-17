mock_provider "nsxt" {}

run "restricted_route_plan" {
  command = plan
  variables {
    tenant_key = "tenant-01"
    domain_key = "D01O"
    allow_restricted_build = true
    test_authorization_ref = "MOCK-test_authorization_ref"
    engineering_record_ref = "MOCK-engineering_record_ref"
    attachment_acceptance_ref = "MOCK-attachment_acceptance_ref"
    route_key = "route-dns"
    destination_cidr = "203.0.113.138/32"
    gateway_path = "/infra/tier-0s/mock-isolated"
    next_hop_address = "198.51.100.1"
  }
  assert {
    condition = output.destination_cidr == "203.0.113.138/32"
    error_message = "Destination changed during native planning."
  }
}
