mock_provider "openstack" {}

variables {
  allow_restricted_build = true
  tenant_key = "tenant-01"
  test_authorization_ref = "MOCK-ONLY-NO-REAL-AUTHORITY"
  wsd_key = "wsd-01"
  environment_key = "qualification-01"
  site_key = "site-01"
  members = {"D01O": {"ipv4_cidr": "192.0.2.0/27", "gateway_host_number": 1, "project_id": "11111111-1111-4111-8111-111111111111"}}
}

run "restricted_composition" {
  command = plan
  assert {
    condition = length(output.members) == 1 && output.scope.wsd_key == "wsd-01"
    error_message = "Stable owned members and WSD identity must be published."
  }
  assert {
    condition = output.delivery_state == "PREPARED_NOT_QUALIFIED_NOT_SERVICE_READY"
    error_message = "Preparation must never imply activation."
  }
}

run "empty_scope_rejected" {
  command = plan
  variables { members = {} }
  expect_failures = [var.members]
}
