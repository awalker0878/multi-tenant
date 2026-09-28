"""Typed semantics beneath the existing capability IDs; never vendor support claims.

A capability name is not an equivalence proof. Properties describe observed
behaviour of the selected resource scope. The inventory/observation digest and
independent qualification still bind who observed it, where and when. Missing
properties are unknown, not false and never a reason to weaken a requirement.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from provisioner.domain.capabilities import CAPABILITIES

# None denotes an exact integer in [0, 2**63-1]; bool is deliberately not an int.
# Only these properties and their documented value types can enter a plan.
PROPERTY_VALUES = MappingProxyType({
    'network_domain.routing_isolation': ('independent-context', 'shared-context'),
    'network_domain.encapsulation': ('none', 'vlan', 'vxlan', 'geneve'),
    'network_domain.mtu': None,
    'network_domain.routing_model': ('nsx-tier1', 'nsx-tier0-vrf', 'nutanix-vpc', 'neutron-router'),
    'network_domain.parent_ha_mode': ('active-standby', 'active-active-stateless', 'active-active-stateful'),
    'distributed_firewall.enforcement': ('enforce', 'monitor', 'disabled'),
    'distributed_firewall.scope': ('all-workload-nics', 'selected-nics', 'gateway-only', 'none'),
    'distributed_firewall.rule_model': ('ordered-first-match', 'additive-allow'),
    'gateway_policy.enforcement': ('enforce', 'monitor', 'disabled'),
    'gateway_policy.default_action': ('deny', 'allow'),
    'sriov_nic.security_path': ('verified-enforcement', 'bypass', 'unsupported'),
    'sriov_nic.migration_mode': ('transparent', 'detach-reattach', 'unsupported'),
    'network_qos.datapath': ('kernel', 'ovs-dpdk', 'sriov'),
    'huge_pages.configured': (True, False),
    'vm_create.firmware': ('bios', 'uefi'),
    'shared_disks.writer_coordination': (True, False),
    'pci_passthrough.mapping_verified': (True, False),
    'cpu_topology.architecture': ('x86_64', 'aarch64'),
    'storage_qos.minimum_iops': None,
    'storage_qos.maximum_iops': None,
    'storage_qos.consumer': ('front-end', 'back-end', 'both'),
    'storage_encryption.layer': ('guest', 'hypervisor', 'storage-backend'),
    'storage_encryption.destination_key_ready': (True, False),
    'snapshot_consistency.level': ('crash', 'filesystem', 'application'),
    'secure_boot.enabled': (True, False),
    'vtpm.state_handling': ('preserve', 'recreate', 'unsupported'),
    'guest_drivers.verified': (True, False),
    'ha_restart.admission_control': (True, False),
})

FORMAT = 'hosting-capability-properties/1'
MAX_REQUIREMENTS = 128
MAX_INTEGER = 2**63 - 1


def contract_digest() -> str:
    """Bind the property vocabulary and semantics revision to derived decisions."""
    body = {'format': FORMAT, 'properties': dict(PROPERTY_VALUES),
            'operators': ['eq', 'gte', 'lte']}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _value(name: str, value: object) -> bool:
    allowed = PROPERTY_VALUES.get(name, ())
    if allowed is None:
        return type(value) is int and 0 <= value <= MAX_INTEGER
    return any(type(value) is type(item) and value == item for item in allowed)


@dataclass(frozen=True, slots=True)
class PropertyRequirement:
    property: str
    operator: str
    value: str | int | bool

    def __post_init__(self) -> None:
        if (not isinstance(self.property, str) or self.property not in PROPERTY_VALUES
                or self.property.split('.', 1)[0] not in CAPABILITIES
                or self.operator not in ('eq', 'gte', 'lte')
                or not _value(self.property, self.value)
                or self.operator != 'eq' and PROPERTY_VALUES[self.property] is not None):
            raise ValueError('Invalid typed capability property requirement')

    def to_dict(self) -> dict:
        return {'property': self.property, 'operator': self.operator, 'value': self.value}

    def satisfied_by(self, value: object) -> bool:
        if not _value(self.property, value):
            return False
        return (value == self.value if self.operator == 'eq' else
                value >= self.value if self.operator == 'gte' else value <= self.value)


def parse_requirements(value: object, capabilities: object) -> tuple[PropertyRequirement, ...]:
    """Strict closed schema; each property must have its existing capability owner."""
    if (not isinstance(value, list) or len(value) > MAX_REQUIREMENTS
            or not isinstance(capabilities, (list, tuple, set, frozenset))
            or any(not isinstance(cap, str) or cap not in CAPABILITIES for cap in capabilities)):
        raise ValueError('Invalid bounded capability property requirements')
    result = []
    for row in value:
        if not isinstance(row, dict) or set(row) != {'property', 'operator', 'value'}:
            raise ValueError('Unknown or missing capability property requirement fields')
        requirement = PropertyRequirement(**row)
        if requirement.property.split('.', 1)[0] not in capabilities:
            raise ValueError('Capability property has no required capability owner')
        if requirement in result:
            raise ValueError('Duplicate capability property requirement')
        result.append(requirement)
    return merge_requirements(tuple(result))


def merge_requirements(*groups: tuple[PropertyRequirement, ...]) -> tuple[PropertyRequirement, ...]:
    """Intersect requirements. Never let the last selected profile weaken a prior one."""
    requirements = set()
    for group in groups:
        if not isinstance(group, tuple) or any(not isinstance(r, PropertyRequirement) for r in group):
            raise ValueError('Expected immutable typed capability requirements')
        requirements.update(group)
    if len(requirements) > MAX_REQUIREMENTS:
        raise ValueError('Capability property requirement budget exceeded')
    for name in sorted({r.property for r in requirements}):
        selected = [r for r in requirements if r.property == name]
        equals = [r.value for r in selected if r.operator == 'eq']
        if equals and any(not r.satisfied_by(equals[0]) for r in selected):
            raise ValueError('Conflicting capability property requirements: ' + name)
        lower = max((r.value for r in selected if r.operator == 'gte'), default=0)
        upper = min((r.value for r in selected if r.operator == 'lte'), default=MAX_INTEGER)
        if lower > upper:
            raise ValueError('Empty capability property range: ' + name)
    return tuple(sorted(requirements, key=lambda r: (r.property, r.operator, str(r.value))))


def entails(requirements: tuple[PropertyRequirement, ...], required: PropertyRequirement) -> bool:
    """Whether a destination requirement set guarantees one source requirement."""
    merge_requirements(requirements)
    matching = [r for r in requirements if r.property == required.property]
    if not matching:
        return False
    equals = [r.value for r in matching if r.operator == 'eq']
    if equals:
        return required.satisfied_by(equals[0])
    lower = max((r.value for r in matching if r.operator == 'gte'), default=0)
    upper = min((r.value for r in matching if r.operator == 'lte'), default=MAX_INTEGER)
    return (lower == upper == required.value if required.operator == 'eq' else
            lower >= required.value if required.operator == 'gte' else upper <= required.value)


def validate_observations(value: object) -> Mapping[str, str | int | bool]:
    """Validate a snapshot's scoped properties without minting evidence or defaults."""
    if (not isinstance(value, dict) or len(value) > len(PROPERTY_VALUES)
            or any(not isinstance(name, str) or name not in PROPERTY_VALUES
                   or not _value(name, observed) for name, observed in value.items())):
        raise ValueError('Unknown or malformed observed capability properties')
    return MappingProxyType(dict(sorted(value.items())))


