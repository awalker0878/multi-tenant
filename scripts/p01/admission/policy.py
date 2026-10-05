"""Trusted-base admission predicates. Candidate data never supplies its own trust."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import PurePosixPath
import re


class Denied(ValueError):
    pass


def need(value, code):
    if not value:
        raise Denied(code)


def safe_path(value: str):
    path = PurePosixPath(value)
    need(bool(value) and not path.is_absolute() and str(path) == value and '..' not in path.parts
         and '\\' not in value, 'unsafe_changed_path')


def affected(paths, base_components, head_components, base_graph, head_graph):
    """Union both owner inventories and dependency edges before transitive expansion."""
    ids = set(base_components) | set(head_components)
    selected = set(); unknown = []; removed = sorted(set(base_components) - set(head_components))
    for path in paths:
        safe_path(path)
        if path.startswith(('scripts/', '.github/', 'deploy/', 'release/', 'architecture/')):
            selected.update(ids)
        elif path.startswith('contracts/'):
            found = set(base_graph.get('contracts', {}).get(path, [])) | set(head_graph.get('contracts', {}).get(path, []))
            if not found:
                unknown.append(path)
            selected.update(found or ids)
        elif path.startswith(('apps/', 'services/', 'workers/', 'packages/')):
            owners = {name for graph in (base_components, head_components) for name, item in graph.items()
                      if path == item['path'] or path.startswith(item['path'] + '/')}
            if not owners:
                unknown.append(path)
            selected.update(owners or ids)
        elif not (path.startswith(('docs/', 'verification/', 'spikes/', 'tests/')) or
                  path in {'next_work.md', 'README.md', 'CONTRIBUTING.md', '.gitignore', 'requirements-docs.txt'}):
            unknown.append(path); selected.update(ids)
        if path.startswith('tests/contracts/'):
            selected.update(ids)
    edges = {}
    for graph in (base_graph, head_graph):
        for consumer, producers in graph.get('dependencies', {}).items():
            need(consumer in ids and set(producers) <= ids, 'unregistered_consumer')
            edges.setdefault(consumer, set()).update(producers)
    for _ in range(len(ids) + 1):
        expanded = selected | {consumer for consumer, deps in edges.items() if deps & selected}
        if expanded == selected:
            break
        selected = expanded
    return {'components': sorted(selected), 'unknown_paths': sorted(unknown), 'removed_components': removed}


def required_roles(paths, impacted):
    roles = {name.removesuffix('-workers') for name in impacted}
    if not roles:
        roles.add('platform')
    if any(PurePosixPath(p).name in {'phpstan.neon', 'deptrac.yaml', 'pint.json', 'pyproject.toml',
                                    'tsconfig.json', 'eslint.config.js', '.dockerignore', '.gitignore'} for p in paths):
        roles |= {'platform', 'security'}
    if any(p.startswith(('.github/', 'scripts/', 'release/', 'architecture/')) for p in paths):
        roles |= {'platform', 'security'}
    if any(p.startswith('contracts/') for p in paths):
        roles.add('architecture')
    if any(any(x in p.lower() for x in ('auth', 'tenant', 'policy', 'evidence', 'credential', 'secret', 'signing')) for p in paths):
        roles.add('security')
    if any(any(x in p.lower() for x in ('migration', 'recover', 'workflow', 'deploy/')) for p in paths):
        roles.add('sre')
    return roles


def check_exceptions(items, accounts, now):
    seen = set()
    for item in items:
        need(item['id'] not in seen, 'duplicate_exception'); seen.add(item['id'])
        need(item['kind'] in {'architecture', 'type-analysis'}, 'forbidden_exception_scope')
        need(item['owner'] and item['reason'] and item['removal_task'] and item['compensating_check'], 'incomplete_exception')
        need(re.fullmatch(r'[0-9a-f]{40}', item['source_revision']), 'exception_source_missing')
        need(item['paths'] and item['rule_id'], 'exception_scope_missing')
        for path in item['paths']:
            safe_path(path); need(not any(x in path for x in '*?[]'), 'wildcard_exception')
        approver = str(item['approved_by'])
        need(approver in accounts and accounts[approver]['type'] == 'User', 'unknown_exception_approver')
        expires = datetime.fromisoformat(item['expires_at']); approved = datetime.fromisoformat(item['approved_at'])
        need(expires.tzinfo is not None and approved.tzinfo is not None, 'exception_time_not_utc')
        need(approved.utcoffset().total_seconds() == expires.utcoffset().total_seconds() == 0, 'exception_time_not_utc')
        need(approved <= now < expires and (expires - approved).total_seconds() <= 30 * 86400, 'exception_expired_or_unbounded')


def review(policy, snapshot, paths, impact, now=None):
    now = now or datetime.now(timezone.utc)
    need(policy['status'] == 'ACTIVE', 'review_roles_unconfigured')
    need(snapshot['repository'] == policy['repository'], 'wrong_repository')
    need(snapshot['state'] == 'open' and not snapshot['draft'], 'pull_request_not_reviewable')
    head, base, tested = (snapshot[k] for k in ('head_sha', 'base_sha', 'tested_sha'))
    need(all(re.fullmatch(r'[0-9a-f]{40}', x) for x in (head, base, tested)), 'invalid_revision')
    need(snapshot['tested_parents'] == [base, head], 'stale_or_unrelated_test_merge')
    need(snapshot['head_after'] == head and snapshot['base_after'] == base, 'revision_changed_during_review')
    need(not impact['unknown_paths'] and not impact['removed_components'], 'unclassified_or_removed_component')
    need(snapshot['unresolved_threads'] == 0, 'unresolved_review_threads')
    check_exceptions(snapshot['exceptions'], policy['accounts'], now)
    check_exceptions(snapshot.get('candidate_exceptions', []), policy['accounts'], now)
    for exception in snapshot['exceptions']:
        need(exception['source_revision'] == head, 'exception_wrong_source')
        need(snapshot['permissions'].get(str(exception['approved_by'])) in {'admin', 'maintain', 'write'}, 'exception_reviewer_not_authorized')
    for check in policy['required_checks']:
        observed = [r for r in snapshot['checks'] if r['name'] == check and r['app_id'] == policy['allowed_check_app_id']
                    and r['head_sha'] == head and r.get('tested_sha') == tested]
        need(observed, 'missing_required_check:' + check)
        latest = max(observed, key=lambda item: item['id'])
        need(latest['status'] == 'completed' and latest['conclusion'] == 'success', 'required_check_not_success:' + check)
    for exception in snapshot['exceptions']:
        need(exception['compensating_check'] in policy['required_checks'], 'exception_compensating_check_not_required')
    latest = {}
    for r in sorted(snapshot['reviews'], key=lambda item: item['id']):
        # Comments do not dismiss an approval or a blocking change request.
        if r['state'] in {'APPROVED', 'CHANGES_REQUESTED', 'DISMISSED'}:
            latest[str(r['user_id'])] = r
    need(not any(r['state'] == 'CHANGES_REQUESTED' for r in latest.values()), 'changes_requested')
    approved = set()
    for account_id, r in latest.items():
        account = policy['accounts'].get(account_id)
        if account and account_id != str(snapshot['author_id']) and r['state'] == 'APPROVED' and r['commit_id'] == head:
            need(account['type'] == 'User' and snapshot['permissions'].get(account_id) in {'admin', 'maintain', 'write'}, 'reviewer_not_authorized')
            need(r['login'] == account['login'], 'reviewer_identity_changed')
            approved.add(account_id)
    roles = required_roles(paths, impact['components'])
    for exception in snapshot.get('candidate_exceptions', []):
        need(str(exception['approved_by']) in approved
             and str(exception['approved_by']) in set(map(str, policy['roles'].get('security', []))),
             'proposed_exception_requires_actual_security_approval')
    need(roles, 'review_scope_missing')
    for role in roles:
        need(set(map(str, policy['roles'].get(role, []))) & approved, 'missing_role_review:' + role)
    critical = bool(roles & {'security', 'architecture', 'sre', 'platform'})
    if critical:
        qualified = {person for role in roles for person in map(str, policy['roles'].get(role, [])) if person in approved}
        need(len(qualified) >= 2, 'distinct_reviewers_required')
        # If security is required, it must be a different person from at least one owning/platform reviewer.
        if 'security' in roles:
            security = set(map(str, policy['roles']['security'])) & approved
            other = {p for role in roles - {'security'} for p in map(str, policy['roles'].get(role, [])) if p in approved}
            need(any(a != b for a in security for b in other), 'independent_security_required')
    return {'result': 'ADMITTED', 'reviewed_head': head, 'tested_merge': tested,
            'roles': sorted(roles), 'reviewers': sorted(approved), 'components': impact['components']}
