# VMware ↔ Nutanix AHV ↔ OpenStack — migration field crosswalk

**Full data mapping:** [`contracts/capabilities/migration-field-crosswalk-v1.json`](../../contracts/capabilities/migration-field-crosswalk-v1.json)  
**Source of field provenance:** [`migration-collection-manifest-v1.json`](../../contracts/capabilities/migration-collection-manifest-v1.json)  
**Validator:** [`scripts/assurance/validate_migration_field_crosswalk.py`](../../scripts/assurance/validate_migration_field_crosswalk.py)

The crosswalk currently covers **278 manifest attributes** in **116 canonical groups**:
59 groups have entries for all three platforms, 57 have a missing platform
entry, and 45 are explicitly platform-specific (only one platform supplies a
field). The **27 shared operator/independent obligations** appear across the
three platforms; matching names here do not make their evidence interchangeable.

## Mapping rules

The statuses in the crosswalk are **declared, not qualified**. A field
reference is evidence-location metadata and does not mean an installation's
API exposes it, that the caller is entitled, or that the operation is
migration-safe. Null means *no safe direct field-level mapping* in this
manifest, **not** that the destination is unsupported. The correct result
without installed and qualified evidence is `unknown`.

- **normalize:** clearly specified transformations for representation
  differences (power state, byte/MiB/GiB units, total CPU count, MAC).
  Transformations remain proposals until exact API versions are exercised.
- **conditional:** semantically related but non-interchangeable values.
  Disk backing, network security, firmware/guest settings, source identity,
  image capture and VM provisioning require independently qualified
  target translations and application/security validation.
- **platform_specific:** no established cross-platform field equivalent;
  treat its loss or need for an adapter according to criticality and
  conditional applicability. A missing critical field must remain a hold.
- **owner_common:** independently witnessed or operator-approved facts,
  including application consistency, writer fencing, RPO/RTO, isolation,
  backup, rollback, license and physical resource reservations. The
  exact source/target scope and expiry must be rechecked.

**Never copy** native VM/disk/controller/project/network IDs between
installations. Required network paths, firewall policy semantics and
tenant isolation cannot be downgraded to optional by the crosswalk.
Qualitative Placement traits, datastore freeSpace, AHV maxCapacityBytes
and independent physical reservation are distinct sources of information.
A migration is authorized only by the existing owner/Assurance/Planning/
Lifecycle gates, never this data file.

## Selected transformations and semantic boundaries

| Canonical meaning | VMware | Nutanix AHV | OpenStack | Safety rule |
| --- | --- | --- | --- | --- |
| Power state | `poweredOn/off` | `ON/OFF` | `ACTIVE/SHUTOFF` | Normalize carefully; hold transitional states |
| Total vCPUs | `numCPU` | Sockets × cores/socket × threads/core | Flavor `vcpus` | Validate target guest CPU topology |
| RAM in MiB | `memoryMB` | `memorySizeBytes / 1048576` | Flavor `ram` | Exact bytes-to-MiB conversion |
| Disk size in bytes | `capacityInBytes` | `diskSizeBytes` | Cinder volume GiB or flavor local disk GiB | Keep local root, Cinder and ephemeral separate |
| NIC MAC | Virtual NIC `macAddress` | NIC backing `macAddress` | Neutron port `mac_address` | Check uniqueness and preservation authority |
| Firmware | BIOS/EFI config | Prism `bootConfig` types | Nova firmware metadata | Metadata ≠ independent guest/boot proof |
| VM/source identity | vCenter+VM identity | Prism cluster+VM generation | Nova tenant+server+created | Never conflate created time with incarnation UUID |
| Disk source capture | VI/JSON and NFC lease | Prism v4 image capture/task | Nova/Glance/Cinder image and volume workflows | Different adapter and disk-consistency proofs |
| Firewall/security | Platform policy and owner tests | Nutanix Microseg | Neutron security-group/rule semantics | Verify required allows **and** denies |
| Storage capacity | Datastore freeSpace | Container maxCapacityBytes | Placement resource inventories/allocations | No inferred common free capacity; separate held reservation |
| Import and VM creation | ImportVApp/OVF/NFC | Prism image + VM tasks | Glance image + Nova VM | Per-platform qualified operation required |

## Complete source-field mapping

The tables below deliberately show **field names**, not only broad feature
categories. Multi-field mappings require the entire listed source set and
the minimum freshness of their observations. Platform-specific rows are
included so no input is silently discarded.

### Source VM observations (61 canonical groups)

