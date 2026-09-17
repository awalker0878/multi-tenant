# NOT EXECUTED IN THIS RELEASE. Requires Terraform >= 1.7 and the pinned provider.
mock_provider "openstack" {}

variables {
  tenant_key = "tenant-01"
  domain_key = "D01O"
  allow_restricted_build = true
  test_authorization_ref = "MOCK-ONLY-NO-REAL-AUTHORITY"
  workload_key = "processor-01"
  boot_disk_gib = 40
  data_disk_gib = 0
  accepted_quarantine_ref = "MOCK-ONLY-NOT-ACCEPTED"
  network_id = "77777777-7777-4777-8777-777777777777"
  subnet_id = "55555555-5555-4555-8555-555555555555"
  security_group_id = "88888888-8888-4888-8888-888888888888"
  ipv4_address = "192.0.2.10"
  image_id = "44444444-4444-4444-8444-444444444444"
  flavor_id = "mock-flavor"
  compute_availability_zone = "mock-compute"
  storage_availability_zone = "mock-storage"
  volume_type = "mock-type"
}

run "quarantine_configuration" {
  command = plan
  assert {
    condition = output.delivery_state == "PREPARED_NOT_QUALIFIED_NOT_SERVICE_READY"
    error_message = "A module must not label preparation as service readiness."
  }
  assert {
    condition = openstack_networking_port_v2.workload.admin_state_up == false
    error_message = "Port must remain down during initial boot."
  }
  assert {
    condition = openstack_compute_instance_v2.workload.block_device[0].delete_on_termination == false
    error_message = "Boot volume must not be deleted with server."
  }
}
