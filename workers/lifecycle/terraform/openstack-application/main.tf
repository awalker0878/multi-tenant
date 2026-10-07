terraform {
  required_version = ">= 1.8.0, < 2.0.0"
  required_providers {
    openstack = {
      source = "terraform-provider-openstack/openstack"
    }
  }
}

# The commissioning root pins the exact Terraform/provider builds and dependency
# lock. This child module selects no installation, backend, credentials or version.
locals {
  ownership = {
    product_tenant_id   = var.tenant_id
    product_resource_id = var.resource_id
  }
  ports = merge([
    for workload_key, workload in var.workloads : {
      for nic_key, nic in workload.nics : "${workload_key}/${nic_key}" => merge(nic, {
        workload_key = workload_key
        nic_key      = nic_key
      })
    }
  ]...)
}

resource "openstack_networking_port_v2" "quarantine" {
  for_each              = local.ports
  name                  = "${var.resource_id}/${each.key}"
  description           = "product:${var.tenant_id}:${var.resource_id}"
  tenant_id             = var.project_id
  network_id            = each.value.network_id
  admin_state_up        = false
  port_security_enabled = true
  security_group_ids    = each.value.security_group_ids
  fixed_ip {
    subnet_id  = each.value.subnet_id
    ip_address = each.value.ip_address
  }
}

resource "openstack_blockstorage_volume_v3" "root" {
  for_each          = var.workloads
  name              = "${var.resource_id}/${each.key}/root"
  image_id          = each.value.image_id
  size              = each.value.root_size_gb
  volume_type       = each.value.volume_type
  availability_zone = each.value.volume_availability_zone
  metadata          = local.ownership
  lifecycle {
    prevent_destroy = true
  }
}

resource "openstack_compute_instance_v2" "application" {
  for_each          = var.workloads
  name              = each.value.name
  flavor_id         = each.value.flavor_id
  key_pair          = each.value.key_pair
  availability_zone = each.value.compute_availability_zone
  metadata          = local.ownership
  config_drive      = true
  force_delete      = false
  block_device {
    uuid                  = openstack_blockstorage_volume_v3.root[each.key].id
    source_type           = "volume"
    destination_type      = "volume"
    boot_index            = 0
    delete_on_termination = false
  }
  dynamic "network" {
    for_each = each.value.nics
    content {
      port = openstack_networking_port_v2.quarantine["${each.key}/${network.key}"].id
    }
  }
}
