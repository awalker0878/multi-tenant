"""Directed, exact-tuple route comparison without execution authority.

This catalogue evaluates reviewed claims for an operator comparison. Its inputs
must be obtained from independently verified installed inventory and campaign
evidence before a service displays them as native facts. Constructing these
values, including a ``RELEASED`` claim, does not authenticate that evidence,
authorize a job, or enable a native operation.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from provisioner.controlplane.authority.model import PlanScope

_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$')
_DIGEST = re.compile(r'^[0-9a-f]{64}$')
FAMILIES = frozenset({'vmware', 'nutanix', 'openstack'})
METHODS = frozenset({'REBUILD_RESTORE', 'COLD_VM_CONVERSION',
                     'SAME_PLATFORM_RELOCATION', 'APPLICATION_NATIVE',
                     'WARM_VM_TRANSFER'})
MATURITY = frozenset({'UNSUPPORTED', 'DESIGNED', 'IMPLEMENTED', 'LAB_VERIFIED',
                      'NATIVE_QUALIFIED', 'RELEASED'})
SIDES = frozenset({'SOURCE_EXIT', 'TARGET_OPERATE'})


def _identifier(value: str) -> bool:
    return isinstance(value, str) and _ID.fullmatch(value) is not None


def _digest(value: str) -> bool:
    return isinstance(value, str) and _DIGEST.fullmatch(value) is not None


def _utc(value: datetime) -> bool:
    return (isinstance(value, datetime) and value.tzinfo is not None
            and value.utcoffset() is not None
            and value.utcoffset().total_seconds() == 0)


def native_scope_key(scope: PlanScope) -> tuple[str, ...]:
    """Native identity stays the same when site or WSD labels differ."""
    return (scope.organization_id, scope.tenant_id, scope.endpoint_id,
            scope.native_scope_id, scope.platform_family)


@dataclass(frozen=True)
class InstalledTuple:
    """Exact observed installation and native scope, including versioned tuple digest."""

    scope: PlanScope
    product_tuple_id: str
    product_tuple_digest: str

    def __post_init__(self) -> None:
        if (not isinstance(self.scope, PlanScope)
                or self.scope.platform_family not in FAMILIES
                or not _identifier(self.product_tuple_id)
                or not _digest(self.product_tuple_digest)):
            raise ValueError('An exact installed product tuple and native scope are required')


@dataclass(frozen=True)
class RouteKey:
    """One direction and one method/profile; no family-level reverse implication."""

    source: InstalledTuple
    destination: InstalledTuple
    method: str
    guest_profile: str
    network_mode: str
    data_mode: str

    def __post_init__(self) -> None:
        if (not isinstance(self.source, InstalledTuple)
                or not isinstance(self.destination, InstalledTuple)
                or self.method not in METHODS
                or not all(_identifier(value) for value in (
                    self.guest_profile, self.network_mode, self.data_mode))):
            raise ValueError('An exact directed route and supported method are required')
        if native_scope_key(self.source.scope) == native_scope_key(self.destination.scope):
            raise ValueError('A route needs distinct source and destination native scopes')
        if (self.method == 'SAME_PLATFORM_RELOCATION'
                and self.source.scope.platform_family != self.destination.scope.platform_family):
            raise ValueError('Same-platform relocation requires matching platform families')


@dataclass(frozen=True)
class QualificationEvidence:
    """One independently reviewed source or target native campaign artifact.

    ``SOURCE_EXIT`` covers the method's actual source action (export, capture,
    or relocation); ``TARGET_OPERATE`` covers its destination action. Both
    artifacts must match the exact installed tuple and all route dimensions.
    The caller, not this data class, authenticates the artifact and its owner.
    """

    side: str
    installation: InstalledTuple
    method: str
    guest_profile: str
    network_mode: str
    data_mode: str
    evidence_id: str
    evidence_digest: str
    observed_at: datetime
    expires_at: datetime

    def __post_init__(self) -> None:
        if (self.side not in SIDES or not isinstance(self.installation, InstalledTuple)
                or self.method not in METHODS
                or not all(_identifier(value) for value in (
                    self.guest_profile, self.network_mode, self.data_mode,
                    self.evidence_id))
                or not _digest(self.evidence_digest)
                or not _utc(self.observed_at) or not _utc(self.expires_at)
                or self.expires_at <= self.observed_at):
            raise ValueError('Invalid exact, time-bounded native qualification evidence')


@dataclass(frozen=True)
class RouteClaim:
    key: RouteKey
    maturity: str
    evidence: tuple[QualificationEvidence, ...] = ()

    def __post_init__(self) -> None:
        if (not isinstance(self.key, RouteKey) or self.maturity not in MATURITY
                or not isinstance(self.evidence, tuple)
                or any(not isinstance(item, QualificationEvidence)
                       for item in self.evidence)
                or self.maturity == 'UNSUPPORTED' and self.evidence):
            raise ValueError('Invalid route claim')
        if len({item.side for item in self.evidence}) != len(self.evidence):
            raise ValueError('Only one current artifact per independent route side is allowed')


@dataclass(frozen=True)
class RouteAssessment:
    key: RouteKey
    status: str
    maturity: str
    blockers: tuple[str, ...]
    source_evidence_digest: str | None
    target_evidence_digest: str | None
    execution_authorized: bool = False

    def __post_init__(self) -> None:
        if self.execution_authorized is not False:
            raise ValueError('A route comparison cannot authorize execution')


class RouteCatalogue:
    """In-memory comparison of explicit directed claims; no mutating API."""

    def __init__(self, claims: Iterable[RouteClaim] = ()) -> None:
        entries: dict[RouteKey, RouteClaim] = {}
        for claim in claims:
            if not isinstance(claim, RouteClaim) or claim.key in entries:
                raise ValueError('Route claims must be unique exact directed keys')
            entries[claim.key] = claim
        self._claims = entries

    @staticmethod
    def _side_blockers(claim: RouteClaim, side: str, at: datetime) -> list[str]:
        expected = claim.key.source if side == 'SOURCE_EXIT' else claim.key.destination
        evidence = next((item for item in claim.evidence if item.side == side), None)
        if evidence is None:
            return [side + '_EVIDENCE_MISSING']
        if (evidence.installation != expected or evidence.method != claim.key.method
                or evidence.guest_profile != claim.key.guest_profile
                or evidence.network_mode != claim.key.network_mode
                or evidence.data_mode != claim.key.data_mode):
            return [side + '_EVIDENCE_SCOPE_MISMATCH']
        if evidence.observed_at > at:
            return [side + '_EVIDENCE_NOT_YET_VALID']
        if evidence.expires_at <= at:
            return [side + '_EVIDENCE_EXPIRED']
        return []

    def evaluate(self, key: RouteKey, *, as_of: datetime) -> RouteAssessment:
        if not isinstance(key, RouteKey) or not _utc(as_of):
            raise ValueError('An exact route and UTC assessment time are required')
        claim = self._claims.get(key)
        if claim is None:
            return RouteAssessment(key, 'UNKNOWN', 'UNKNOWN', ('ROUTE_NOT_CATALOGUED',),
                                   None, None)
        if claim.maturity == 'UNSUPPORTED':
            return RouteAssessment(key, 'BLOCKED', claim.maturity,
                                   ('ROUTE_EXPLICITLY_UNSUPPORTED',), None, None)
        proof = {item.side: item for item in claim.evidence}
        blockers = []
        if claim.maturity not in {'NATIVE_QUALIFIED', 'RELEASED'}:
            blockers.append('ROUTE_NOT_NATIVE_QUALIFIED')
        for side in ('SOURCE_EXIT', 'TARGET_OPERATE'):
            blockers.extend(self._side_blockers(claim, side, as_of))
        if ({'SOURCE_EXIT', 'TARGET_OPERATE'} <= proof.keys()
                and (proof['SOURCE_EXIT'].evidence_id == proof['TARGET_OPERATE'].evidence_id
                     or proof['SOURCE_EXIT'].evidence_digest == proof['TARGET_OPERATE'].evidence_digest)):
            blockers.append('SOURCE_TARGET_EVIDENCE_NOT_INDEPENDENT')
        return RouteAssessment(
            key, 'CONDITIONAL' if blockers else 'CANDIDATE', claim.maturity,
            tuple(blockers),
            proof['SOURCE_EXIT'].evidence_digest if 'SOURCE_EXIT' in proof else None,
            proof['TARGET_OPERATE'].evidence_digest if 'TARGET_OPERATE' in proof else None)

    def compare_destinations(self, source: InstalledTuple,
                             destinations: Iterable[InstalledTuple], *,
                             method: str, guest_profile: str, network_mode: str,
                             data_mode: str, as_of: datetime) -> tuple[RouteAssessment, ...]:
        """Preserve operator destination order and give every option a reason."""
        if not isinstance(source, InstalledTuple):
            raise ValueError('An exact observed source tuple is required')
        return tuple(self.evaluate(RouteKey(source, destination, method, guest_profile,
                                            network_mode, data_mode), as_of=as_of)
                     for destination in destinations)
