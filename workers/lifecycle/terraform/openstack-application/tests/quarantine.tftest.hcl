mock_provider "openstack" {}

run "quarantined_multi_workload_plan" {
  command = plan
  variables {
    tenant_id   = "00000000-0000-4000-8000-000000000001"
    resource_id = "00000000-0000-4000-8000-000000000002"
    project_id  = "00000000000040008000000000000003"
    workloads = {
      web = {
        name                      = "synthetic-web"
        image_id                  = "00000000-0000-4000-8000-000000000004"
        flavor_id                 = "small"
        volume_type               = "synthetic-encrypted"
        root_size_gb              = 10
        compute_availability_zone = "compute-a"
        volume_availability_zone  = "storage-b"
        key_pair                  = "synthetic-key"
        nics = {
          application = {
            network_id         = "00000000-0000-4000-8000-000000000005"
            subnet_id          = "00000000-0000-4000-8000-000000000006"
            ip_address         = "192.0.2.8"
            security_group_ids = ["00000000-0000-4000-8000-000000000007"]
          }
          management = {
            network_id         = "00000000-0000-4000-8000-000000000008"
            subnet_id          = "00000000-0000-4000-8000-000000000009"
            ip_address         = "2001:db8::8"
            security_group_ids = ["00000000-0000-4000-8000-000000000010"]
          }
        }
      }
      database = {
        name                      = "synthetic-database"
        image_id                  = "00000000-0000-4000-8000-000000000004"
        flavor_id                 = "large"
        volume_type               = "synthetic-encrypted"
        root_size_gb              = 20
        compute_availability_zone = "compute-a"
        volume_availability_zone  = "storage-b"
        key_pair                  = "synthetic-key"
        nics = {
          application = {
            network_id         = "00000000-0000-4000-8000-000000000005"
            subnet_id          = "00000000-0000-4000-8000-000000000006"
            ip_address         = "192.0.2.9"
            security_group_ids = ["00000000-0000-4000-8000-000000000007"]
          }
        }
      }
    }
  }
  assert {
    condition = (
      length(openstack_networking_port_v2.quarantine) == 3 &&
      alltrue([for p in openstack_networking_port_v2.quarantine : (
        !p.admin_state_up && p.port_security_enabled && length(p.security_group_ids) > 0
      )])
    )
    error_message = "Every explicit NIC must remain disabled and protected."
  }
  assert {
    condition = (
      length(openstack_compute_instance_v2.application) == 2 &&
      alltrue([for s in openstack_compute_instance_v2.application : (
        s.config_drive && !s.force_delete &&
        alltrue([for d in s.block_device : !d.delete_on_termination])
      )])
    )
    error_message = "Instances must retain their boot volumes and avoid forced deletion."
  }
  assert {
    condition = (
      openstack_compute_instance_v2.application["web"].availability_zone == "compute-a" &&
      openstack_blockstorage_volume_v3.root["web"].availability_zone == "storage-b"
    )
    error_message = "Compute and storage placement must use their independent discovered inputs."
  }
}
