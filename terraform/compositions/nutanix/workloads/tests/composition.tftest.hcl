mock_provider "nutanix" {}

variables {
  allow_restricted_build = true
  tenant_key = "tenant-01"
  test_authorization_ref = "MOCK-ONLY-NO-REAL-AUTHORITY"
  wsd_key = "wsd-01"
  environment_key = "qualification-01"
  site_key = "site-01"
  members = {"processor-01": {"domain_key": "D01O", "vcpu": 2, "memory_gib": 4, "boot_disk_gib": 40, "data_disk_gib": 0, "accepted_quarantine_ref": "MOCK-ONLY-NOT-ACCEPTED", "cluster_id": "22222222-2222-4222-8222-222222222222", "project_id": "11111111-1111-4111-8111-111111111111", "storage_container_id": "33333333-3333-4333-8333-333333333333", "image_id": "44444444-4444-4444-8444-444444444444", "subnet_id": "55555555-5555-4555-8555-555555555555", "security_category_id": "66666666-6666-4666-8666-666666666666", "ipv4_address": "192.0.2.10"}}
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