| Canonical field | VMware vSphere manifest field(s) | Nutanix AHV manifest field(s) | OpenStack manifest field(s) | Relationship | Criticality · max age |
| --- | --- | --- | --- | --- | --- |
| `source.vm.id` | `identity.vm_ref` → `VirtualMachine.moId` | `identity.vm_ext_id` → `data.extId` | `identity.server_id` → `server.id` | normalize | critical · 60s |
| `source.vm.incarnation` | `identity.instance_uuid` → `VirtualMachine.config.instanceUuid` | `identity.generation_uuid` → `data.generationUuid` | `identity.instance_created` → `server.created` | conditional | critical · 60s |
| `source.vm.bios_uuid` | `identity.bios_uuid` → `VirtualMachine.config.uuid` | `identity.bios_uuid` → `data.biosUuid` | **No direct field mapping** | conditional | critical · 120s |
| `source.scope.project` | **No direct field mapping** | `identity.project` → `data.project.extId / projectExtId` | `identity.project` → `server.tenant_id` | conditional | critical · 60s |
| `source.vm.host` | `identity.host` → `VirtualMachine.runtime.host` | `identity.host` → `data.host.extId` | **No direct field mapping** | conditional | critical · 60s |
| `source.platform.release` | `identity.vcenter_version` → `ServiceInstance.content.about.version`; `identity.vcenter_build` → `ServiceInstance.content.about.build` | `identity.prism_version` → `config.buildInfo`; `identity.aos_version` → `config.buildInfo + clusterSoftwareMap` | `identity.installed_product` → `owner: distribution_and_backend_release` | conditional | critical · 3600s |
| `source.api.releases` | `identity.api_release` → `ServiceInstance.content.about.apiVersion + enrolled VI/JSON release` | `identity.namespace_version` → `owner: v4_namespace_entitlements_and_installed_bounds` | `identity.compute_microversion` → `GET versions + OpenStack-API-Version compute 2.1`; `identity.volume_microversion` → `GET versions + OpenStack-API-Version volume 3.0`; `identity.network_api` → `GET /extensions + Networking API 2.0` | conditional | critical · 3600s |
| `source.vm.revision` | `identity.config_change_version` → `VirtualMachine.config.changeVersion` | `identity.update_time` → `data.updateTime` | **No direct field mapping** | conditional | critical · 60s |
| `source.vm.power_state` | `compute.power_state` → `VirtualMachine.runtime.powerState` | `compute.power_state` → `data.powerState` | `compute.power_state` → `server.status` | normalize | critical · 10s |
| `source.vm.vcpu_total` | `compute.cpu_count` → `VirtualMachine.config.hardware.numCPU` | `compute.sockets` → `data.numSockets`; `compute.cores_per_socket` → `data.numCoresPerSocket`; `compute.threads_per_core` → `data.numThreadsPerCore` | `compute.vcpus` → `flavor.vcpus` | normalize | critical · 120s |
| `source.vm.memory_mib` | `compute.memory_mib` → `VirtualMachine.config.hardware.memoryMB` | `compute.memory_bytes` → `data.memorySizeBytes` | `compute.memory_mib` → `flavor.ram` | normalize | critical · 120s |
| `source.guest.os_identity` | `guest.guest_id` → `VirtualMachine.config.guestId` | `guest.os_identity` → `owner: guest_identity_and_drivers` | `guest.os_metadata` → `server.metadata.os_distro` | conditional | critical · 300s |
| `source.guest.firmware` | `guest.firmware` → `VirtualMachine.config.firmware` | `guest.boot_mode` → `data.bootConfig.$objectType` | `guest.firmware_metadata` → `server.metadata.hw_firmware_type` | conditional | critical · 120s |
| `source.guest.secure_boot` | `guest.secure_boot` → `VirtualMachine.config.bootOptions.efiSecureBootEnabled` | `guest.secure_boot` → `data.bootConfig.isSecureBootEnabled` | **No direct field mapping** | conditional | critical · 120s |
| `source.guest.vtpm` | `guest.vtpm` → `VirtualMachine.config.hardware.device[*]._typeName=VirtualTPM` | `guest.vtpm` → `data.vtpmConfig` | **No direct field mapping** | conditional | critical · 120s |
| `source.guest.tools` | `guest.tools_status` → `VirtualMachine.guest.toolsRunningStatus`; `guest.tools_version` → `VirtualMachine.guest.toolsVersion` | `guest.tools` → `data.guestTools` | **No direct field mapping** | conditional | critical · 60s |
| `source.disks.complete` | `storage.disk_inventory` → `VirtualMachine.config.hardware.device[*]._typeName=VirtualDisk` | `storage.disk_inventory` → `data.disks[*].extId` | `storage.volume_attachments` → `GET /servers/{id}/os-volume_attachments.volumeAttachments[*].volumeId`; `storage.server_volume_refs` → `server.os-extended-volumes:volumes_attached` | conditional | critical · 60s |
| `source.disk.native_identity` | `storage.disk_identity` → `VirtualDisk.key + backing` | `storage.disk_backing_identity` → `data.disks[*].backingInfo` | `storage.volume_id` → `volume.id` | conditional | critical · 60s |
| `source.disk.capacity_bytes` | `storage.disk_size` → `VirtualDisk.capacityInBytes` | `storage.disk_capacity` → `data.disks[*].backingInfo.diskSizeBytes` | `storage.volume_size` → `volume.size`; `compute.local_disk_gib` → `flavor.disk` | conditional | critical · 120s |
| `source.disk.controller` | `storage.disk_controller` → `VirtualDisk.controllerKey + unitNumber` | `storage.disk_address` → `data.disks[*].diskAddress.index`; `storage.disk_bus` → `data.disks[*].diskAddress.busType` | `guest.boot_device` → `server.OS-EXT-SRV-ATTR:root_device_name` | conditional | critical · 120s |
| `source.disk.backing` | `storage.disk_backing_chain` → `VirtualDisk.backing.parent[*] + _typeName` | `storage.disk_backing_type` → `data.disks[*].backingInfo.$objectType`; `storage.storage_config` → `data.storageConfig` | `storage.volume_type` → `volume.volume_type`; `storage.volume_image_metadata` → `volume.volume_image_metadata` | conditional | critical · 60s |
| `source.disk.sharing` | `storage.disk_sharing` → `VirtualDisk.backing.sharing + controller.sharedBus` | `storage.shared_external` → `data.disks[*].backingInfo.$objectType + owner_mapping` | `storage.multiattach` → `volume.multiattach`; `storage.attachments` → `volume.attachments[*].server_id` | conditional | critical · 60s |
| `source.disk.encryption` | `storage.disk_encryption` → `VirtualDisk.backing.keyId + VirtualMachine.config.keyId` | `storage.encryption` → `owner: storage_encryption_and_key_custody` | `storage.encrypted` → `volume.encrypted` | conditional | critical · 60s |
| `source.disk.capture_method` | `storage.nfc_export` → `VirtualMachine.ExportVm + HttpNfcLease.info.deviceUrl` | `storage.image_capture` → `POST images + task status + source disk readback` | `storage.local_image_capture` → `POST createImage + Glance readback`; `storage.volume_snapshot_capture` → `POST snapshots + clone + volume-to-image readback` | conditional | critical · 300s |
| `source.nic.inventory` | `network.nic_inventory` → `VirtualMachine.config.hardware.device[*].macAddress` | `network.nic_inventory` → `data.nics[*].extId` | `network.port_ids` → `ports[*].id`; `network.ports_complete` → `GET ports?device_id={id}&project_id={project} + ports_links` | conditional | critical · 60s |
| `source.nic.guest_model` | `network.nic_model` → `VirtualEthernetCard._typeName` | `network.nic_model` → `data.nics[*].backingInfo.model` | `network.nic_model` → `ports[*].binding:vnic_type` | conditional | critical · 120s |
| `source.nic.mac` | `network.nic_mac` → `VirtualEthernetCard.macAddress` | `network.nic_mac` → `data.nics[*].backingInfo.macAddress` | `network.nic_mac` → `ports[*].mac_address` | normalize | critical · 60s |
| `source.nic.connected` | `network.nic_connection` → `VirtualEthernetCard.connectable.connected + startConnected` | `network.nic_connection` → `data.nics[*].backingInfo.isConnected` | `network.port_status` → `ports[*].status + admin_state_up` | conditional | critical · 30s |
| `source.nic.attachment` | `network.nic_backing` → `VirtualEthernetCard.backing` | `network.nic_backing` → `data.nics[*].backingInfo` | `network.port_network` → `ports[*].network_id`; `network.fixed_ips` → `ports[*].fixed_ips` | conditional | critical · 60s |
| `source.nic.security` | **No direct field mapping** | **No direct field mapping** | `network.security_groups` → `ports[*].security_groups`; `network.port_security` → `ports[*].port_security_enabled`; `network.declared_security_groups` → `server.security_groups` | platform_specific | critical · 60s |
| `source.passthrough` | `compute.passthrough_devices` → `VirtualMachine.config.hardware.device[*]._typeName` | `compute.gpu_passthrough` → `data.gpus[*] + data.pcieDevices[*]` | **No direct field mapping** | conditional | critical · 120s |
| `source.vm.display_name` | `identity.display_name` → `VirtualMachine.config.name` | `identity.display_name` → `data.name` | **No direct field mapping** | conditional | optional · 300s |
| `source.vm.creation_time` | `identity.create_date` → `VirtualMachine.config.createDate` | `identity.create_time` → `data.createTime` | **No direct field mapping** | conditional | optional · 3600s |
| `source.vmware.identity.vcenter_uuid` | `identity.vcenter_uuid` → `ServiceInstance.content.about.instanceUuid` | **No direct field mapping** | **No direct field mapping** | platform_specific | critical · 3600s |
| `source.vmware.compute.hardware_version` | `compute.hardware_version` → `VirtualMachine.config.version` | **No direct field mapping** | **No direct field mapping** | platform_specific | critical · 3600s |
| `source.vmware.compute.cpu_hot_add` | `compute.cpu_hot_add` → `VirtualMachine.config.cpuHotAddEnabled` | **No direct field mapping** | **No direct field mapping** | platform_specific | optional · 120s |
| `source.vmware.compute.memory_hot_add` | `compute.memory_hot_add` → `VirtualMachine.config.memoryHotAddEnabled` | **No direct field mapping** | **No direct field mapping** | platform_specific | optional · 120s |
| `source.vmware.storage.disk_mode` | `storage.disk_mode` → `VirtualDisk.backing.diskMode` | **No direct field mapping** | **No direct field mapping** | platform_specific | critical · 60s |
| `source.vmware.storage.datastore` | `storage.datastore` → `VirtualDisk.backing.datastore` | **No direct field mapping** | **No direct field mapping** | platform_specific | critical · 60s |
| `source.vmware.storage.snapshots` | `storage.snapshots` → `VirtualMachine.snapshot` | **No direct field mapping** | **No direct field mapping** | platform_specific | critical · 60s |
| `source.vmware.storage.snapshot_supported` | `storage.snapshot_supported` → `VirtualMachine.capability.snapshotConfigSupported` | **No direct field mapping** | **No direct field mapping** | platform_specific | critical · 300s |
| `source.vmware.storage.clone_from_snapshot` | `storage.clone_from_snapshot` → `HostSystem.capability.cloneFromSnapshotSupported` | **No direct field mapping** | **No direct field mapping** | platform_specific | critical · 300s |
| `source.vmware.network.nic_guest_control` | `network.nic_guest_control` → `VirtualEthernetCard.connectable.allowGuestControl` | **No direct field mapping** | **No direct field mapping** | platform_specific | critical · 120s |
| `source.vmware.storage.ovf_descriptor` | `storage.ovf_descriptor` → `OvfManager.CreateDescriptor + import spec` | **No direct field mapping** | **No direct field mapping** | platform_specific | critical · 3600s |
| `source.ahv.identity.cluster` | **No direct field mapping** | `identity.cluster` → `data.cluster.extId` | **No direct field mapping** | platform_specific | critical · 60s |
| `source.ahv.network.nic_subnet` | **No direct field mapping** | `network.nic_subnet` → `data.nics[*].networkInfo.subnet.extId` | **No direct field mapping** | platform_specific | critical · 60s |
| `source.ahv.compute.cdrom` | **No direct field mapping** | `compute.cdrom` → `data.cdRoms[*]` | **No direct field mapping** | platform_specific | optional · 300s |
| `source.ahv.identity.categories` | **No direct field mapping** | `identity.categories` → `data.categories` | **No direct field mapping** | platform_specific | optional · 3600s |
| `source.openstack.compute.flavor_id` | **No direct field mapping** | **No direct field mapping** | `compute.flavor_id` → `server.flavor.id` | platform_specific | critical · 120s |
| `source.openstack.compute.swap_and_ephemeral` | **No direct field mapping** | **No direct field mapping** | `compute.swap_and_ephemeral` → `flavor.swap + OS-FLV-EXT-DATA:ephemeral` | platform_specific | critical · 120s |
| `source.openstack.compute.availability_zone` | **No direct field mapping** | **No direct field mapping** | `compute.availability_zone` → `server.OS-EXT-AZ:availability_zone` | platform_specific | critical · 120s |
| `source.openstack.guest.image_id` | **No direct field mapping** | **No direct field mapping** | `guest.image_id` → `server.image.id` | platform_specific | critical · 120s |
| `source.openstack.guest.config_drive` | **No direct field mapping** | **No direct field mapping** | `guest.config_drive` → `server.config_drive` | platform_specific | critical · 120s |
| `source.openstack.guest.user_key` | **No direct field mapping** | **No direct field mapping** | `guest.user_key` → `server.key_name` | platform_specific | optional · 300s |
| `source.openstack.storage.bootable` | **No direct field mapping** | **No direct field mapping** | `storage.bootable` → `volume.bootable` | platform_specific | critical · 120s |
| `source.openstack.storage.volume_metadata` | **No direct field mapping** | **No direct field mapping** | `storage.volume_metadata` → `volume.metadata` | platform_specific | optional · 120s |
| `source.openstack.network.port_project` | **No direct field mapping** | **No direct field mapping** | `network.port_project` → `ports[*].project_id` | platform_specific | critical · 60s |
| `source.openstack.network.nic_binding` | **No direct field mapping** | **No direct field mapping** | `network.nic_binding` → `ports[*].binding:vif_type` | platform_specific | critical · 60s |
| `source.openstack.network.qos_policy` | **No direct field mapping** | **No direct field mapping** | `network.qos_policy` → `ports[*].qos_policy_id` | platform_specific | optional · 300s |
| `source.openstack.network.declared_addresses` | **No direct field mapping** | **No direct field mapping** | `network.declared_addresses` → `server.addresses` | platform_specific | critical · 60s |
| `source.openstack.guest.image_metadata` | **No direct field mapping** | **No direct field mapping** | `guest.image_metadata` → `server.metadata` | platform_specific | critical · 300s |

