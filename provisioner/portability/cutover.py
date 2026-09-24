"""Cross-platform cutover and rollback contract."""
from __future__ import annotations

from provisioner.domain.request import digest

FORMAT = 'hosting-portable-cutover-plan/1'


def compile(mobility: dict, source_plan, target_plan) -> dict:
    cutover = mobility['spec']['cutover']
    body = {
        'format': FORMAT,
        'source': {
            'platform': source_plan.desired_state.platform,
            'site': source_plan.desired_state.site_key,
            'generation': source_plan.generation,
        },
        'target': {
            'platform': target_plan.desired_state.platform,
            'site': target_plan.desired_state.site_key,
            'generation': target_plan.generation,
        },
        'objectives': {
            'max_downtime_seconds': cutover['maxDowntimeSeconds'],
            'max_data_loss_seconds': cutover['maxDataLossSeconds'],
            'rollback_window_seconds': cutover['rollbackWindowSeconds'],
        },
        'required_evidence': [
            'source-writer-fenced',
            'final-data-consistency-point',
            'target-policy-conformance',
            'target-service-conformance',
            'target-production-authorization',
            'post-cutover-useful-service-test',
        ],
        'rollback': {
            'allowed_before_target_writes': True,
            'after_target_writes': 'requires-reverse-sync-or-restore-decision',
            'source_restart_without_reconciliation': 'forbidden',
        },
        'source_retirement': {
            'status': 'HELD_UNTIL_TARGET_ACCEPTED_AND_ROLLBACK_WINDOW_DECIDED',
            'requires': ['target-accepted', 'retained-data-decision', 'dns-route-withdrawal'],
        },
        'status': 'HELD_EXTERNAL_EVIDENCE',
        'native_contact': False,
        'limits': [
            'A timeout or lost response never proves fencing, cutover or rollback succeeded',
            'Source retirement is a separate source-scope operation after target acceptance',
            'Any writer switch requires explicit authority and generation-bound evidence',
        ],
    }
    return {**body, 'digest': digest(body)}
