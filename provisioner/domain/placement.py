"""Placement decision models.

A placement decision records every candidate that was evaluated, why each was
rejected and which authority produced the decision. A fixture-derived decision
is never presented as an authorization to build.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from provisioner.domain.request import digest

PLACEMENT_FORMAT = 'hosting-placement-decision/1'

AUTHORITATIVE = 'AUTHORITATIVE_SITE_STATE'
FIXTURE = 'FIXTURE_NOT_PLACEMENT_AUTHORITY'
AUTHORITIES = (AUTHORITATIVE, FIXTURE)

PLACED = 'PLACED'
HOLD_NO_ELIGIBLE_SITE = 'HOLD_NO_ELIGIBLE_SITE'
HOLD_NO_ELIGIBLE_PLATFORM = 'HOLD_NO_ELIGIBLE_PLATFORM'
HOLD_CAPABILITY_NOT_QUALIFIED = 'HOLD_CAPABILITY_NOT_QUALIFIED'
HOLD_CAPACITY_INSUFFICIENT = 'HOLD_CAPACITY_INSUFFICIENT'
HOLD_SERVICE_UNAVAILABLE = 'HOLD_SERVICE_UNAVAILABLE'
HOLD_PREFIX_POOL_EXHAUSTED = 'HOLD_PREFIX_POOL_EXHAUSTED'

# Every status this model can emit. `HOLD_NO_ELIGIBLE_SITE` is the only status
# produced when no candidate was evaluated at all; the remaining holds are
# ordered most-specific first so one inventory always yields one status.
HOLD_PRIORITY = (HOLD_CAPACITY_INSUFFICIENT, HOLD_SERVICE_UNAVAILABLE,
                 HOLD_PREFIX_POOL_EXHAUSTED, HOLD_CAPABILITY_NOT_QUALIFIED,
                 HOLD_NO_ELIGIBLE_PLATFORM)

STATUSES = (PLACED, HOLD_NO_ELIGIBLE_SITE) + HOLD_PRIORITY


@dataclass(frozen=True)
class CandidateEvaluation:
    """One evaluated site/cell/platform option."""

    site_key: str
    cell_key: str
    platform: str
    platform_family: str
    zone: str
    eligible: bool
    score: int
    blockers: tuple[str, ...] = ()
    capability_blockers: tuple[str, ...] = ()
    product_tuple: str = 'UNSELECTED'

    def to_dict(self) -> dict:
        return {'site_key': self.site_key, 'cell_key': self.cell_key,
                'platform': self.platform, 'platform_family': self.platform_family,
                'zone': self.zone, 'eligible': self.eligible, 'score': self.score,
                'blockers': list(self.blockers),
                'capability_blockers': list(self.capability_blockers),
                'product_tuple': self.product_tuple}


@dataclass(frozen=True)
class PlacementDecision:
    """Deterministic placement result, or an explicit hold."""

    status: str
    authority: str
    request_digest: str
    selection_rule: str = ''
    selected: dict | None = None
    candidates: tuple[CandidateEvaluation, ...] = ()
    reasons: tuple[str, ...] = ()
    registry_blockers: tuple[str, ...] = ()
    required_capabilities: tuple[str, ...] = ()
    digest: str = ''
    format: str = PLACEMENT_FORMAT

    def __post_init__(self):
        if self.status not in STATUSES:
            raise ValueError(f'Unknown placement status: {self.status}')
        if self.authority not in AUTHORITIES:
            raise ValueError(f'Unknown placement authority: {self.authority}')

    @property
    def held(self) -> bool:
        return self.status != PLACED

    @property
    def authorized(self) -> bool:
        return self.status == PLACED and self.authority == AUTHORITATIVE

    @property
    def site_key(self) -> str | None:
        return (self.selected or {}).get('site_key')

    @property
    def cell_key(self) -> str | None:
        return (self.selected or {}).get('cell_key')

    @property
    def platform(self) -> str | None:
        return (self.selected or {}).get('platform')

    @property
    def clusters(self) -> dict:
        return dict((self.selected or {}).get('clusters', {}))

    def to_dict(self) -> dict:
        limits = ['A placement decision is not an authorization to build']
        if self.authority == FIXTURE:
            limits.append('Fixture placement cannot be promoted to production')
        return {'format': self.format, 'status': self.status, 'authority': self.authority,
                'request_digest': self.request_digest,
                'selection_rule': self.selection_rule,
                'required_capabilities': list(self.required_capabilities),
                'registry_blockers': list(self.registry_blockers),
                'selected': self.selected,
                'candidates': [c.to_dict() for c in self.candidates],
                'reasons': list(self.reasons), 'digest': self.digest, 'limits': limits}


def finalize(decision: PlacementDecision) -> PlacementDecision:
    """Attach the self-describing digest so the decision can be cited later."""
    body = decision.to_dict()
    body.pop('digest')
    return PlacementDecision(**{**decision.__dict__, 'digest': digest(body)})