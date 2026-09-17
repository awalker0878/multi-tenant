# NOT EXECUTED IN THIS RELEASE. Requires Terraform >= 1.7 and the pinned provider.
mock_provider "nutanix" {}

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
  cluster_id = "22222222-2222-4222-8222-222222222222"
  project_id = "11111111-1111-4111-8111-111111111111"
  storage_container_id = "33333333-3333-4333-8333-333333333333"
  image_id = "44444444-4444-4444-8444-444444444444"
  subnet_id = "55555555-5555-4555-8555-555555555555"
  security_category_id = "66666666-6666-4666-8666-666666666666"
  ipv4_address = "192.0.2.10"
}

run "quarantine_configuration" {
  command = plan
  assert {
    condition = output.delivery_state == "PREPARED_NOT_QUALIFIED_NOT_SERVICE_READY"
    error_message = "A module must not label preparation as service readiness."
  }
  assert {
    condition = nutanix_virtual_machine_v2.workload.power_state == "OFF"
    error_message = "VM should request OFF."
  }
  assert {
    condition = nutanix_virtual_machine_v2.workload.nics[0].nic_backing_info[0].virtual_ethernet_nic[0].is_connected == false
    error_message = "NIC must stay disconnected."
  }
}
