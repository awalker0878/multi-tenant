"""Declared directed mobility implementations and expansion campaign procedures.

Evidence is selected by the existing mobility/native/campaign owners. This module
does not introduce an index or an executable plugin registry. An evidence dossier
cannot supply an implementation: only declared installed owner paths may run.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import TYPE_CHECKING

from provisioner.controlplane.authority.model import PlanScope
from provisioner.controlplane.authority.service import AuthorityDenied

if TYPE_CHECKING:
    from .mobility import MobilityCampaign

_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$')
_PLATFORM = {'vmware': 'vmware-nsx', 'vmware-nsx': 'vmware-nsx',
             'nutanix': 'nutanix', 'openstack': 'openstack'}
_SCOPE = {'organizationId', 'tenantId', 'locationId', 'securityDomainId',
          'endpointId', 'nativeScopeId', 'platformFamily'}
PLAN_METHODS = {
    'REBUILD_RESTORE': 'APPLICATION_REBUILD_RESTORE',
    'COLD_VM_CONVERSION': 'COLD_WHOLE_VM',
    'SAME_PLATFORM_RELOCATION': 'SAME_FAMILY_RELOCATION',
    'APPLICATION_NATIVE': 'APPLICATION_NATIVE_DATABASE_SYNC',
    'WARM_VM_TRANSFER': 'WARM_WHOLE_VM',
}


@dataclass(frozen=True)
class DirectedImplementation:
    source: str
    destination: str
    method: str
    guest_profile: str
    driver: str
    owners: tuple[str, ...]

    @property
    def key(self):
        return self.source, self.destination, self.method, self.guest_profile


# The current control application's exact driver, guest/data selection and source
# fence owners implement this one direction. Entries are code declarations, not
# data loaded from a caller, evidence file, release matrix or directory of plugins.
_FIRST_APPLICATION = DirectedImplementation(
    'vmware-nsx', 'openstack', 'APPLICATION_REBUILD_RESTORE', 'linux-ubuntu-2404',
    'openstack-linux-rebuild/1',
    ('provisioner.controlplane.workflow.execution_selection',
     'provisioner.migration.application', 'provisioner.migration.cutover'))
IMPLEMENTATIONS = {_FIRST_APPLICATION.key: _FIRST_APPLICATION}
_DRIVERS = {_FIRST_APPLICATION.driver: _FIRST_APPLICATION}

_METHOD_BLOCKERS = {
    'COLD_WHOLE_VM': ('NATIVE_COLD_CAPTURE_EXPORT_OWNER_MISSING',
                     'NATIVE_DISK_CHAIN_CAPTURE_OWNER_MISSING',
                     'TARGET_IMAGE_IMPORT_AND_BOOT_OWNER_MISSING',
                     'QUALIFIED_GUEST_REMEDIATION_OWNER_MISSING'),
    'SAME_FAMILY_RELOCATION': ('QUALIFIED_TOPOLOGY_RELOCATION_DRIVER_MISSING',
                             'NATIVE_MOVE_TASK_AND_OLD_WRITER_RECOVERY_MISSING'),
    'APPLICATION_NATIVE_DATABASE_SYNC': ('SELECTED_DATABASE_SYNC_DRIVER_MISSING',
                                         'COMMIT_POSITION_AND_DIVERGENCE_OWNER_MISSING'),
    'WARM_WHOLE_VM': ('NATIVE_WARM_CAPTURE_CONVERGENCE_DRIVER_MISSING',
                    'RAM_DEVICE_AND_KEY_STATE_PRESERVATION_UNIMPLEMENTED'),
    'APPLICATION_REBUILD_RESTORE': ('DIRECTED_APPLICATION_NATIVE_DRIVER_MISSING',),
}

# The observation classes are the existing exported-campaign contract. Every
# NEGATIVE_CONTROL also requires the owner's independent positive-control proof.
EXPANSION_ASSERTIONS = {
    'APPLICATION_REBUILD_RESTORE': {
        'SOURCE_DATASET_SCOPE_VERIFIED': 'SERVICE_OPERATION',
        'RESTORE_METADATA_VALIDATED': 'SERVICE_OPERATION',
        'EXACT_GUEST_PROFILE_INSTALLED': 'SERVICE_OPERATION',
    },
    'COLD_WHOLE_VM': {
        'COLD_CAPTURE_IMMUTABLE': 'LIFECYCLE',
        'DISK_CHAIN_BOUNDARY_VERIFIED': 'SERVICE_OPERATION',
        'BROKEN_DISK_CHAIN_REJECTED': 'NEGATIVE_CONTROL',
        'ENCRYPTED_OR_VTPM_DEVICE_REJECTED': 'NEGATIVE_CONTROL',
        'PASSTHROUGH_OR_SHARED_DISK_REJECTED': 'NEGATIVE_CONTROL',
        'CONVERTER_TOOLCHAIN_AND_ISOLATION': 'OTHER',
        'CONVERTED_IMPORT_BOOT_OBSERVED': 'SERVICE_OPERATION',
        'FIRMWARE_SECURE_BOOT_AND_GUEST_DRIVERS': 'SERVICE_OPERATION',
        'REMAPPED_NATIVE_IDS_OBSERVED': 'LIFECYCLE',
    },
    'SAME_FAMILY_RELOCATION': {
        'SAME_RESOURCE_NOOP_REJECTED': 'NEGATIVE_CONTROL',
        'TOPOLOGY_MOVE_EXCLUSION_OBSERVED': 'FAILURE_RECOVERY',
        'DEVICE_AND_KEY_LINEAGE_PRESERVED': 'SERVICE_OPERATION',
        'INTERRUPTED_NATIVE_MOVE_RECONCILED': 'FAILURE_RECOVERY',
    },
    'APPLICATION_NATIVE_DATABASE_SYNC': {
        'DATABASE_ENGINE_AND_VERSION_BOUND': 'OTHER',
        'DATABASE_INITIAL_COPY_CONSISTENT': 'SERVICE_OPERATION',
        'DATABASE_LAG_CUTOFF_MEASURED': 'CAPACITY_LOAD',
        'DATABASE_FINAL_COMMIT_POSITION_BOUND': 'LIFECYCLE',
        'DATABASE_DIVERGENT_WRITERS_REJECTED': 'NEGATIVE_CONTROL',
        'DATABASE_POSTWRITE_REVERSE_SYNC': 'FAILURE_RECOVERY',
    },
    'WARM_WHOLE_VM': {
        'WARM_CONVERGENCE_AND_STOP_THRESHOLD': 'CAPACITY_LOAD',
        'WARM_ITERATION_STORAGE_AND_BANDWIDTH_BOUND': 'CAPACITY_LOAD',
        'RAM_DEVICE_AND_KEY_STATE_PRESERVED': 'SERVICE_OPERATION',
    },
}

WAVE_ASSERTIONS = {
    'WAVE_DEPENDENCY_ORDER_OBSERVED': 'LIFECYCLE',
    'WAVE_CONCURRENT_RESOURCE_BUDGET_STOP': 'CAPACITY_LOAD',
    'WAVE_SHARED_RISK_CONTAINED': 'FAILURE_RECOVERY',
    'WAVE_TENANT_FAIRNESS_OBSERVED': 'CAPACITY_LOAD',
}


def campaign_implementation_blockers(spec: 'MobilityCampaign') -> list[str]:
    """Keep a fully evidenced but unimplemented route explicitly unavailable."""
    key = (spec.source.platform, spec.destination.platform, spec.method, spec.guest_profile)
    if key in IMPLEMENTATIONS:
        return []
    if spec.method not in _METHOD_BLOCKERS:
        return ['MOBILITY_METHOD_NOT_DECLARED']
    # A matching direction/method with a different OS release must not reuse the
    # installed driver's Linux category as evidence of exact guest support.
    route = key[:3]
    if any(item[:3] == route for item in IMPLEMENTATIONS):
        return ['EXACT_GUEST_PROFILE_IMPLEMENTATION_MISSING']
    return list(_METHOD_BLOCKERS[spec.method])


def expansion_assertions(method: str, *, include_wave=False) -> dict[str, str]:
    """Return method procedures for the existing campaign run sheet owner."""
    if method not in EXPANSION_ASSERTIONS or type(include_wave) is not bool:
        raise ValueError('Declared mobility method and explicit wave applicability required')
    result = dict(EXPANSION_ASSERTIONS[method])
    if include_wave:
        result.update(WAVE_ASSERTIONS)
    return result


def _scope(value: dict) -> PlanScope:
    if not isinstance(value, dict) or set(value) != _SCOPE:
        raise ValueError('Exact native scope is required for directed execution')
    for field in _SCOPE - {'nativeScopeId', 'platformFamily'}:
        if not isinstance(value[field], str) or not _ID.fullmatch(value[field]):
            raise ValueError('Bounded native scope identities required')
    if (value['platformFamily'] not in _PLATFORM or not isinstance(value['nativeScopeId'], str)
            or not 1 <= len(value['nativeScopeId']) <= 512):
        raise ValueError('Implemented platform and exact native scope identity required')
    return PlanScope.from_record(value)


def require_implemented_action_selection(selection: dict) -> DirectedImplementation:
    """Guard the actual installed driver before any qualification/effect check.

    This check supplies no authority. The action gate still rereads current
    tuple/profile/site/action evidence, and B07/B10 still check worker ownership.
    """
    try:
        if not isinstance(selection, dict):
            raise ValueError('Directed execution selection required')
        implementation = _DRIVERS.get(selection['driver'])
        if implementation is None:
            raise ValueError('No installed directed execution driver')
        source, destination = _scope(selection['source']), _scope(selection['destination'])
        actual = (_PLATFORM[source.platform_family], _PLATFORM[destination.platform_family],
                  implementation.method, selection['guestProfile'])
        if actual != implementation.key:
            raise ValueError('Direction or exact guest differs from installed execution implementation')
        if (source.organization_id, source.tenant_id) != (destination.organization_id, destination.tenant_id):
            raise ValueError('Directed execution crosses the approved tenant')
        native_from = (source.platform_family, source.endpoint_id, source.native_scope_id, source.site_id)
        native_to = (destination.platform_family, destination.endpoint_id, destination.native_scope_id, destination.site_id)
        if native_from == native_to:
            raise ValueError('Same-resource no-op is not a native relocation')
        return implementation
    except (KeyError, TypeError, ValueError):
        raise AuthorityDenied('Selected direction, method or exact guest has no installed native execution implementation') from None
