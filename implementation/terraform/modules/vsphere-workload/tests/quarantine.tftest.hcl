# NOT EXECUTED IN THIS RELEASE. Requires Terraform >= 1.7 and the pinned provider.
mock_provider "vsphere" {}

variables {
  tenant_key = "tenant-01"
  domain_key = "D01O"
  allow_restricted_build = true
  test_authorization_ref = "MOCK-ONLY-NO-REAL-AUTHORITY"
  workload_key = "processor-01"
  vcpu = 2
  memory_gib = 4
  boot_disk_gib = 40
  data_disk_gib = 0
  accepted_quarantine_ref = "MOCK-ONLY-NOT-ACCEPTED"
  resource_pool_id = "resgroup-mock"
  datastore_id = "datastore-mock"
  quarantine_network_id = "network-mock"
  template_uuid = "99999999-9999-4999-8999-999999999999"
  guest_id = "otherLinux64Guest"
  scsi_type = "pvscsi"
  firmware = "efi"
  storage_policy_id = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
}

run "quarantine_configuration" {
  command = plan
  assert {
    condition = output.delivery_state == "PREPARED_NOT_QUALIFIED_NOT_SERVICE_READY"
    error_message = "A module must not label preparation as service readiness."
  }
  assert {
    condition = vsphere_virtual_machine.workload.network_interface[0].network_id == var.quarantine_network_id
    error_message = "VM network must match the reviewed mapping."
  }
  assert {
    condition = vsphere_virtual_machine.workload.disk[0].keep_on_remove == true
    error_message = "Disk retention must remain enabled."
  }
}
