"""Portable dataset transfer planning for workload mobility."""
from __future__ import annotations

from provisioner.domain.request import digest

FORMAT = 'hosting-portable-data-transfer-plan/1'
IMPLEMENTED_METHODS = ('backup-restore',)


def compile(mobility: dict, source_plan, target_plan) -> dict:
    """Compile dataset intent into owner handoffs without moving any data."""
    rows = []
    blockers = []
    source_services = set(source_plan.resolution.services)
    target_services = set(target_plan.resolution.services)

    for dataset in mobility['spec']['data']['datasets']:
        method = dataset['method']
        row_blockers = []
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
            'delivery_kind': 'restic' if method == 'backup-restore' else None,
            'delivery_action': 'restore' if method == 'backup-restore' else None,
            'status': 'PLANNED_OWNER_HANDOFF' if not row_blockers else 'HELD',
            'blockers': row_blockers,
        })

    body = {
        'format': FORMAT,
        'datasets': rows,
        'blockers': sorted(set(blockers)),
        'ready': not blockers,
        'limits': [
            'A dataset reference and digest identify source state; they do not prove a usable restore',
            'The data owner supplies credentials and target storage under separate authority',
            'Application consistency must be proven by the selected transfer method and acceptance test',
        ],
        'native_contact': False,
    }
    return {**body, 'digest': digest(body)}
