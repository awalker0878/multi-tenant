output "server_ids" {
  value = { for key, server in openstack_compute_instance_v2.application : key => server.id }
}

output "port_ids" {
  value = { for key, port in openstack_networking_port_v2.quarantine : key => port.id }
}

output "retained_volume_ids" {
  value = { for key, volume in openstack_blockstorage_volume_v3.root : key => volume.id }
}
