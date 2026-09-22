"""`hosting evidence` — the repository-side evidence records for one decision.

Every record binds an artifact to the request digest it came from and states the
stage it proves. No record claims native acceptance, qualification or service
readiness, because none of those can be produced here.
"""
from __future__ import annotations

from provisioner.cli import plan as plan_command
from provisioner.cli.support import EXIT_OK, EXIT_REFUSED, Context
from provisioner.domain import evidence as evidence_module
from provisioner.domain.errors import ProvisioningError
from provisioner.domain.request import digest as request_digest

RESULT_FORMAT = 'hosting-evidence-result/1'

REPOSITORY_LIMITS = ('Evidence records are repository-side only',
                     'No record is a native acceptance or qualification result')


def records(plan) -> list[dict]:
    """One evidence record per repository-side artifact the plan produced."""
    request_digest_value = plan.request.digest
    rows = [
        evidence_module.record(
            'request', f'{plan.request.tenant}/{plan.request.wsd}', request_digest_value,
            request_digest_value, 'request', 'RECORDED',
            {'source': plan.request.source, 'apiVersion': plan.request.api_version,
             'kind': plan.request.kind}, REPOSITORY_LIMITS),
        evidence_module.record(
            'validation', f'{plan.request.tenant}/{plan.request.wsd}', request_digest_value,
            request_digest(plan.policy), 'validated', 'PASSED',
            {'rules_evaluated': plan.policy.get('rules_evaluated'),
             'rules_failed': plan.policy.get('rules_failed', [])}, REPOSITORY_LIMITS),
        evidence_module.record(
            'resolution', f'{plan.request.tenant}/{plan.request.wsd}', request_digest_value,
            request_digest(plan.resolution.to_dict()), 'resolved', 'RESOLVED',
            {'profiles': dict(plan.resolution.profiles)}, REPOSITORY_LIMITS),
        evidence_module.record(
            'placement', f'{plan.request.tenant}/{plan.request.wsd}', request_digest_value,
            plan.decision.digest, 'placed', plan.decision.status,
            {'authority': plan.decision.authority, 'site': plan.decision.site_key,
             'cell': plan.decision.cell_key}, REPOSITORY_LIMITS),
        evidence_module.record(
            'compilation', f'{plan.request.tenant}/{plan.request.wsd}', request_digest_value,
            request_digest(plan.environment), 'compiled', 'COMPILED',
            {'files': sorted(plan.compiled),
             'environment_digest': request_digest(plan.environment)}, REPOSITORY_LIMITS),
        evidence_module.record(
            'plan', f'{plan.request.tenant}/{plan.request.wsd}', request_digest_value,
            plan.digest, 'planned', plan.status,
            {'terraform_scopes': len(plan.terraform_scopes),
             'ansible_scopes': len(plan.ansible_scopes),
             'blocking_operations': plan.delivery.get('blocking', [])}, REPOSITORY_LIMITS),
        evidence_module.record(
            'conformance', f'{plan.request.tenant}/{plan.request.wsd}', request_digest_value,
            request_digest(plan.conformance), 'planned', plan.conformance['status'],
            {'failed': plan.conformance['failed'],
             'pending': plan.conformance['pending']}, REPOSITORY_LIMITS),
    ]
    return [row.to_dict() for row in rows]


def run(context: Context) -> tuple[int, dict]:
    try:
        plan = plan_command.plan_for(context)
    except ProvisioningError as error:
        return EXIT_REFUSED, {'format': RESULT_FORMAT, 'status': 'REFUSED',
                              'source': context.source, 'errors': [error.to_dict()],
                              'native_contact': False}
    rows = records(plan)
    return EXIT_OK, {'format': RESULT_FORMAT, 'status': 'RECORDED',
                     'source': context.source, 'plan_digest': plan.digest,
                     'request_digest': plan.request.digest,
                     'count': len(rows), 'evidence': rows,
                     'external_stages': ['approved', 'executed', 'observed', 'verified',
                                         'activated'],
                     'native_contact': False, 'limits': list(REPOSITORY_LIMITS)}