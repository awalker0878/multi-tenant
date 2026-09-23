"""`hosting apply` — refuse to execute, and hand the exact plan to its owners.

This repository plans. It does not hold approval authority, does not contact a
native platform and does not run Terraform. Apply therefore always refuses, but it
refuses usefully: it binds the caller's approval to one immutable plan digest and
emits the exact owner operations that a human must perform.
"""
from __future__ import annotations

from pathlib import Path

from provisioner.allocations import addresses as address_owner
from provisioner.allocations import owner as capacity_owner
from provisioner.cli.support import EXIT_REFUSED
from provisioner.domain import generation as generation_module
from provisioner.domain.errors import ProvisioningError
from provisioner.execution import authority as authority_module
from provisioner.execution import delivery as delivery_module
from provisioner.execution import handoff as handoff_module
from provisioner.execution import manifest as manifest_module
from provisioner.execution.service import (Context, address_evidence, capacity_evidence,
                                           plan_for)
from provisioner import repository

RESULT_FORMAT = 'hosting-apply-result/1'
HANDOFF_STATUS = 'EXECUTION_REFUSED_HANDOFF_READY'
NO_CHECKOUT = 'BLOCKED_NO_CURRENT_CHECKOUT'


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


def bind_source_commit(plan, requested: str | None) -> tuple:
    """Bind one exact clean source commit, or refuse before anything is compiled.

    The delivery runner refuses a handoff whose `source_commit` is not the clean
    checkout it is running from, so the repository refuses first rather than
    emitting a graph that cannot be accepted.
    """
    source = repository.source_commit()
    commit = source['commit']
    if requested is not None:
        if not handoff_module.SOURCE_COMMIT.match(requested):
            raise ProvisioningError(
                'SCHEMA_VALIDATION_FAILED',
                'A delivery handoff binds one exact clean source commit',
                path='$.apply', details={'source_commit': requested})
        if source['status'] != NO_CHECKOUT and requested != commit:
            raise ProvisioningError(
                'ARTIFACT_INTEGRITY_FAILED',
                'The declared source commit is not the commit under review',
                path='$.apply',
                details={'source_commit': requested, 'checkout_commit': commit})
        return requested, source
    if source['status'] != 'HASHES_MATCH':
        raise ProvisioningError(
            'ARTIFACT_INTEGRITY_FAILED',
            'A delivery handoff binds one exact clean source commit',
            path='$.apply',
            details={'status': source['status'], 'issues': source['issues'],
                     'instruction': 'hosting apply <request> --approved-plan <digest> '
                                    '--source-commit <40-hex commit>'})
    return commit, source


def run(context: Context, approved_plan: str | None = None,
        approvals=(), source_commit: str | None = None,
        reservation_index=None, capacity_facts=None,
        allocation_index=None, registration_index=None) -> tuple[int, dict]:
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

    try:
        commit, source = bind_source_commit(plan, source_commit)
        capacity = capacity_evidence(plan, reservation_index, facts_path=capacity_facts)
        capacity_owner.require_settled(capacity['reconciliation'])
        addresses = address_evidence(plan, reservation_index, allocation_index,
                                     registration_index)
        address_owner.require_settled(addresses['reconciliation'])
        graph = handoff_module.build(plan, commit)
    except ProvisioningError as error:
        return EXIT_REFUSED, {'format': RESULT_FORMAT, 'status': 'REFUSED',
                              'source': context.source, 'errors': [error.to_dict()],
                              'plan_digest': plan.digest, 'native_contact': False,
                              'limits': ['This repository never executes a change']}

    handoff = {
        'format': RESULT_FORMAT, 'status': HANDOFF_STATUS,
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
        'source_commit': commit,
        'source_checkout': {'status': source['status'], 'commit': source['commit']},
        'delivery': graph,
        'delivery_review': handoff_module.review(graph),
        'capacity': dict(capacity),
        'capacity_review': capacity['review'],
        'capacity_owner_handoff': capacity['handoff'],
        'addresses': dict(addresses),
        'address_review': addresses['review'],
        'address_owner_handoff': addresses['handoff'],
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
                   'The compiled graph is executed by the existing delivery runner, '
                   'which owns the journal, the stage packets and the recovery model',
                   'Each stage packet is prepared and authorised by the owner of its step',
                   'A handoff carries one generation; the authoritative record decides '
                   'whether it is still current',
                   'The approved digest binds the complete reviewed manifest, not a summary',
                   'A capacity reservation is a compiled proposal until the authoritative '
                   'owner confirms it; this repository never holds capacity',
                   'An address is a compiled proposal until the authoritative IPAM owner '
                   'confirms it; this repository never holds an address',
                   'A name is registered only by the authoritative DNS owner, and only '
                   'after the bound allocation is confirmed',
                   'Addressing is released in owner order: dependent DNS and native state '
                   'withdraws before reusable addressing is released'],
    }
    error = ProvisioningError(
        'EXECUTION_REFUSED',
        'This repository holds no execution authority; the plan is handed to its owners',
        path='$.apply',
        details={'plan_digest': plan.digest,
                 'manifest_digest': plan.manifest_digest,
                 'source_commit': commit,
                 'capacity_state': capacity['state'],
                 'address_state': addresses['state'],
                 'reservation_id': capacity['binding']['reservation_id'],
                 'blocking': handoff['blocking'],
                 'handoff_operations': [o['name'] for o in handoff['operations']]})
    return EXIT_REFUSED, {**handoff, 'errors': [error.to_dict()]}


def require_unblocked(plan) -> None:
    """Refuse while a blocking owner operation is outstanding."""
    delivery_module.require_unblocked(plan.delivery)