### Destination environment and operation prerequisites (28 canonical groups)

| Canonical field | VMware vSphere manifest field(s) | Nutanix AHV manifest field(s) | OpenStack manifest field(s) | Relationship | Criticality · max age |
| --- | --- | --- | --- | --- | --- |
| `target.api.versions` | `target.api_release` → `ServiceInstance.content.about.apiVersion + selected VI/JSON release` | `target.aos_and_ahv_versions` → `data.config.buildInfo + clusterSoftwareMap + hypervisorTypes` | `target.compute_api_bounds` → `GET versions.min_version + version`; `target.volume_api_bounds` → `GET versions.min_version + version`; `target.image_api_versions` → `GET versions` | conditional | critical · 3600s |
| `target.compute.placement` | `target.resource_pool` → `/api/vcenter/resource-pool`; `target.compute_host` → `/api/vcenter/host` | `target.cluster_identity` → `clusters/{id}.data.extId`; `target.cluster_availability` → `data.config.isAvailable` | `target.availability_zones` → `GET /os-availability-zone.availabilityZoneInfo[*].zoneState`; `target.flavors` → `GET /flavors/detail.flavors[*].vcpus + ram + disk` | conditional | critical · 30s |
| `target.compute.capacity` | `target.compute_capacity` → `ResourcePool.summary + HostSystem.summary` | **No direct field mapping** | **No direct field mapping** | platform_specific | critical · 15s |
| `target.storage.backend` | `target.datastore` → `/api/vcenter/datastore` | `target.storage_containers` → `storage-containers[*].extId + clusterExtId`; `target.storage_container_state` → `storage-containers[*].isMarkedForRemoval + isInternal` | `target.volume_types` → `GET /types.volume_types[*].extra_specs + is_public`; `target.image_stores` → `GET /v2/info/stores.stores[*]` | conditional | critical · 60s |
| `target.storage.capacity_indicators` | `target.storage_capacity` → `Datastore.summary.freeSpace` | `target.storage_capacity` → `storage-containers[*].maxCapacityBytes` | `target.placement_inventory` → `GET /resource_providers/{uuid}/inventories`; `target.provider_allocations` → `GET /allocations/{consumer_uuid}` | conditional | critical · 15s |
| `target.network.segment` | `target.network_backing` → `/api/vcenter/network` | `target.subnets` → `subnets[*].extId + subnetType + clusterReference`; `target.vpc_mapping` → `vpcs[*].extId + projectExtId`; `target.ip_configuration` → `subnets[*].ipConfig` | `target.network_subnets` → `GET /subnets.subnets[*].cidr + ip_version + gateway_ip`; `target.network_ports` → `GET /ports.ports[*].fixed_ips + security_groups + port_security_enabled`; `target.network_routers` → `GET /routers.routers[*].routes + external_gateway_info` | conditional | critical · 60s |
| `target.network.security_policy` | `target.security_policies` → `owner: approved_network_policy_observer` | `target.security_policy` → `policies[*].scope + securedGroups + state` | `target.security_group_rules` → `GET /security-groups.security_groups[*].security_group_rules`; `target.security_stateful` → `security_groups[*].stateful` | conditional | critical · 60s |
| `target.network.isolation` | `target.boot_and_isolation` → `owner: quarantine_native_allow_deny_test` | `target.allowed_denied_flows` → `owner: native_allow_and_deny_policy_measurement` | `target.network_isolation` → `owner: verified_negative_ingress_egress_paths` | conditional | critical · 60s |
| `target.guest.boot_drivers` | `target.guest_device_support` → `owner: guest_firmware_driver_target_profile` | `target.guest_driver_compat` → `owner: guest_driver_and_boot_certification` | `target.boot_guest_drivers` → `owner: tested_guest_boot_device_driver_matrix` | conditional | critical · 3600s |
| `target.image.ingest` | **No direct field mapping** | `target.image_import` → `POST images + task.status + image URL readback` | `target.image_import_probe` → `POST /v2/images + import + GET /v2/images/{id}` | conditional | critical · 300s |
| `target.vm.create` | `target.ovf_import` → `ResourcePool.ImportVApp + HttpNfcLease` | `target.vm_creation` → `POST vms + task.status + VM readback` | `target.vm_create_probe` → `POST /servers + GET /servers/{id}` | conditional | critical · 300s |
| `target.permissions.entitlements` | `target.privileges_and_license` → `owner: vcenter_permissions_and_product_entitlements` | `target.project_authorization` → `subnets[*].projectExtId + sharedWithProjects`; `target.quotas_and_fences` → `owner: reserved_capacity_and_api_entitlements` | `target.project_quotas` → `owner: project_quotas_and_policy_grants` | conditional | critical · 15s |
| `target.optional.categories` | `target.optional_tags` → `/api/cis/tagging/tag-association` | `target.categories` → `categories[*].key + value` | **No direct field mapping** | conditional | optional · 3600s |
| `target.vmware.target.datacenter_scope` | `target.datacenter_scope` → `/api/vcenter/datacenter` | **No direct field mapping** | **No direct field mapping** | platform_specific | critical · 300s |
| `target.vmware.target.vm_folder` | `target.vm_folder` → `/api/vcenter/folder[*].type=VIRTUAL_MACHINE` | **No direct field mapping** | **No direct field mapping** | platform_specific | critical · 300s |
| `target.ahv.target.prism_identity` | **No direct field mapping** | `target.prism_identity` → `domain-managers/{id}.data.extId` | **No direct field mapping** | platform_specific | critical · 3600s |
| `target.ahv.target.storage_encryption` | **No direct field mapping** | `target.storage_encryption` → `storage-containers[*].isEncrypted + replicationFactor` | **No direct field mapping** | platform_specific | critical · 300s |
| `target.ahv.target.subnet_external` | **No direct field mapping** | `target.subnet_external` → `subnets[*].isExternal` | **No direct field mapping** | platform_specific | critical · 60s |
| `target.ahv.target.subnet_vpc` | **No direct field mapping** | `target.subnet_vpc` → `subnets[*].vpcReference` | **No direct field mapping** | platform_specific | critical · 60s |
| `target.openstack.target.image_formats` | **No direct field mapping** | **No direct field mapping** | `target.image_formats` → `GET /v2/schemas/image.properties.disk_format.enum` | platform_specific | critical · 3600s |
| `target.openstack.target.image_import_methods` | **No direct field mapping** | **No direct field mapping** | `target.image_import_methods` → `GET /v2/info/import.import-methods.value` | platform_specific | critical · 3600s |
| `target.openstack.target.network_extensions` | **No direct field mapping** | **No direct field mapping** | `target.network_extensions` → `GET /extensions.extensions[*].alias` | platform_specific | critical · 3600s |
| `target.openstack.target.network_trunks` | **No direct field mapping** | **No direct field mapping** | `target.network_trunks` → `GET /trunks.trunks[*].sub_ports` | platform_specific | critical · 120s |
| `target.openstack.target.qos_policies` | **No direct field mapping** | **No direct field mapping** | `target.qos_policies` → `GET /qos/policies.policies[*].rules` | platform_specific | optional · 300s |
| `target.openstack.target.secret_key_backends` | **No direct field mapping** | **No direct field mapping** | `target.secret_key_backends` → `owner: barbican_key_and_volume_backend_mapping` | platform_specific | critical · 300s |
| `target.openstack.target.identity_catalog` | **No direct field mapping** | **No direct field mapping** | `target.identity_catalog` → `GET /auth/catalog` | platform_specific | critical · 3600s |
| `target.openstack.target.network_dhcp` | **No direct field mapping** | **No direct field mapping** | `target.network_dhcp` → `subnets[*].enable_dhcp + dns_nameservers + allocation_pools` | platform_specific | critical · 60s |
| `target.openstack.placement_traits` | **No direct field mapping** | **No direct field mapping** | `target.placement_traits` → `GET /traits.traits[*]` | platform_specific | critical · 120s |

