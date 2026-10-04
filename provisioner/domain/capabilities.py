"""Reviewed workload capability vocabulary shared by all qualification consumers.

These are independently assessable requirements, not vendor feature promises.
Every platform registry must explicitly cover every ID; an absent, unknown or
unqualified capability cannot satisfy a mandatory requirement. Directed migration
route qualification and per-effect authority remain separate controls.
"""
from __future__ import annotations

import hashlib
import json
from types import MappingProxyType

CAPABILITY_GROUPS = MappingProxyType({
    'compute': (
        'vm_create', 'vm_resize', 'vm_power', 'vm_delete', 'cpu_topology',
        'memory_reservation', 'host_affinity', 'host_anti_affinity',
        'numa_placement', 'cpu_pinning', 'huge_pages', 'gpu_passthrough',
        'vgpu', 'pci_passthrough', 'secure_boot', 'vtpm',
        'firmware_bios', 'firmware_uefi',
    ),
    'storage': (
        'boot_volume', 'data_volumes', 'storage_placement', 'storage_qos',
        'storage_encryption', 'snapshot_consistency', 'snapshot_chain',
        'capture_export', 'image_import', 'disk_conversion', 'shared_disks',
        'disk_order', 'volume_resize',
    ),
    'network': (
        'network_domain', 'ipv4', 'ipv6', 'dynamic_routing',
        'native_load_balancer', 'multiple_nics', 'nic_order',
        'address_preservation', 'address_translation', 'trunk_vlan',
        'sriov_nic', 'network_qos', 'route_readback',
    ),
    'security': (
        'distributed_firewall', 'gateway_policy', 'service_insertion',
        'dedicated_edge_context', 'audit_logging', 'policy_equivalence',
        'controlled_ingress', 'controlled_egress',
    ),
    'guest': (
        'guest_linux', 'guest_windows', 'guest_appliance',
        'guest_customization', 'guest_drivers', 'guest_identity',
        'guest_readiness',
    ),
    'discovery': (
        'inventory_collection', 'inventory_pagination', 'inventory_freshness',
        'inventory_scope', 'quota_readback', 'dependency_review',
        'no_change_adoption',
    ),
    'migration': (
        'dataset_transfer', 'incremental_sync', 'data_integrity',
        'consistency_groups', 'source_quiesce', 'source_fencing',
        'isolated_rehearsal', 'final_sync', 'traffic_cutover',
        'target_activation', 'pre_write_rollback', 'post_write_recovery',
        'reverse_sync', 'source_retention',
    ),
    'services': (
        'dns_registration', 'identity_join', 'time_sync', 'trust_distribution',
        'log_forwarding', 'monitoring', 'backup_restore',
    ),
    'operations': (
        'capacity_reservation', 'ipam_reservation', 'staging_budget',
        'concurrency_budget', 'operation_reconciliation', 'ha_restart',
        'controlplane_dr', 'evidence_retention', 'privileged_access',
        'release_qualification',
    ),
})
CAPABILITIES = frozenset(capability for group in CAPABILITY_GROUPS.values()
                         for capability in group)
PLATFORMS = frozenset({'nutanix', 'vmware-nsx', 'openstack'})


def catalog_digest() -> str:
    """Bind registry review to the complete grouped vocabulary, not just its size."""
    document = {group: list(ids) for group, ids in CAPABILITY_GROUPS.items()}
    return hashlib.sha256(json.dumps(document, sort_keys=True,
                                    separators=(',', ':')).encode('utf-8')).hexdigest()
