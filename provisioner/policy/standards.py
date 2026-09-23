"""Standards policy rules.

Rules are reviewed JSON under `policy/rules/*.json` and are evaluated by one
small, deterministic interpreter: every rule states a `when` selector and either
a `require` allow-list or a `forbid` deny-list over request paths.
"""
from __future__ import annotations

import json
from pathlib import Path

from provisioner.domain.errors import ProvisioningError
from provisioner.domain.request import digest

ROOT = Path(__file__).resolve().parents[2]
RULE_ROOT = ROOT / 'policy' / 'rules'

SEVERITIES = ('error', 'warning')


def _lookup(document, path: str):
    node = document
    for part in path.split('.'):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def load_rules(root: Path = RULE_ROOT) -> list[dict]:
    rules: list[dict] = []
    seen: set[str] = set()
    for path in sorted(root.glob('*.json')):
        try:
            document = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError) as exc:
            raise ProvisioningError('POLICY_VIOLATION', f'Unreadable policy rules: {exc}',
                                    path=str(path.relative_to(ROOT))) from exc
        rows = document.get('rules')
        if not isinstance(rows, list) or not rows:
            raise ProvisioningError('POLICY_VIOLATION', 'Empty policy rule file',
                                    path=str(path.relative_to(ROOT)))
        for row in rows:
            if not isinstance(row, dict) or not {'rule', 'description', 'when'} <= set(row):
                raise ProvisioningError('POLICY_VIOLATION', 'Incomplete policy rule',
                                        path=str(path.relative_to(ROOT)))
            if row['rule'] in seen:
                raise ProvisioningError('POLICY_VIOLATION', f'Duplicate policy rule: {row["rule"]}',
                                        path=str(path.relative_to(ROOT)))
            if set(row) - {'rule', 'family', 'description', 'severity', 'when', 'require', 'forbid', 'remediation'}:
                raise ProvisioningError('POLICY_VIOLATION', f'Unknown policy rule field: {row["rule"]}',
                                        path=str(path.relative_to(ROOT)))
            if not ({'require', 'forbid'} & set(row)):
                raise ProvisioningError('POLICY_VIOLATION',
                                        f'Policy rule states no requirement: {row["rule"]}',
                                        path=str(path.relative_to(ROOT)))
            if row.get('severity', 'error') not in SEVERITIES:
                raise ProvisioningError('POLICY_VIOLATION', f'Unknown rule severity: {row["rule"]}',
                                        path=str(path.relative_to(ROOT)))
            seen.add(row['rule'])
            rules.append(row)
    if not rules:
        raise ProvisioningError('POLICY_VIOLATION', 'No standards policy rules are present')
    return rules


def rules_digest(rules: list[dict] | None = None, root: Path = RULE_ROOT) -> str:
    """The canonical digest of the reviewed rule set.

    A plan cites the exact reviewed policy revision it was evaluated against, so a
    later rule edit is visible in every plan identity rather than silently reusing
    the earlier outcome.
    """
    return digest(rules if rules is not None else load_rules(root))


def evaluate(document: dict, rules: list[dict]) -> list[dict]:
    """Return violations in rule order. A rule that cannot resolve a path fails closed."""
    violations: list[dict] = []
    for rule in rules:
        selector = rule['when']
        if not all(_lookup(document, path) in values for path, values in selector.items()):
            continue
        for path, allowed in rule.get('require', {}).items():
            actual = _lookup(document, path)
            if actual not in allowed:
                violations.append(_violation(rule, path, f'{actual!r} is not one of {allowed}'))
        for path, denied in rule.get('forbid', {}).items():
            actual = _lookup(document, path)
            if actual in denied:
                violations.append(_violation(rule, path, f'{actual!r} is forbidden by standards'))
    return violations


def _violation(rule: dict, path: str, detail: str) -> dict:
    return {'rule': rule['rule'], 'family': rule.get('family', 'standards'),
            'severity': rule.get('severity', 'error'),
            'path': f'$.{path}', 'detail': detail,
            'remediation': rule.get('remediation', 'Change the request or obtain a reviewed exception.'),
            'description': rule['description']}