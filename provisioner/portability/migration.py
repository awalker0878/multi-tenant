"""Fail-closed cross-platform workload mobility planning."""
from __future__ import annotations

from copy import deepcopy

from provisioner.domain.errors import ProvisioningError
from provisioner.domain.request import digest
from provisioner.portability import bundle as portability_bundle
from provisioner.portability import capabilities, cutover, data as data_transfer, policy_translation
from provisioner.schemas import registry

MIGRATION_FORMAT = 'hosting-workload-migration-plan/1'
MOBILITY_SCHEMA = 'workload-mobility'
MODES = ('rebuild-restore', 'image-convert', 'replicate')
IMPLEMENTED_MODES = ('rebuild-restore',)


def validate_intent(document: dict) -> dict:
    problems = registry.validate_named(document, MOBILITY_SCHEMA)
    if problems:
        first = problems[0]
        raise ProvisioningError(
            'SCHEMA_VALIDATION_FAILED',
            f'Mobility intent does not satisfy {MOBILITY_SCHEMA}: {first["message"]}',
            path=first['path'], details={'violations': problems})
    return document


def target_request(source_request: dict, mobility: dict) -> dict:
    """Project the same portable WSD intent onto the target placement."""
    result = deepcopy(source_request)
    target = mobility['spec']['target']
    result['spec']['platform']['preference'] = target['platform']
    result['spec']['placement']['region'] = target['region']
    result['spec']['placement']['site'] = target.get('site')
    result['spec']['placement']['cell'] = target.get('cell')
    return result


def source_request(source_request: dict, mobility: dict) -> dict:
    result = deepcopy(source_request)
    result['spec']['platform']['preference'] = mobility['spec']['source']['platform']
    return result


def _identity_matches(plan, mobility: dict) -> None:
    metadata = mobility['metadata']
    expected = (plan.request.tenant, plan.request.wsd, plan.request.owner)
    actual = (metadata['tenant'], metadata['name'], metadata['owner'])
    if expected != actual:
        raise ProvisioningError(
            'PORTABILITY_POLICY_MISMATCH',
            'Mobility intent identity does not match the portable workload request',
            path='$.metadata',
            details={'workload': list(expected), 'mobility': list(actual)})


def _transfer_blockers(plan, mobility: dict) -> list[str]:
    spec = mobility['spec']
    mode = spec['strategy']['mode']
    blockers = []
    if mode not in IMPLEMENTED_MODES:
        blockers.append(f'MIGRATION_MODE_NOT_IMPLEMENTED:{mode}')
    image = spec['artifact']['image']
    if not image.get('sha256'):
        blockers.append('WORKLOAD_ARTIFACT_INTEGRITY_UNBOUND')
    datasets = spec['data']['datasets']
    if not datasets:
        blockers.append('DATASET_TRANSFER_NOT_DECLARED')
    if any(row['method'] == 'backup-restore' for row in datasets)             and 'backup' not in plan.resolution.services:
        blockers.append('BACKUP_SERVICE_NOT_DECLARED')
    if spec['security']['secrets'] not in ('rebind', 'external-provider'):
        blockers.append('SECRET_STRATEGY_NOT_PORTABLE')
    if spec['security']['keys'] not in ('rebind', 'external-kms'):
        blockers.append('KEY_STRATEGY_NOT_PORTABLE')
    return blockers


def _stages(blockers: list[str]) -> list[dict]:
    transfer_held = any(item.startswith(('MIGRATION_MODE_', 'WORKLOAD_ARTIFACT_',
                                         'DATASET_TRANSFER_', 'BACKUP_SERVICE_'))
                        for item in blockers)
    qualification_held = any('NATIVE_QUALIFICATION' in item for item in blockers)
    return [
        {'stage': 'target-capability-gate',
         'status': 'HELD' if qualification_held else 'READY'},
        {'stage': 'target-environment-rebuild', 'status': 'READY'},
        {'stage': 'portable-policy-recompile', 'status': 'READY'},
        {'stage': 'service-identity-rebind', 'status': 'READY'},
        {'stage': 'workload-artifact-transfer',
         'status': 'HELD' if transfer_held else 'READY'},
        {'stage': 'dataset-transfer',
         'status': 'HELD' if transfer_held else 'READY'},
        {'stage': 'writer-fence-and-cutover', 'status': 'HELD_EXTERNAL_AUTHORITY'},
        {'stage': 'target-conformance', 'status': 'HELD_EXTERNAL_EVIDENCE'},
        {'stage': 'source-retirement', 'status': 'HELD_UNTIL_TARGET_ACCEPTED'},
    ]


def build(source_plan, target_plan, mobility: dict, artifact_resolutions: dict | None = None) -> dict:
    """Build a deterministic mobility plan; never execute or imply success."""
    mobility = validate_intent(mobility)
    _identity_matches(source_plan, mobility)
    _identity_matches(target_plan, mobility)
    if source_plan.desired_state.platform == target_plan.desired_state.platform:
        raise ProvisioningError(
            'PORTABILITY_POLICY_MISMATCH',
            'Cross-platform mobility requires distinct source and target platforms',
            path='$.spec.target.platform')

    portable = portability_bundle.build(source_plan)
    equivalence = capabilities.compare(source_plan, target_plan)
    translated_policy = policy_translation.compile(portable['policy'], target_plan)
    transfer_plan = data_transfer.compile(mobility, source_plan, target_plan)
    cutover_plan = cutover.compile(mobility, source_plan, target_plan)
    blockers = (list(equivalence['blockers'])
                + list(translated_policy['blockers'])
                + list(transfer_plan['blockers'])
                + _transfer_blockers(source_plan, mobility))
    artifact_resolutions = dict(artifact_resolutions or {})
    for side in ('source', 'target'):
        reference = artifact_resolutions.get(side)
        if reference and reference.get('status') != 'AUTHORITATIVE':
            blockers.append(f'{side.upper()}_ARTIFACT_MAPPING_NOT_AUTHORITATIVE')
    blockers = sorted(set(blockers))
    repository_blocked = any(item.startswith('MIGRATION_MODE_NOT_IMPLEMENTED')
                             for item in blockers)

    body = {
        'format': MIGRATION_FORMAT,
        'status': ('HELD_REPOSITORY_CAPABILITY_GAP' if repository_blocked
                   else 'PLANNED_DISABLED_NOT_AUTHORIZED'),
        'readiness': ('HELD' if blockers else 'READY_FOR_EXTERNAL_AUTHORITY'),
        'identity': dict(portable['identity']),
        'source': {
            'platform': source_plan.desired_state.platform,
            'site': source_plan.desired_state.site_key,
            'plan_digest': source_plan.digest,
        },
        'target': {
            'platform': target_plan.desired_state.platform,
            'site': target_plan.desired_state.site_key,
            'plan_digest': target_plan.digest,
        },
        'portability_bundle': portable,
        'equivalence': equivalence,
        'policy_translation': translated_policy,
        'data_transfer': transfer_plan,
        'cutover': cutover_plan,
        'transfer': deepcopy(mobility['spec']),
        'artifact_realizations': artifact_resolutions,
        'capabilities': capabilities.dimensions(source_plan),
        'blockers': blockers,
        'stages': _stages(blockers),
        'limits': [
            'This plan moves no data and contacts no platform',
            'Target qualification, writer fencing, data-owner acceptance and activation authority remain external',
            'A mandatory policy or capability mismatch is a hold and cannot be downgraded',
            'Source retirement is always after target conformance and explicit acceptance',
        ],
        'native_contact': False,
    }
    return {**body, 'digest': digest(body)}
