# Plan-only provider mocks; actual native execution needs separate qualification.
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

run "restricted_bootstrap_power_and_port" {
  command = plan
  variables {
    lifecycle_stage = "bootstrap"
    bootstrap_acceptance_ref = "MOCK-ONLY-NOT-ACCEPTED"
    config_drive = true
  }
  assert {
    condition = openstack_compute_instance_v2.workload.power_state == "active" && openstack_networking_port_v2.workload.admin_state_up && openstack_networking_port_v2.workload.port_security_enabled
    error_message = "Explicit bootstrap powers and connects only the guarded owned workload."
  }
  assert {
    condition = openstack_compute_instance_v2.workload.block_device[0].delete_on_termination == false && length(openstack_networking_port_v2.workload.security_group_ids) == 1
    error_message = "Bootstrap must retain data and the single mandatory group."
  }
}

run "bootstrap_without_acceptance_rejected" {
  command = plan
  variables {
    lifecycle_stage = "bootstrap"
    config_drive = true
  }
  # Terraform stops traversal at these failed dependencies; the server is not evaluated.
  expect_failures = [openstack_networking_port_v2.workload, openstack_blockstorage_volume_v3.boot]
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
