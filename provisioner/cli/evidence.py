"""`hosting evidence` — the repository-side evidence records for one decision.

Every record binds an artifact to the request digest it came from and states the
stage it proves. No record claims native acceptance, qualification or service
readiness, because none of those can be produced here.
"""
from __future__ import annotations

from provisioner.cli.support import EXIT_OK, EXIT_REFUSED
from provisioner.domain import evidence as evidence_module
from provisioner.domain import generation as generation_module
from provisioner.domain.errors import ProvisioningError
from provisioner.domain.request import digest as request_digest
from provisioner.execution.service import (Context, address_evidence, capacity_evidence,
                                           plan_for)

RESULT_FORMAT = 'hosting-evidence-result/1'

REPOSITORY_LIMITS = ('Evidence records are repository-side only',
                     'No record is a native acceptance or qualification result',
                     'Every record is bound to one WSD generation')


def records(plan, capacity=None, addresses=None) -> list[dict]:
    """One evidence record per repository-side artifact the plan produced.

    `capacity` and `addresses` are the reconciled owner evidence the transport read,
    if any. The capacity record states the capacity owner's state and the allocation
    and registration records state the addressing owners' state; none of them is a
    record of our own authority over capacity, addresses or names.
    """
    request_digest_value = plan.request.digest
    generation = plan.generation
    rows = [
        evidence_module.record(
            'request', f'{plan.request.tenant}/{plan.request.wsd}', request_digest_value,
            request_digest_value, 'request', 'RECORDED',
            {'source': plan.request.source, 'apiVersion': plan.request.api_version,
             'kind': plan.request.kind}, REPOSITORY_LIMITS, generation),
        evidence_module.record(
            'validation', f'{plan.request.tenant}/{plan.request.wsd}', request_digest_value,
            request_digest(plan.policy), 'validated', 'PASSED',
            {'rules_evaluated': plan.policy.get('rules_evaluated'),
             'rules_digest': plan.policy.get('rules_digest', ''),
             'rules_failed': plan.policy.get('rules_failed', [])}, REPOSITORY_LIMITS,
            generation),
        evidence_module.record(
            'resolution', f'{plan.request.tenant}/{plan.request.wsd}', request_digest_value,
            request_digest(plan.resolution.to_dict()), 'resolved', 'RESOLVED',
            {'profiles': dict(plan.resolution.profiles)}, REPOSITORY_LIMITS, generation),
        evidence_module.record(
            'placement', f'{plan.request.tenant}/{plan.request.wsd}', request_digest_value,
            plan.decision.digest, 'placed', plan.decision.status,
            {'authority': plan.decision.authority, 'site': plan.decision.site_key,
             'cell': plan.decision.cell_key}, REPOSITORY_LIMITS, generation),
        evidence_module.record(
            'compilation', f'{plan.request.tenant}/{plan.request.wsd}', request_digest_value,
            request_digest(plan.environment), 'compiled', 'COMPILED',
            {'files': sorted(plan.compiled),
             'environment_digest': request_digest(plan.environment)}, REPOSITORY_LIMITS,
            generation),
        evidence_module.record(
            'generation', f'{plan.request.tenant}/{plan.request.wsd}', request_digest_value,
            request_digest(plan.identity.to_dict()), 'claimed', 'CLAIMED_BY_CALLER',
            {'generation': generation, 'identity': plan.identity.key,
             'identity_digest': plan.identity.digest, 'operation_id': plan.operation_id,
             'desired_state_digest': plan.desired_state.digest,
             'authority': generation_module.to_dict()['authority']},
            REPOSITORY_LIMITS, generation),
        evidence_module.record(
            'plan', f'{plan.request.tenant}/{plan.request.wsd}', request_digest_value,
            plan.digest, 'planned', plan.status,
            {'manifest_digest': plan.manifest_digest,
             'terraform_scopes': len(plan.terraform_scopes),
             'ansible_scopes': len(plan.ansible_scopes),
             'blocking_operations': plan.delivery.get('blocking', [])}, REPOSITORY_LIMITS,
            generation),
        evidence_module.record(
            'conformance', f'{plan.request.tenant}/{plan.request.wsd}', request_digest_value,
            request_digest(plan.conformance), 'planned', plan.conformance['status'],
            {'failed': plan.conformance['failed'],
             'pending': plan.conformance['pending']}, REPOSITORY_LIMITS, generation),
    ]
    if capacity is not None:
        rows.append(evidence_module.record(
            'capacity', f'{plan.request.tenant}/{plan.request.wsd}', request_digest_value,
            capacity['view']['digest'], 'capacity', capacity['state'],
            {'state': capacity['state'], 'confirmed': capacity['confirmed'],
             'may_allocate': capacity['may_allocate'],
             'operation_id': plan.operation_id,
             'reservation_id': capacity['binding']['reservation_id'],
             'view_digest': capacity['view']['digest'],
             'records_checked': capacity['reconciliation']['records_checked'],
             'authority': 'CAPACITY_OWNER'}, REPOSITORY_LIMITS, generation))
    if addresses is not None:
        allocations = addresses['reconciliation']['allocations']
        zones = [{'zone': item['zone'], 'state': item['state'],
                  'registration_state': item['registration_state'],
                  'next_owner_action': item['next_owner_action']}
                 for item in allocations]
        registrations = [{'zone': item['zone'], 'registration_id': item['registration_id'],
                          'state': item['registration_state'],
                          'next_owner_action': item['next_owner_action']}
                         for item in allocations]
        rows.append(evidence_module.record(
            'allocation', f'{plan.request.tenant}/{plan.request.wsd}', request_digest_value,
            addresses['view']['digest'], 'allocated', addresses['state'],
            {'state': addresses['state'], 'confirmed': addresses['confirmed'],
             'may_allocate': addresses['may_allocate'],
             'parent_state': addresses['reconciliation']['parent']['state'],
             'operation_id': plan.operation_id,
             'reservation_id': addresses['reconciliation']['reservation_id'],
             'view_digest': addresses['view']['digest'], 'zones': zones,
             'records_checked': addresses['reconciliation']['records_checked'],
             'authority': 'IPAM_OWNER'}, REPOSITORY_LIMITS, generation))
        rows.append(evidence_module.record(
            'registration', f'{plan.request.tenant}/{plan.request.wsd}', request_digest_value,
            request_digest(addresses['review']), 'allocated', addresses['review']['state'],
            {'state': addresses['review']['state'],
             'registered': addresses['registered'],
             'may_register': addresses['may_register'],
             'operation_id': plan.operation_id,
             'view_digest': addresses['view']['digest'],
             'zones': registrations,
             'authority': 'DNS_OWNER'}, REPOSITORY_LIMITS, generation))
    return [row.to_dict() for row in rows]


def run(context: Context, reservation_index=None, capacity_facts=None,
        allocation_index=None, registration_index=None) -> tuple[int, dict]:
    try:
        plan = plan_for(context)
    except ProvisioningError as error:
        return EXIT_REFUSED, {'format': RESULT_FORMAT, 'status': 'REFUSED',
                              'source': context.source, 'errors': [error.to_dict()],
                              'native_contact': False}
    capacity = capacity_evidence(plan, reservation_index, facts_path=capacity_facts)
    addresses = address_evidence(plan, reservation_index, allocation_index,
                                 registration_index)
    rows = records(plan, capacity, addresses)
    return EXIT_OK, {'format': RESULT_FORMAT, 'status': 'RECORDED',
                     'source': context.source, 'plan_digest': plan.digest,
                     'manifest_digest': plan.manifest_digest,
                     'request_digest': plan.request.digest,
                     'generation': plan.generation,
                     'operation_id': plan.operation_id,
                     'count': len(rows), 'evidence': rows,
                     'external_stages': ['approved', 'executed', 'observed', 'verified',
                                         'activated'],
                     'native_contact': False, 'limits': list(REPOSITORY_LIMITS)}