"""`hosting status` — read one plan back as a stage-by-stage status.

Status never invents progress. A stage is only reported as reached when the
artifact that proves it exists for the same request digest, and every stage that
requires external evidence is reported as held.
"""
from __future__ import annotations

from provisioner.cli.support import EXIT_OK, EXIT_REFUSED
from provisioner.domain.errors import ProvisioningError
from provisioner.domain.lifecycle import (EXTERNAL_EVIDENCE_STAGES, REPOSITORY_STAGES,
                                          STAGES)
from provisioner.execution.service import Context, plan_for

RESULT_FORMAT = 'hosting-status-result/1'

# Which stage each repository-side artifact proves, in pipeline order.
ARTIFACT_STAGES = (('request', 'request'), ('normalized', 'normalized'),
                   ('validated', 'validated'), ('resolved', 'resolved'),
                   ('placed', 'placed'), ('allocated', 'allocated'),
                   ('compiled', 'compiled'), ('planned', 'planned'))


def run(context: Context) -> tuple[int, dict]:
    try:
        plan = plan_for(context)
    except ProvisioningError as error:
        return EXIT_REFUSED, {'format': RESULT_FORMAT, 'status': 'REFUSED',
                              'source': context.source, 'errors': [error.to_dict()],
                              'native_contact': False}

    reached = ['request', 'normalized', 'validated', 'resolved']
    reached.append('placed')
    reached.append('allocated')
    if plan.compiled:
        reached.append('compiled')
    reached.append('planned')
    reached = [s for s in STAGES if s in reached]

    held = [{'stage': stage,
             'reason': 'Evidence must be produced outside this repository'}
            for stage in STAGES if stage in EXTERNAL_EVIDENCE_STAGES]

    return EXIT_OK, {
        'format': RESULT_FORMAT, 'status': plan.status, 'source': context.source,
        'subject': f'{plan.request.tenant}/{plan.request.wsd}',
        'request_digest': plan.request.digest, 'plan_digest': plan.digest,
        'stages': [{'stage': s, 'status': 'REACHED'} for s in reached] +
                  [{'stage': s['stage'], 'status': 'HELD'} for s in held],
        'repository_stages': list(REPOSITORY_STAGES),
        'phases': [dict(p) for p in plan.phases],
        'placement': {'status': plan.decision.status, 'authority': plan.decision.authority,
                      'site': plan.decision.site_key, 'cell': plan.decision.cell_key},
        'delivery': {'blocking': plan.delivery.get('blocking', []),
                     'operations': len(plan.delivery.get('operations', []))},
        'conformance': {'status': plan.conformance.get('status'),
                        'failed': plan.conformance.get('failed', []),
                        'pending': plan.conformance.get('pending', [])},
        'activation': 'HELD',
        'native_contact': False,
        'limits': ['A reached stage is a repository artifact, not native state',
                   'No stage beyond planning can be reached without external evidence']}


def to_dict(context: Context) -> dict:
    """Read-only status projection used by tests."""
    return {'format': RESULT_FORMAT, 'stages': list(STAGES),
            'repository_stages': list(REPOSITORY_STAGES),
            'external_evidence_stages': list(EXTERNAL_EVIDENCE_STAGES)}