"""Snapshot-bound semantic comparison, never native execution authorization.

The source policy requirements must be independently reviewed with the existing
POLICY_TRANSLATION/SECURITY_EQUIVALENCE findings. An API feature name, vendor
manual, arbitrary VM tag or family name is not such a review. Target properties
refer to the selected realization, not every possible configuration of a cloud.
"""
from __future__ import annotations

from provisioner.domain.capabilities import CAPABILITIES
from provisioner.domain.capability_properties import (
    PropertyRequirement, contract_digest, evaluate, merge_requirements,
    parse_requirements, validate_observations,
)
from .model import DiscoveryObject

_WHOLE_VM = frozenset({'COLD_VM_CONVERSION', 'WARM_VM_TRANSFER', 'SAME_PLATFORM_RELOCATION'})
_MAX = 2**63 - 1


def _fact(obj: DiscoveryObject | None, name: str):
    if obj is None:
        return None
    item = next((f for f in obj.facts if f.name == name), None)
    return item.value() if item is not None and item.state == 'KNOWN' else None


def _number(value: object, minimum: int = 0) -> bool:
    return type(value) is int and minimum <= value <= _MAX


def check_compatibility(source: DiscoveryObject | None, target: DiscoveryObject | None,
                        method: str) -> tuple[tuple[str, str, str, str], ...]:
    """Return explicit BLOCKER/UNKNOWN findings for one directed comparison.

    Hardware preservation requirements are derived only from explicit source
    facts. Warm transfer means disk pre-copy with final synchronization, not live
    memory transfer. Generic feature support cannot bypass missing native facts.
    """
    issues = []

    def add(severity, code, reason, remedy):
        issues.append((severity, code, reason, remedy))

    requirements = ()
    required_capabilities = ()
    for obj, label in ((source, 'SOURCE'), (target, 'DESTINATION')):
        if _fact(obj, 'capabilityPropertySchemaDigest') != contract_digest():
            add('UNKNOWN', label + '_PROPERTY_SCHEMA_UNVERIFIED',
                'The property interpretation is missing or from another revision.',
                'Collect current properties and re-review both snapshot digests; do not relabel old evidence.')
    capabilities = _fact(source, 'requiredCapabilities')
    try:
        if (not isinstance(capabilities, list) or len(capabilities) > len(CAPABILITIES)
                or any(not isinstance(cap, str) for cap in capabilities)
                or len(set(capabilities)) != len(capabilities)):
            raise ValueError('Incomplete capability requirements')
        requirements = parse_requirements(_fact(source, 'capabilityRequirements'), capabilities)
        required_capabilities = tuple(capabilities)
    except (ValueError, TypeError):
        add('UNKNOWN', 'SOURCE_CAPABILITY_REQUIREMENTS_UNVERIFIED',
            'The source lacks a complete typed requirement set.',
            'Bind reviewed profile requirements to this source observation, including an explicit empty set when applicable.')
    try:
        observations = validate_observations(_fact(target, 'capabilityProperties'))
    except (ValueError, TypeError):
        observations = {}
        add('UNKNOWN', 'DESTINATION_CAPABILITY_PROPERTIES_UNVERIFIED',
            'The selected target realization lacks valid observed property semantics.',
            'Observe the selected target datapath, storage and control configuration with exact native identities.')

    derived = []
    if method in _WHOLE_VM:
        for name, prop, values in (
                ('architecture', 'cpu_topology.architecture', ('x86_64', 'aarch64')),
                ('firmware', 'vm_create.firmware', ('bios', 'uefi'))):
            value = _fact(source, name)
            if not isinstance(value, str) or value not in values:
                add('UNKNOWN', 'SOURCE_' + name.upper() + '_UNVERIFIED',
                    'The source ' + name + ' is not observed.',
                    'Collect native hardware facts; do not infer them from the OS profile name.')
            else:
                derived.append(PropertyRequirement(prop, 'eq', value))
        for name, prop, wanted in (
                ('secureBootEnabled', 'secure_boot.enabled', True),
                ('vtpmEnabled', 'vtpm.state_handling', 'preserve'),
                ('storageEncrypted', 'storage_encryption.destination_key_ready', True),
                ('sharedDisks', 'shared_disks.writer_coordination', True)):
            value = _fact(source, name)
            if type(value) is not bool:
                add('UNKNOWN', 'SOURCE_' + name.upper() + '_UNVERIFIED',
                    'The source ' + name + ' state is unknown.',
                    'Observe all relevant native devices and keys; absence of an API field is not false.')
            elif name == 'secureBootEnabled':
                derived.append(PropertyRequirement(prop, 'eq', value))
            elif value:
                derived.append(PropertyRequirement(prop, 'eq', wanted))
        if _fact(source, 'storageEncrypted') is True:
            layer = _fact(source, 'storageEncryptionLayer')
            if layer not in ('guest', 'hypervisor', 'storage-backend'):
                add('UNKNOWN', 'SOURCE_ENCRYPTION_LAYER_UNVERIFIED',
                    'Encryption mechanisms and key custody are not interchangeable.',
                    'Observe the source encryption layer and review an explicit destination protection design.')
            else:
                derived.append(PropertyRequirement('storage_encryption.layer', 'eq', layer))
        devices = _fact(source, 'passthroughDevices')
        if (not isinstance(devices, list) or len(devices) > 256
                or any(not isinstance(device, str) or not 1 <= len(device) <= 512
                       or any(ord(c) < 32 or ord(c) == 127 for c in device) for device in devices)
                or len(set(devices)) != len(devices)):
            add('UNKNOWN', 'SOURCE_PASSTHROUGH_DEVICES_UNVERIFIED',
                'The source passthrough attachment set is unknown or ambiguous.',
                'Collect the complete device set and qualify destination device mappings.')
        elif devices:
            derived.append(PropertyRequirement('pci_passthrough.mapping_verified', 'eq', True))
        memory_required = _fact(source, 'memoryStateRequired')
        if type(memory_required) is not bool:
            add('UNKNOWN', 'SOURCE_MEMORY_STATE_REQUIREMENT_UNVERIFIED',
                'Whether volatile execution state must survive is unreviewed.',
                'Record the application-approved restart or memory-state requirement.')
        elif memory_required and method in {'COLD_VM_CONVERSION', 'WARM_VM_TRANSFER'}:
            add('BLOCKER', 'MEMORY_STATE_TRANSFER_NOT_IMPLEMENTED',
                'Disk conversion and warm disk pre-copy do not preserve running memory state.',
                'Use an independently qualified memory-state route or an approved application restart strategy.')
        if method in {'COLD_VM_CONVERSION', 'WARM_VM_TRANSFER'}:
            derived.append(PropertyRequirement('guest_drivers.verified', 'eq', True))
    # Hardware observations create requirements independently of a reviewed
    # profile. A matching property must not reconstruct an absent capability.
    # Preserving explicitly disabled Secure Boot does not require enabling it.
    derived_capabilities = {
        requirement.property.split('.', 1)[0] for requirement in derived
        if not (requirement.property == 'secure_boot.enabled' and requirement.value is False)
    }
    required_capabilities = set(required_capabilities) | derived_capabilities
    available = _fact(target, 'observedCapabilities')
    if (not isinstance(available, list) or len(available) > len(CAPABILITIES)
            or any(not isinstance(cap, str) or cap not in CAPABILITIES for cap in available)
            or len(set(available)) != len(available)):
        add('UNKNOWN', 'DESTINATION_CAPABILITY_SET_UNVERIFIED',
            'The selected native capability set is missing or ambiguous.',
            'Collect a complete observed set; route reviews do not supply omitted feature facts.')
    else:
        for missing in sorted(set(required_capabilities) - set(available)):
            add('BLOCKER', 'REQUIRED_CAPABILITY_ABSENT',
                'The selected target does not advertise required capability ' + missing + '.',
                'Choose and qualify a target that satisfies every source requirement; do not drop it.')

    try:
        combined = merge_requirements(requirements, tuple(derived))
    except ValueError:
        combined = requirements
        add('BLOCKER', 'SOURCE_PROFILE_NATIVE_CONTRADICTION',
            'Declared policy conflicts with the observed source hardware.',
            'Reconcile the source configuration and policy; never discard the stricter requirement.')
    for issue in evaluate(combined, observations):
        code, _, prop = issue.partition(':')
        severity = 'UNKNOWN' if code == 'PROPERTY_UNKNOWN' else 'BLOCKER'
        add(severity, code, 'Target capability property check: ' + (prop or code) + '.',
            'Collect missing scoped facts or choose a compatible native realization; re-review policy and route evidence.')

    if method == 'WARM_VM_TRANSFER':
        rate = _fact(source, 'dirtyRateBytesPerSecond')
        speed = _fact(target, 'measuredTransferBytesPerSecond')
        source_sample = _fact(source, 'dirtyRateSampleSeconds')
        target_sample = _fact(target, 'transferSampleSeconds')
        if not (_number(rate) and _number(speed, 1)
                and _number(source_sample, 1) and _number(target_sample, 1)):
            add('UNKNOWN', 'WARM_TRANSFER_MEASUREMENT_MISSING',
                'A current bounded dirty-rate/throughput observation is unavailable.',
                'Measure both directions of the selected transfer path and source change rate before scheduling cutover.')
        elif rate >= speed:
            add('BLOCKER', 'WARM_TRANSFER_NONCONVERGENT',
                'The observed source dirty rate is not below the effective transfer rate.',
                'Reduce change rate, add qualified bandwidth or choose an approved cold/application-native route.')
    # Deterministic de-duplication preserves property-specific reason text.
    return tuple(dict.fromkeys(issues))
