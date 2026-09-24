"""Cross-platform capability and equivalence evaluation."""
from __future__ import annotations

from provisioner.adapters import base as adapters

EQUIVALENCE_FORMAT = 'hosting-portability-equivalence/1'

PORTABILITY_DIMENSIONS = (
    'portable-intent',
    'target-rebuild',
    'network-policy',
    'security-policy',
    'service-rebind',
    'identity-rebind',
    'backup-restore',
    'workload-artifact',
    'data-transfer',
    'secret-key-rebind',
    'cutover-fencing',
    'rollback',
)


def _dimension(name: str, implemented: bool, authority: str,
               blockers=(), notes=()) -> dict:
    return {'dimension': name, 'implemented': bool(implemented),
            'authority': authority, 'blockers': sorted(set(blockers)),
            'notes': list(notes)}


def dimensions(plan) -> list[dict]:
    """Repository-side portability capabilities for one portable plan.

    These describe the wrapper itself, not native qualification. A dimension is
    marked implemented only when the repository has a real provider-neutral
    contract for it.
    """
    services = set(plan.resolution.services)
    return [
        _dimension('portable-intent', True, 'hosting.platform/v1 WorkloadSecurityDomain'),
        _dimension('target-rebuild', True, 'existing WSD compiler and platform adapters'),
        _dimension('network-policy', True, 'portable policy capsule'),
        _dimension('security-policy', True, 'portable policy capsule'),
        _dimension('service-rebind', True, 'portable service profile bindings'),
        _dimension('identity-rebind', 'identity' in services, 'identity service owner',
                   () if 'identity' in services else ('IDENTITY_SERVICE_NOT_DECLARED',)),
        _dimension('backup-restore', 'backup' in services, 'backup service owner',
                   () if 'backup' in services else ('BACKUP_SERVICE_NOT_DECLARED',)),
        _dimension('workload-artifact', True, 'WorkloadMobility artifact contract'),
        _dimension('data-transfer', True, 'WorkloadMobility dataset contract'),
        _dimension('secret-key-rebind', True, 'WorkloadMobility rebind-only contract'),
        _dimension('cutover-fencing', True, 'WorkloadMobility cutover contract'),
        _dimension('rollback', True, 'WorkloadMobility rollback contract'),
    ]


def compare(source_plan, target_plan) -> dict:
    """Compare source and target outcomes without assuming identical topology."""
    source_adapter = adapters.get(source_plan.desired_state.platform)
    target_adapter = adapters.get(target_plan.desired_state.platform)
    required = tuple(sorted(source_plan.resolution.required_capabilities))
    target_capability = target_adapter.capability_contract(required=required)
    source_capability = source_adapter.capability_contract(required=required)

    mismatches = []
    if source_plan.resolution.profiles != target_plan.resolution.profiles:
        mismatches.append('PROFILE_SET_DIFFERS')
    if source_plan.resolution.profile_versions != target_plan.resolution.profile_versions:
        mismatches.append('PROFILE_VERSION_SET_DIFFERS')
    if source_plan.resolution.required_capabilities != target_plan.resolution.required_capabilities:
        mismatches.append('REQUIRED_CAPABILITIES_DIFFER')
    if source_plan.policy.get('rules_digest') != target_plan.policy.get('rules_digest'):
        mismatches.append('POLICY_RULE_SET_DIFFERS')
    if source_plan.policy.get('rules_failed', []) != target_plan.policy.get('rules_failed', []):
        mismatches.append('POLICY_OUTCOME_DIFFERS')

    blockers = list(mismatches)
    if not source_capability['qualified']:
        blockers.append('SOURCE_NATIVE_QUALIFICATION_ABSENT')
    if not target_capability['qualified']:
        blockers.append('TARGET_NATIVE_QUALIFICATION_ABSENT')

    return {
        'format': EQUIVALENCE_FORMAT,
        'source': {
            'platform': source_plan.desired_state.platform,
            'family': source_adapter.family,
            'capability': source_capability,
            'realization_gaps': [dict(row) for row in source_adapter.realization_gaps()],
        },
        'target': {
            'platform': target_plan.desired_state.platform,
            'family': target_adapter.family,
            'capability': target_capability,
            'realization_gaps': [dict(row) for row in target_adapter.realization_gaps()],
        },
        'required_capabilities': list(required),
        'semantic_mismatches': mismatches,
        'blockers': sorted(set(blockers)),
        'equivalent': not blockers,
        'native_contact': False,
    }
