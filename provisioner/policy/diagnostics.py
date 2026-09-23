"""Policy diagnostics.

One place decides how a policy violation becomes a structured diagnostic. Schema
failures, semantic refusals and standards violations all leave the pipeline in
the same shape so the CLI and the tests can render them uniformly.
"""
from __future__ import annotations

from provisioner.domain.errors import Diagnostics, ProvisioningError

POLICY_FORMAT = 'hosting-policy-diagnostics/1'

LAYER_BY_FAMILY = {
    'environment': 'policy',
    'zones': 'policy',
    'recovery': 'policy',
    'exposure': 'policy',
    'network': 'policy',
    'capacity': 'policy',
    'services': 'policy',
    'standards': 'policy',
    'semantics': 'domain',
}


def from_violation(violation: dict) -> dict:
    family = violation.get('family', 'standards')
    return {'code': 'POLICY_VIOLATION', 'layer': LAYER_BY_FAMILY.get(family, 'policy'),
            'message': f'{violation["rule"]}: {violation["description"]} ({violation["detail"]})',
            'path': violation.get('path'), 'details': {'rule': violation['rule'],
                                                      'severity': violation.get('severity', 'error'),
                                                      'family': family},
            'remediation': violation.get('remediation')}


def collect(document: dict, rules: list[dict], diagnostics: Diagnostics) -> list[dict]:
    """Evaluate standards rules and add every violation to `diagnostics`."""
    from provisioner.policy.standards import evaluate

    violations = evaluate(document, rules)
    for violation in violations:
        payload = from_violation(violation)
        error = ProvisioningError(payload['code'], payload['message'], path=payload['path'],
                                 details=payload['details'],
                                 remediation=payload['remediation'])
        if payload['details']['severity'] == 'warning':
            diagnostics.add_warning(error)
        else:
            diagnostics.add_error(error)
    return violations


def summary(diagnostics: Diagnostics, violations: list[dict], rules_evaluated: int,
            rules_digest: str = '') -> dict:
    """The policy outcome, plus the identity of the exact rule set that produced it.

    Binding the rule-set digest into the outcome means a reviewed change to a policy
    rule changes the identity of every plan evaluated against it, even when the
    outcome counts happen to be identical.
    """
    return {'format': POLICY_FORMAT,
            'errors': len(diagnostics.errors),
            'warnings': len(diagnostics.warnings),
            'rules_evaluated': rules_evaluated,
            'rules_failed': sorted({v['rule'] for v in violations}),
            'rules_digest': rules_digest}