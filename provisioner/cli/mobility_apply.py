"""hosting mobility-apply — compile an approved mobility plan to delivery v2 and refuse.

The command never executes a migration. It proves the supplied approval cites the
exact mobility decision, requires that decision to be unblocked, binds one clean
source commit, compiles the target-side graph accepted by the existing delivery
runner, and returns that handoff with an explicit execution refusal.
"""
from __future__ import annotations

from provisioner.cli.support import EXIT_REFUSED
from provisioner.domain.errors import ProvisioningError
from provisioner.execution import authority as authority_module
from provisioner.execution import handoff as delivery_handoff
from provisioner.execution import source as source_module
from provisioner.execution.service import Context, mobility_session_for
from provisioner.portability import handoff as mobility_handoff

RESULT_FORMAT = 'hosting-mobility-apply-result/1'
HANDOFF_STATUS = 'EXECUTION_REFUSED_HANDOFF_READY'


def _refuse(error: ProvisioningError, context: Context, plan=None) -> tuple[int, dict]:
    payload = {'format': RESULT_FORMAT, 'status': 'REFUSED',
               'request_source': context.source, 'errors': [error.to_dict()],
               'native_contact': False}
    if plan is not None:
        payload['plan_digest'] = plan.get('digest')
        payload['blockers'] = list(plan.get('blockers', []))
    return EXIT_REFUSED, payload


def run(context: Context, mobility_intent, target_inventory=None, artifact_registry=None,
        approved_plan: str | None = None, approvals=(),
        source_commit: str | None = None) -> tuple[int, dict]:
    if not mobility_intent:
        return _refuse(ProvisioningError(
            'SCHEMA_VALIDATION_FAILED',
            'mobility-apply requires --mobility-intent',
            path='$.mobility'), context)

    try:
        session = mobility_session_for(context, mobility_intent, target_inventory,
                                       artifact_registry)
    except ProvisioningError as error:
        return _refuse(error, context)

    plan = session.migration_plan
    if not approved_plan:
        return _refuse(ProvisioningError(
            'AUTHORITY_REQUIRED',
            'Mobility apply requires the digest of an already reviewed mobility plan',
            path='$.apply',
            details={'plan_digest': plan['digest'],
                     'instruction': 'hosting mobility-apply <request> '
                                    '--mobility-intent <mobility.yaml> '
                                    '--approved-plan <digest>'}), context, plan)

    if approved_plan != plan['digest']:
        return _refuse(ProvisioningError(
            'ARTIFACT_INTEGRITY_FAILED',
            'The approved digest does not cite the mobility plan produced from these inputs',
            path='$.apply',
            details={'approved_plan': approved_plan,
                     'plan_digest': plan['digest']}), context, plan)

    if plan.get('blockers') or plan.get('readiness') != 'READY_FOR_EXTERNAL_AUTHORITY':
        return _refuse(ProvisioningError(
            'MIGRATION_NOT_READY',
            'The reviewed mobility decision remains held',
            path='$.migration',
            details={'readiness': plan.get('readiness'),
                     'blockers': list(plan.get('blockers', []))}), context, plan)

    try:
        approval = authority_module.require_approval(plan['digest'], approvals)
        commit, source = source_module.bind(
            source_commit,
            instruction='hosting mobility-apply <request> --mobility-intent <mobility.yaml> '
                        '--approved-plan <digest> --source-commit <40-hex commit>')
        graph = mobility_handoff.build(session.target_plan, plan, commit)
    except ProvisioningError as error:
        return _refuse(error, context, plan)

    refusal = ProvisioningError(
        'EXECUTION_REFUSED',
        'This repository holds no migration execution authority; the approved mobility '
        'plan is handed to the existing delivery runner',
        path='$.apply',
        details={'plan_digest': plan['digest'], 'source_commit': commit,
                 'operation_id': graph['operation_id']})
    return EXIT_REFUSED, {
        'format': RESULT_FORMAT,
        'status': HANDOFF_STATUS,
        'request_source': context.source,
        'mobility_source': str(session.mobility_path),
        'plan_digest': plan['digest'],
        'approval': approval.to_dict(),
        'source': dict(plan['source']),
        'target': dict(plan['target']),
        'source_commit': commit,
        'source_checkout': {'status': source['status'], 'commit': source['commit']},
        'delivery': graph,
        'delivery_review': delivery_handoff.review(graph),
        'policy_translation': plan['policy_translation'],
        'data_transfer': plan['data_transfer'],
        'cutover': plan['cutover'],
        'artifact_realizations': plan['artifact_realizations'],
        'native_contact': False,
        'errors': [refusal.to_dict()],
        'limits': [
            'The existing delivery runner is the only execution engine',
            'Source writer fencing and source retirement remain separate source-side authority',
            'A delivery handoff is not native qualification, migration success or activation',
        ],
    }
