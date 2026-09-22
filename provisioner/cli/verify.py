"""`hosting verify` — the conformance report and the verification plan.

Verification states what is proven, what is blocked on evidence produced
elsewhere, and what would have to be observed natively before activation. It never
claims service readiness.
"""
from __future__ import annotations

from provisioner.cli import plan as plan_command
from provisioner.cli.support import EXIT_OK, EXIT_REFUSED, Context
from provisioner.conformance import report as conformance_report
from provisioner.domain.errors import ProvisioningError
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
             'evidence_owner': 'platform-owner'}
            for subject, native_id in subjects]


def run(context: Context, observations=()) -> tuple[int, dict]:
    try:
        plan = plan_command.plan_for(context)
    except ProvisioningError as error:
        return EXIT_REFUSED, {'format': RESULT_FORMAT, 'status': 'REFUSED',
                              'source': context.source, 'errors': [error.to_dict()],
                              'native_contact': False}

    report = conformance_report.build(plan, observations)
    comparison = reconciliation_compare.build(plan.desired_state, observations)
    classification = reconciliation_classify.classify(comparison)
    drift = drift_module.to_dict(plan.desired_state, observations)
    health = health_module.to_dict(plan.desired_state, observations)

    return EXIT_OK, {
        'format': RESULT_FORMAT, 'status': report['status'],
        'source': context.source, 'plan_digest': plan.digest,
        'request_digest': plan.request.digest,
        'conformance': report,
        'verification_plan': verification_plan(plan),
        'observations': native_module.to_dict(observations, plan.desired_state),
        'drift': drift,
        'reconciliation': classification,
        'health': health,
        'activation': 'HELD',
        'native_contact': False,
        'limits': ['Verification is repository-side until native readback exists',
                   'Absent observation is never reported as in sync or healthy']}


def to_dict(context: Context) -> dict:
    return {'format': RESULT_FORMAT, 'native_contact': False}