"""`hosting verify` — the conformance report and the verification plan.

Verification states what is proven, what is blocked on evidence produced
elsewhere, and what would have to be observed natively before activation. It never
claims service readiness.
"""
from __future__ import annotations

from provisioner.cli.support import EXIT_OK, EXIT_REFUSED
from provisioner.conformance import report as conformance_report
from provisioner.domain.errors import ProvisioningError
from provisioner.execution.service import (Context, address_evidence, capacity_evidence,
                                           plan_for)
from provisioner.observation import drift as drift_module
from provisioner.observation import health as health_module
from provisioner.observation import native as native_module
from provisioner.reconciliation import classify as reconciliation_classify
from provisioner.reconciliation import compare as reconciliation_compare

RESULT_FORMAT = 'hosting-verification-result/1'


def verification_plan(plan) -> list[dict]:
    """Every native subject that must be observed before this decision is verified."""
    subjects = native_module.expected_subjects(plan.desired_state)
    return [{'subject': subject, 'native_id': native_id,
             'method': 'native readback', 'status': 'NOT_OBSERVED',
             'generation': plan.generation, 'operation_id': plan.operation_id,
             'evidence_owner': 'platform-owner'}
            for subject, native_id in subjects]


def run(context: Context, observations=(), reservation_index=None,
        capacity_facts=None, allocation_index=None,
        registration_index=None) -> tuple[int, dict]:
    try:
        plan = plan_for(context)
    except ProvisioningError as error:
        return EXIT_REFUSED, {'format': RESULT_FORMAT, 'status': 'REFUSED',
                              'source': context.source, 'errors': [error.to_dict()],
                              'native_contact': False}

    capacity = capacity_evidence(plan, reservation_index, facts_path=capacity_facts)
    addresses = address_evidence(plan, reservation_index, allocation_index,
                                 registration_index)
    report = conformance_report.build(plan, observations, capacity=capacity,
                                      addresses=addresses)
    comparison = reconciliation_compare.build(plan.desired_state, observations)
    classification = reconciliation_classify.classify(comparison)
    drift = drift_module.to_dict(plan.desired_state, observations)
    health = health_module.to_dict(plan.desired_state, observations)
    bound = native_module.binding(observations, plan.generation)

    return EXIT_OK, {
        'format': RESULT_FORMAT, 'status': report['status'],
        'source': context.source, 'plan_digest': plan.digest,
        'manifest_digest': plan.manifest_digest,
        'request_digest': plan.request.digest,
        'generation': plan.generation,
        'identity': plan.identity.to_dict(),
        'operation_id': plan.operation_id,
        'conformance': report,
        'capacity': capacity,
        'addresses': addresses,
        'verification_plan': verification_plan(plan),
        'observations': native_module.to_dict(observations, plan.desired_state,
                                              plan.generation),
        'binding': bound,
        'drift': drift,
        'reconciliation': classification,
        'health': health,
        'activation': 'HELD',
        'native_contact': False,
        'limits': ['Verification is repository-side until native readback exists',
                   'Absent observation is never reported as in sync or healthy',
                   'An observation from another generation is reported stale, never accepted',
                   'The capacity confirmation check reports the owner state read from the '
                   'exported reservation records, and only the owner can satisfy it',
                   'The address and registration checks report the owner state read from '
                   'the exported IPAM and DNS records, and only those owners can satisfy them']}


def to_dict(context: Context) -> dict:
    return {'format': RESULT_FORMAT, 'native_contact': False}