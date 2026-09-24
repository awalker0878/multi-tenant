"""Canonical sovereign portability bundle.

The bundle is the provider-neutral payload that survives a platform change. Source
placement, CIDRs, native identifiers and provider-specific fields are provenance,
not portable workload requirements, so they are deliberately excluded from the
portable workload/network sections.
"""
from __future__ import annotations

from provisioner.domain.request import digest
from provisioner.portability import policy

BUNDLE_FORMAT = 'hosting-portability-bundle/1'


def _workloads(plan) -> list[dict]:
    rows = []
    for domain in plan.desired_state.domains:
        for workload in domain.workloads:
            rows.append({
                'name': workload.name,
                'zone': domain.zone,
                'compute': {'vcpu': workload.vcpu, 'memory_gib': workload.memory_gib},
                'storage': {'boot_disk_gib': workload.boot_disk_gib,
                            'data_disk_gib': workload.data_disk_gib},
            })
    return sorted(rows, key=lambda row: (row['zone'], row['name']))


def build(plan) -> dict:
    """Build the immutable portable state of a reviewed WSD plan."""
    capsule = policy.build(plan)
    body = {
        'format': BUNDLE_FORMAT,
        'identity': {
            'tenant': plan.request.tenant,
            'wsd': plan.request.wsd,
            'owner': plan.request.owner,
            'environment': plan.desired_state.lifecycle,
            'generation': plan.generation,
        },
        'source': {
            'platform': plan.desired_state.platform,
            'site': plan.desired_state.site_key,
            'plan_digest': plan.digest,
            'desired_state_digest': plan.desired_state.digest,
        },
        'workloads': _workloads(plan),
        'network': {
            'profile': plan.resolution.network['profile'],
            'address_family': plan.resolution.network['address_family'],
            'prefix_length': plan.resolution.network['prefix_length'],
            'zones': list(plan.resolution.zones),
        },
        'services': {
            name: {'profile': profile}
            for name, profile in sorted(plan.resolution.services.items())
        },
        'policy': capsule,
        'required_capabilities': list(plan.resolution.required_capabilities),
        'portability_rules': {
            'addresses': 'reallocate-on-target',
            'service_endpoints': 'rebind-on-target',
            'native_ids': 'never-portable',
            'policy': 'preserve-outcome-recompile-native',
            'secrets': 'never-embedded',
        },
        'limits': [
            'The bundle contains no source CIDR, cluster, VLAN, VNI, project, segment or provider ID',
            'Workload image and mutable data transfer are supplied by a separate mobility intent',
            'Successful target planning is not evidence that workload state has moved',
        ],
        'native_contact': False,
    }
    return {**body, 'digest': digest(body)}
