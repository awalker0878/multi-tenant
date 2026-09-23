"""Conformance reporting.

The report is the artifact a reviewer reads before activation. It states the
outcome, the blocking checks and — explicitly — what it does not prove.

The distinction the report exists to make is between a proposal and an answer. A
repository-side check reports what this repository can prove from its own artifacts,
which is planning intent; the owner's own answer is a separate row, and only that row
can settle a proposal. A repository row that used the owner's vocabulary without the
owner's evidence would read as a confirmation nobody gave, so the report refuses to
be built at all rather than emit it.
"""
from __future__ import annotations

import re

from provisioner.conformance import checks as check_set
from provisioner.domain.errors import ProvisioningError

REPORT_FORMAT = 'hosting-conformance-report/1'
PROPOSAL_FORMAT = 'hosting-conformance-proposal/1'

READY = 'CONFORMANT'
BLOCKED = 'BLOCKED_ON_EXTERNAL_EVIDENCE'
FAILED = 'FAILED'
STATUSES = (READY, BLOCKED, FAILED)

#: Which owner's answer settles each repository-side proposal.
PROPOSAL_SOURCES = dict(check_set.CONFIRMATION_OF)

#: What a repository-side proposal is, stated as the authority it carries.
PROPOSAL_AUTHORITY = 'REPOSITORY_PROPOSAL_NOT_OWNER_STATE'

_OWNERSHIP = re.compile(r'\b(' + '|'.join(check_set.OWNERSHIP_VOCABULARY) + r')\b',
                        re.IGNORECASE)


def _strings(value):
    """Every string a check is described by.

    Evidence keys are the reviewed contract's own identifiers \u2014 the native field an
    adapter declares it observes, the authority a catalog names \u2014 so only the prose
    and the values are read as claims. A key is a name, not a sentence.
    """
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            yield from _strings(item)


def _ownership_words(check) -> list[str]:
    """The ownership vocabulary a repository-side check uses, if any.

    Every repository-side row is read for the prose it states. A proposal is read for
    the values it carries as well, because a proposal's evidence is where an owner's
    outcome would be asserted. A non-proposal row's evidence is a reviewed artifact's
    own vocabulary \u2014 the message an adapter attaches to a field mapping, the native
    field name a module declares \u2014 so it is read as a name, not as a claim.
    """
    texts = list(_strings(check.detail))
    if check.name in PROPOSAL_SOURCES:
        texts += list(_strings(check.evidence))
    found: set[str] = set()
    for text in texts:
        found |= {match.group(0).lower() for match in _OWNERSHIP.finditer(text)}
    return sorted(found)


def ownership_claims(results) -> list[dict]:
    """Every repository-side row that claims an outcome only an owner can give.

    The words that assert an authoritative outcome belong to the owner's own row. A
    proposal is allowed to use one only when the owner check that settles it has
    already passed; otherwise the claim is unproven and is reported as such.
    """
    satisfied = {check.name for check in results if check.satisfied}
    claims = []
    for check in results:
        if check.authority != 'REPOSITORY':
            continue
        words = _ownership_words(check)
        if not words:
            continue
        confirming = PROPOSAL_SOURCES.get(check.name)
        if confirming in satisfied:
            continue
        claims.append({'check': check.name, 'words': words,
                       'confirmation_check': confirming})
    return claims


def proposal_block(results) -> dict:
    """What the repository proposes and which owner answer is still outstanding."""
    satisfied = {check.name for check in results if check.satisfied}
    return {'format': PROPOSAL_FORMAT,
            'authority': PROPOSAL_AUTHORITY,
            'checks': sorted(PROPOSAL_SOURCES),
            'confirmed_by': dict(PROPOSAL_SOURCES),
            'unconfirmed': sorted(name for name, owner_check in PROPOSAL_SOURCES.items()
                                  if owner_check not in satisfied),
            'limits': ['A repository-side check reports a proposal, never owner state',
                       'Only the owner check named in confirmed_by settles a proposal',
                       'An unconfirmed proposal is blocking and is never reported as an answer']}


def build(plan, observations=(), authorization=None, subject: str | None = None,
          capacity=None, addresses=None) -> dict:
    """Summarise every check into one conformance report.

    `capacity` and `addresses` are the reconciled owner evidence the transport read,
    if any. They change only how the owners' own state is reported, never whether the
    repository produced that evidence.
    """
    results = check_set.run(plan, observations, authorization, capacity, addresses)
    claims = ownership_claims(results)
    if claims:
        raise ProvisioningError(
            'CONFORMANCE_CLAIM_UNPROVEN',
            'A repository-side conformance check claims an owner outcome without the '
            'owner evidence that settles it',
            path='$.conformance.checks',
            details={'claims': claims,
                     'ownership_vocabulary': list(check_set.OWNERSHIP_VOCABULARY)})
    failed = sorted(c.name for c in results if c.status == check_set.FAIL)
    pending = sorted(c.name for c in results if c.status == check_set.PENDING)
    blocking = sorted(c.name for c in results if c.mandatory and not c.satisfied)

    if failed:
        status = FAILED
    elif pending:
        status = BLOCKED
    else:
        status = READY

    return {'format': REPORT_FORMAT, 'status': status,
            'subject': subject or f'{plan.request.tenant}/{plan.request.wsd}',
            'generation': plan.generation,
            'identity': plan.identity.key,
            'operation_id': plan.operation_id,
            'plan_digest': plan.digest,
            'request_digest': plan.request.digest,
            'checks': [c.to_dict() for c in results],
            'proposal': proposal_block(results),
            'failed': failed, 'pending': pending, 'blocking': blocking,
            'ready': status == READY,
            'native_contact': False,
            'limits': ['This report is repository-side conformance evidence',
                       'A repository-side check reports a proposal, never owner state',
                       'A blocking check prevents activation, never planning',
                       'Unknown required evidence is never reported as PASS',
                       'Evidence produced for another generation never satisfies this report',
                       'Evidence that names another plan digest, identity or generation settles no check']}


def to_dict(plan, observations=(), authorization=None, capacity=None,
            addresses=None) -> dict:
    return build(plan, observations, authorization, capacity=capacity, addresses=addresses)