### Owner, application, security and operating obligations (27 canonical groups)

| Canonical field | VMware vSphere manifest field(s) | Nutanix AHV manifest field(s) | OpenStack manifest field(s) | Relationship | Criticality · max age |
| --- | --- | --- | --- | --- | --- |
| `owner.application.consistency` | `application.consistency` → `owner: application_consistency` | `application.consistency` → `owner: application_consistency` | `application.consistency` → `owner: application_consistency` | owner_common | critical · 3600s |
| `owner.application.datasets` | `application.datasets` → `owner: datasets_and_mounts` | `application.datasets` → `owner: datasets_and_mounts` | `application.datasets` → `owner: datasets_and_mounts` | owner_common | critical · 3600s |
| `owner.application.dependencies` | `application.dependencies` → `owner: dependencies` | `application.dependencies` → `owner: dependencies` | `application.dependencies` → `owner: dependencies` | owner_common | critical · 3600s |
| `owner.application.writer_fencing` | `application.writer_fencing` → `owner: writer_fencing` | `application.writer_fencing` → `owner: writer_fencing` | `application.writer_fencing` → `owner: writer_fencing` | owner_common | critical · 300s |
| `owner.application.final_delta` | `application.final_delta` → `owner: delta_protocol` | `application.final_delta` → `owner: delta_protocol` | `application.final_delta` → `owner: delta_protocol` | owner_common | critical · 300s |
| `owner.application.outage_objective` | `application.outage_objective` → `owner: max_outage_seconds` | `application.outage_objective` → `owner: max_outage_seconds` | `application.outage_objective` → `owner: max_outage_seconds` | owner_common | critical · 3600s |
| `owner.application.data_loss_objective` | `application.data_loss_objective` → `owner: max_data_loss_bytes` | `application.data_loss_objective` → `owner: max_data_loss_bytes` | `application.data_loss_objective` → `owner: max_data_loss_bytes` | owner_common | critical · 3600s |
| `owner.guest.boot_drivers` | `guest.boot_drivers` → `owner: guest_transformation_profile` | `guest.boot_drivers` → `owner: guest_transformation_profile` | `guest.boot_drivers` → `owner: guest_transformation_profile` | owner_common | critical · 3600s |
| `owner.guest.os_activation` | `guest.os_activation` → `owner: guest_os_licensing_and_activation` | `guest.os_activation` → `owner: guest_os_licensing_and_activation` | `guest.os_activation` → `owner: guest_os_licensing_and_activation` | owner_common | critical · 86400s |
| `owner.guest.application_health` | `guest.application_health` → `owner: application_readiness_checks` | `guest.application_health` → `owner: application_readiness_checks` | `guest.application_health` → `owner: application_readiness_checks` | owner_common | critical · 300s |
| `owner.storage.encryption_key_custody` | `storage.encryption_key_custody` → `owner: key_escrow_and_restore` | `storage.encryption_key_custody` → `owner: key_escrow_and_restore` | `storage.encryption_key_custody` → `owner: key_escrow_and_restore` | owner_common | critical · 300s |
| `owner.recovery.rollback_protocol` | `recovery.rollback_protocol` → `owner: recovery_protocol` | `recovery.rollback_protocol` → `owner: recovery_protocol` | `recovery.rollback_protocol` → `owner: recovery_protocol` | owner_common | critical · 3600s |
| `owner.recovery.restore_evidence` | `recovery.restore_evidence` → `owner: measured_restore_receipt` | `recovery.restore_evidence` → `owner: measured_restore_receipt` | `recovery.restore_evidence` → `owner: measured_restore_receipt` | owner_common | critical · 3600s |
| `owner.network.required_paths` | `network.required_paths` → `owner: application_allow_and_deny_paths` | `network.required_paths` → `owner: application_allow_and_deny_paths` | `network.required_paths` → `owner: application_allow_and_deny_paths` | owner_common | critical · 300s |
| `owner.network.address_ownership` | `network.address_ownership` → `owner: ipam_dns_ownership` | `network.address_ownership` → `owner: ipam_dns_ownership` | `network.address_ownership` → `owner: ipam_dns_ownership` | owner_common | critical · 3600s |
| `owner.network.firewall_flows` | `network.firewall_flows` → `owner: policy_flows_and_rule_semantics` | `network.firewall_flows` → `owner: policy_flows_and_rule_semantics` | `network.firewall_flows` → `owner: policy_flows_and_rule_semantics` | owner_common | critical · 300s |
| `owner.security.tenant_isolation` | `security.tenant_isolation` → `owner: tenant_and_network_isolation_acceptance` | `security.tenant_isolation` → `owner: tenant_and_network_isolation_acceptance` | `security.tenant_isolation` → `owner: tenant_and_network_isolation_acceptance` | owner_common | critical · 300s |
| `owner.security.credential_scope` | `security.credential_scope` → `owner: service_credential_and_role_attestation` | `security.credential_scope` → `owner: service_credential_and_role_attestation` | `security.credential_scope` → `owner: service_credential_and_role_attestation` | owner_common | critical · 300s |
| `owner.operations.backup_coverage` | `operations.backup_coverage` → `owner: backup_coverage_acceptance` | `operations.backup_coverage` → `owner: backup_coverage_acceptance` | `operations.backup_coverage` → `owner: backup_coverage_acceptance` | owner_common | critical · 3600s |
| `owner.operations.monitoring` | `operations.monitoring` → `owner: monitoring_and_logging_acceptance` | `operations.monitoring` → `owner: monitoring_and_logging_acceptance` | `operations.monitoring` → `owner: monitoring_and_logging_acceptance` | owner_common | critical · 3600s |
| `owner.operations.dns_cutover` | `operations.dns_cutover` → `owner: dns_switch_and_rollback_authority` | `operations.dns_cutover` → `owner: dns_switch_and_rollback_authority` | `operations.dns_cutover` → `owner: dns_switch_and_rollback_authority` | owner_common | critical · 300s |
| `owner.operations.time_and_identity` | `operations.time_and_identity` → `owner: time_dns_directory_and_trust_mappings` | `operations.time_and_identity` → `owner: time_dns_directory_and_trust_mappings` | `operations.time_and_identity` → `owner: time_dns_directory_and_trust_mappings` | owner_common | critical · 3600s |
| `owner.operations.cleanup_and_retention` | `operations.cleanup_and_retention` → `owner: retention_and_cleanup` | `operations.cleanup_and_retention` → `owner: retention_and_cleanup` | `operations.cleanup_and_retention` → `owner: retention_and_cleanup` | owner_common | critical · 3600s |
| `owner.application.optional_tags` | `application.optional_tags` → `owner: nonfunctional_descriptions_and_tags` | `application.optional_tags` → `owner: nonfunctional_descriptions_and_tags` | `application.optional_tags` → `owner: nonfunctional_descriptions_and_tags` | owner_common | optional · 86400s |
| `owner.network.optional_firewall_flows` | `network.optional_firewall_flows` → `owner: provably_nonessential_policy_flows` | `network.optional_firewall_flows` → `owner: provably_nonessential_policy_flows` | `network.optional_firewall_flows` → `owner: provably_nonessential_policy_flows` | owner_common | optional · 300s |
| `owner.operations.optional_integrations` | `operations.optional_integrations` → `owner: nonessential_integrations` | `operations.optional_integrations` → `owner: nonessential_integrations` | `operations.optional_integrations` → `owner: nonessential_integrations` | owner_common | optional · 3600s |
| `owner.placement.native_reserved_capacity` | `placement.native_reserved_capacity` → `owner: native_owner_available_capacity_and_exclusive_reservation` | `placement.native_reserved_capacity` → `owner: native_owner_available_capacity_and_exclusive_reservation` | `placement.native_reserved_capacity` → `owner: native_owner_available_capacity_and_exclusive_reservation` | owner_common | critical · 15s |

## Required further implementation

The collection manifest and crosswalk now describe the required mapping,
but do not yet *execute* translations, collect per-VM facts, evaluate
conditional applicability, prove destination feature availability, maintain
an append-only signed evidence ledger, or suppress optional native effects
in real migrations. The integration must build a scope-bound canonical
projection, keep source API version and freshness on every datum, and use
this crosswalk to enumerate blockers and warnings before Assurance can
independently qualify a method. Review owner approval and evidence
revocation at every native write and retry.

Crosswalk drift checks must reject changed source field paths,
missing rows, mismatched criticality, stale age assumptions, new undocumented
native collectors and a changed platform version or installed entitlement.
See `next_work.md` CT-N15/CT-API-10 for native integration gates.
