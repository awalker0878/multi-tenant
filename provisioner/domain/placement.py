"""Placement decision models.

A placement decision records every candidate that was evaluated, why each was
rejected and which authority produced the decision. A fixture-derived decision
is never presented as an authorization to build, and a decision can only be
`authorized` when both the inventory and the qualification it rests on are
authoritative.
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
HOLD_PLATFORM_NOT_QUALIFIED = 'HOLD_PLATFORM_NOT_QUALIFIED'
HOLD_CAPABILITY_NOT_QUALIFIED = 'HOLD_CAPABILITY_NOT_QUALIFIED'
HOLD_CAPACITY_INSUFFICIENT = 'HOLD_CAPACITY_INSUFFICIENT'
HOLD_SERVICE_UNAVAILABLE = 'HOLD_SERVICE_UNAVAILABLE'
HOLD_PREFIX_POOL_EXHAUSTED = 'HOLD_PREFIX_POOL_EXHAUSTED'
HOLD_NO_COHERENT_ENVELOPE = 'HOLD_NO_COHERENT_ENVELOPE'

# Every status this model can emit. `HOLD_NO_ELIGIBLE_SITE` is the only status
# produced when no candidate was evaluated at all; the remaining holds are
# ordered most-specific first so one inventory always yields one status, with
# `HOLD_NO_ELIGIBLE_PLATFORM` as the least specific catch-all.
HOLD_PRIORITY = (HOLD_CAPACITY_INSUFFICIENT, HOLD_SERVICE_UNAVAILABLE,
                 HOLD_PREFIX_POOL_EXHAUSTED, HOLD_CAPABILITY_NOT_QUALIFIED,
                 HOLD_PLATFORM_NOT_QUALIFIED, HOLD_NO_COHERENT_ENVELOPE,
                 HOLD_NO_ELIGIBLE_PLATFORM)

STATUSES = (PLACED, HOLD_NO_ELIGIBLE_SITE) + HOLD_PRIORITY

# The qualification identity recorded when a decision was assembled without a
# qualification source. It is explicit, self-describing and never authoritative,
# so an unrecorded qualification can never authorize a build.
UNRECORDED_QUALIFICATION = {'source': 'UNRECORDED', 'status': 'NOT_EVALUATED',
                            'authoritative': False, 'product_tuples': {}}

# The explicit product-tuple marker for a decision that selected no platform.
UNSELECTED_PRODUCT = 'UNSELECTED'


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
    blocker_classes: tuple[str, ...] = ()
    qualification_blockers: tuple[str, ...] = ()
    cell_blockers: tuple[str, ...] = ()
    product_tuple: str = UNSELECTED_PRODUCT

    def to_dict(self) -> dict:
        return {'site_key': self.site_key, 'cell_key': self.cell_key,
                'platform': self.platform, 'platform_family': self.platform_family,
                'zone': self.zone, 'eligible': self.eligible, 'score': self.score,
                'blockers': list(self.blockers),
                'blocker_classes': list(self.blocker_classes),
                'qualification_blockers': list(self.qualification_blockers),
                'cell_blockers': list(self.cell_blockers),
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
    qualification: dict = field(default_factory=dict)
    qualification_blockers: tuple[str, ...] = ()
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
    def qualification_identity(self) -> dict:
        """The recorded qualification, or the explicit unrecorded identity."""
        return dict(self.qualification) if self.qualification else dict(UNRECORDED_QUALIFICATION)

    @property
    def authorized(self) -> bool:
        """Only a placed decision over authoritative inventory and authoritative
        qualification can authorize anything. Declared qualification never can."""
        return (self.status == PLACED and self.authority == AUTHORITATIVE
                and bool(self.qualification_identity['authoritative']))

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
    def product_tuple(self) -> str:
        """The qualified product tuple of the selected platform.

        A product tuple is a function of the platform, so every evaluated candidate
        for the selected platform agrees; the first one found is the answer. A held
        decision has no selected platform and therefore no product tuple.
        """
        platform = self.platform
        if not platform:
            return UNSELECTED_PRODUCT
        for candidate in self.candidates:
            if candidate.platform == platform:
                return candidate.product_tuple
        return UNSELECTED_PRODUCT

    @property
    def clusters(self) -> dict:
        return dict((self.selected or {}).get('clusters', {}))

    @property
    def cells(self) -> dict:
        """The cell chosen for every required zone."""
        return dict((self.selected or {}).get('cells', {}))

    @property
    def envelope(self) -> dict:
        """The coherent site/platform boundary the selected zones were realized in."""
        return dict((self.selected or {}).get('envelope', {}))

    def to_dict(self) -> dict:
        limits = ['A placement decision is not an authorization to build']
        if self.authority == FIXTURE:
            limits.append('Fixture placement cannot be promoted to production')
        if not self.qualification_identity['authoritative']:
            limits.append('Native qualification is absent; this decision rests on a '
                          'declared qualification assumption')
        return {'format': self.format, 'status': self.status, 'authority': self.authority,
                'request_digest': self.request_digest,
                'selection_rule': self.selection_rule,
                'required_capabilities': list(self.required_capabilities),
                'qualification': self.qualification_identity,
                'qualification_blockers': list(self.qualification_blockers),
                'selected': self.selected,
                'candidates': [c.to_dict() for c in self.candidates],
                'reasons': list(self.reasons), 'digest': self.digest, 'limits': limits}


def finalize(decision: PlacementDecision) -> PlacementDecision:
    """Attach the self-describing digest so the decision can be cited later."""
    body = decision.to_dict()
    body.pop('digest')
    return PlacementDecision(**{**decision.__dict__, 'digest': digest(body)})