"""Portable dataset transfer planning for workload mobility."""
from __future__ import annotations

from provisioner.domain.request import digest
from provisioner.domain.errors import ProvisioningError

FORMAT = 'hosting-portable-data-transfer-plan/1'
IMPLEMENTED_METHODS = ('backup-restore',)


def compile(mobility: dict, source_plan, target_plan) -> dict:
    """Compile dataset intent into owner handoffs without moving any data."""
    rows = []
    blockers = []
    seen = {field: set() for field in ('name', 'datasetId', 'targetRef', 'sha256')}
    groups = {}
    source_services = set(source_plan.resolution.services)
    target_services = set(target_plan.resolution.services)

    for dataset in mobility['spec']['data']['datasets']:
        method = dataset['method']
        binding = dataset.get('transferManifest')
        row_blockers = []
        identities = {'name': dataset['name'], **(binding or {})}
        for field in seen:
            value = identities.get(field)
            if value is not None:
                if value in seen[field]:
                    raise ProvisioningError('SCHEMA_VALIDATION_FAILED',
                        f'Duplicate dataset transfer {field}', path='$.spec.data.datasets')
                seen[field].add(value)
        if binding is None:
            row_blockers.append(f'DATASET_TRANSFER_BINDING_ABSENT:{dataset["name"]}')
        else:
            groups.setdefault(binding['consistencyGroupId'], []).append(dataset['name'])
        if method not in IMPLEMENTED_METHODS:
            row_blockers.append(f'DATA_TRANSFER_METHOD_NOT_IMPLEMENTED:{method}')
        if method == 'backup-restore':
            if 'backup' not in source_services:
                row_blockers.append('SOURCE_BACKUP_SERVICE_NOT_DECLARED')
            if 'backup' not in target_services:
                row_blockers.append('TARGET_BACKUP_SERVICE_NOT_DECLARED')
        blockers.extend(row_blockers)
        rows.append({
            'name': dataset['name'],
            'method': method,
            'consistency': dataset['consistency'],
            'source_ref': dataset['sourceRef'],
            'source_sha256': dataset['sha256'],
            'owner': 'backup-service-owner' if method == 'backup-restore' else 'external-data-owner',
            'delivery_kind': 'dataset_restore' if method == 'backup-restore' else None,
            'delivery_action': 'restore' if method == 'backup-restore' else None,
            'transfer_binding': ({'dataset_id': binding['datasetId'],
                                  'target_ref': binding['targetRef'],
                                  'consistency_group_id': binding['consistencyGroupId'],
                                  'transfer_manifest_sha256': binding['sha256']}
                                 if binding else None),
            'source_scope': dict(source_plan.identity.scope),
            'destination_scope': dict(target_plan.identity.scope),
            'verified': False,
            'native_qualified': False,
            'status': 'PLANNED_OWNER_HANDOFF' if not row_blockers else 'HELD',
            'blockers': row_blockers,
        })

    body = {
        'format': FORMAT,
        'datasets': rows,
        'consistency_groups': [{'group_id': group, 'dataset_names': names,
                                'status': 'PLANNED_UNVERIFIED'}
                               for group, names in sorted(groups.items())],
        'verified': False,
        'native_qualified': False,
        'blockers': sorted(set(blockers)),
        'ready': not blockers,
        'limits': [
            'A dataset reference and digest identify source state; they do not prove a usable restore',
            'Every dataset requires its own immutable transfer manifest and verified destination receipt',
            'Consistency-group byte verification does not prove application consistency or native qualification',
            'The data owner supplies credentials and target storage under separate authority',
            'Application consistency must be proven by the selected transfer method and acceptance test',
        ],
        'native_contact': False,
    }
    return {**body, 'digest': digest(body)}
