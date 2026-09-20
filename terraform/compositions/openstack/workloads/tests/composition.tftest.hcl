mock_provider "openstack" {}

variables {
  allow_restricted_build = true
  tenant_key = "tenant-01"
  test_authorization_ref = "MOCK-ONLY-NO-REAL-AUTHORITY"
  wsd_key = "wsd-01"
  environment_key = "qualification-01"
  site_key = "site-01"
  members = {"processor-01": {"domain_key": "D01O", "boot_disk_gib": 40, "data_disk_gib": 0, "accepted_quarantine_ref": "MOCK-ONLY-NOT-ACCEPTED", "network_id": "77777777-7777-4777-8777-777777777777", "subnet_id": "55555555-5555-4555-8555-555555555555", "security_group_id": "88888888-8888-4888-8888-888888888888", "ipv4_address": "192.0.2.10", "image_id": "44444444-4444-4444-8444-444444444444", "flavor_id": "mock-flavor", "compute_availability_zone": "mock-compute", "storage_availability_zone": "mock-storage", "volume_type": "mock-type"}}
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