def evaluate(requirements: tuple[PropertyRequirement, ...], observations: Mapping) -> tuple[str, ...]:
    """Stable diagnostics for missing, incompatible or internally impossible facts.

    This is a deterministic compatibility check, not native qualification. A
    successful result never authorizes an operation or proves policy equivalence.
    """
    merge_requirements(requirements)  # validate direct callers too
    if not isinstance(observations, Mapping):
        raise ValueError('Expected scoped property observations')
    observed = validate_observations(dict(observations))
    issues = []
    for requirement in requirements:
        name = requirement.property
        if name not in observed:
            issues.append('PROPERTY_UNKNOWN:' + name)
        elif not requirement.satisfied_by(observed[name]):
            issues.append('PROPERTY_MISMATCH:' + name)
    # Only apply a native restriction when that exact realization is observed.
    # A VRF or a platform family alone must not imply a parent HA mode.
    if observed.get('network_domain.routing_model') == 'nsx-tier0-vrf':
        mode = observed.get('network_domain.parent_ha_mode')
        if mode is None:
            issues.append('PROPERTY_UNKNOWN:network_domain.parent_ha_mode')
        elif mode == 'active-active-stateful':
            issues.append('NSX_VRF_PARENT_HA_INCOMPATIBLE')
    if observed.get('network_qos.datapath') == 'ovs-dpdk':
        pages = observed.get('huge_pages.configured')
        if pages is None:
            issues.append('PROPERTY_UNKNOWN:huge_pages.configured')
        elif pages is not True:
            issues.append('OVS_DPDK_HUGE_PAGES_REQUIRED')
    if (observed.get('distributed_firewall.scope') == 'all-workload-nics'
            and observed.get('sriov_nic.security_path') == 'bypass'):
        issues.append('DISTRIBUTED_FIREWALL_DATAPATH_BYPASS')
    return tuple(sorted(set(issues)))
