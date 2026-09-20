mock_provider "vsphere" {}

variables {
  allow_restricted_build = true
  tenant_key = "tenant-01"
  test_authorization_ref = "MOCK-ONLY-NO-REAL-AUTHORITY"
  wsd_key = "wsd-01"
  members = {"processor-01": {"domain_key": "D01O", "vcpu": 2, "memory_gib": 4, "boot_disk_gib": 40, "data_disk_gib": 0, "accepted_quarantine_ref": "MOCK-ONLY-NOT-ACCEPTED", "resource_pool_id": "resgroup-mock", "datastore_id": "datastore-mock", "quarantine_network_id": "network-mock", "template_uuid": "99999999-9999-4999-8999-999999999999", "guest_id": "otherLinux64Guest", "scsi_type": "pvscsi", "firmware": "efi", "storage_policy_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"}}
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
