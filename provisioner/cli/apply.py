"""`hosting apply` — refuse to execute, and hand the exact plan to its owners.

This repository plans. It does not hold approval authority, does not contact a
native platform and does not run Terraform. Apply therefore always refuses, but it
refuses usefully: it binds the caller's approval to one immutable plan digest and
emits the exact owner operations that a human must perform.
"""
from __future__ import annotations

from pathlib import Path

from provisioner.cli.support import EXIT_REFUSED
from provisioner.domain import generation as generation_module
from provisioner.domain.errors import ProvisioningError
from provisioner.execution import authority as authority_module
from provisioner.execution import delivery as delivery_module
from provisioner.execution import manifest as manifest_module
from provisioner.execution.service import Context, plan_for

RESULT_FORMAT = 'hosting-apply-result/1'


def load_approvals(path) -> tuple:
    """Read recorded approvals. An approval is external evidence, never a request field."""
    if path is None:
        return ()
    document = authority_module.load_approvals(Path(path))
    return tuple(document)


def refuse(code: str, message: str, context: Context, **details) -> tuple[int, dict]:
    error = ProvisioningError(code, message, path='$.apply', details=details)
    return EXIT_REFUSED, {'format': RESULT_FORMAT, 'status': 'REFUSED',
                          'source': context.source, 'errors': [error.to_dict()],
                          'native_contact': False,
                          'limits': ['This repository never executes a change']}


def run(context: Context, approved_plan: str | None = None,
        approvals=()) -> tuple[int, dict]:
    try:
        plan = plan_for(context)
    except ProvisioningError as error:
        return EXIT_REFUSED, {'format': RESULT_FORMAT, 'status': 'REFUSED',
                              'source': context.source, 'errors': [error.to_dict()],
                              'native_contact': False}

    if not approved_plan:
        return refuse('AUTHORITY_REQUIRED',
                      'Apply requires the digest of an already reviewed plan',
                      context, plan_digest=plan.digest,
                      manifest_digest=plan.manifest_digest,
                      instruction='hosting apply <request> --approved-plan <digest>')

    if approved_plan != plan.digest:
        return refuse('ARTIFACT_INTEGRITY_FAILED',
                      'The approved digest does not cite the plan produced from this request',
                      context, approved_plan=approved_plan, plan_digest=plan.digest,
                      manifest_digest=plan.manifest_digest)

    try:
        approval = authority_module.require_approval(plan.digest, approvals)
    except ProvisioningError as error:
        return EXIT_REFUSED, {'format': RESULT_FORMAT, 'status': 'REFUSED',
                              'source': context.source, 'errors': [error.to_dict()],
                              'plan_digest': plan.digest, 'native_contact': False,
                              'limits': ['This repository never executes a change']}

    handoff = {
        'format': RESULT_FORMAT, 'status': 'EXECUTION_REFUSED_REPOSITORY_PLAN_ONLY',
        'source': context.source, 'plan_digest': plan.digest,
        'manifest_digest': plan.manifest_digest,
        'manifest': dict(plan.manifest),
        'reviewed': manifest_module.review(plan.manifest),
        'request_digest': plan.request.digest, 'approval': approval.to_dict(),
        'generation': plan.generation,
        'identity': plan.identity.to_dict(),
        'operation_id': plan.operation_id,
        'generation_record': generation_module.record_for(plan).to_dict(),
        'authority': authority_module.to_dict(),
        'phases': [dict(p) for p in plan.phases],
        'terraform_scopes': [dict(s) for s in plan.terraform_scopes],
        'ansible_scopes': [dict(s) for s in plan.ansible_scopes],
        'operations': plan.delivery.get('operations', []),
        'blocking': plan.delivery.get('blocking', []),
        'conformance': plan.conformance.get('status'),
        'native_contact': False,
        'limits': ['Every operation is performed by its named owner',
                   'Terraform execution and state remain with the stack owner',
                   'This repository holds no execution authority',
                   'A handoff carries one generation; the authoritative record decides '
                   'whether it is still current',
                   'The approved digest binds the complete reviewed manifest, not a summary'],
    }
    error = ProvisioningError(
        'EXECUTION_REFUSED',
        'This repository holds no execution authority; the plan is handed to its owners',
        path='$.apply',
        details={'plan_digest': plan.digest,
                 'manifest_digest': plan.manifest_digest,
                 'blocking': handoff['blocking'],
                 'handoff_operations': [o['name'] for o in handoff['operations']]})
    return EXIT_REFUSED, {**handoff, 'errors': [error.to_dict()]}


def require_unblocked(plan) -> None:
    """Refuse while a blocking owner operation is outstanding."""
    delivery_module.require_unblocked(plan.delivery)