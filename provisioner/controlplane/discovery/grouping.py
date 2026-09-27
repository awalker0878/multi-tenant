"""Reviewed, assessment-only application grouping over one exact native scope.

The caller independently authenticates the application owner and verifies the
review reference. A value constructed here is neither an approved canonical
ApplicationGroup nor permission to adopt, migrate or alter a Workload. Optional
CMDB, guest and monitoring assertions retain provenance and unresolved edges.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta

from provisioner.controlplane.authority.model import PlanScope

from .model import DiscoveryResult, NativeIdentity

_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z')
_DIGEST = re.compile(r'[0-9a-f]{64}\Z')
_SOURCES = frozenset({'CMDB', 'GUEST', 'MONITORING', 'APPLICATION_OWNER'})
_RELATIONS = frozenset({'STARTS_AFTER', 'SERVICE_CALL'})
_UNKNOWN_REASONS = frozenset({'UNRESOLVED_TARGET', 'NOT_OBSERVED',
                              'CONFLICTING_SOURCES', 'EXTERNAL_DEPENDENCY'})


class GroupingHeld(ValueError):
    """The reviewed source, membership, ordering or provenance is unsound."""


def _id(value: object) -> bool:
    return isinstance(value, str) and _ID.fullmatch(value) is not None


def _utc(value: object) -> bool:
    return (isinstance(value, datetime) and value.tzinfo is not None
            and value.utcoffset() == timedelta(0))


def _hash(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(',', ':'),
                         ensure_ascii=True, allow_nan=False).encode('utf-8')
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class GroupMember:
    workload_id: str  # proposed logical ID; no Workload record is written
    native_vm: NativeIdentity


@dataclass(frozen=True, slots=True)
class ConsistencyProposal:
    group_id: str
    dataset_ids: tuple[str, ...]  # owner-asserted, not verified data consistency


@dataclass(frozen=True, slots=True)
class GroupDraft:
    application_group_id: str
    name: str
    owner_id: str
    members: tuple[GroupMember, ...]
    dataset_ids: tuple[str, ...]
    consistency_groups: tuple[ConsistencyProposal, ...]
    startup_order: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DependencyAssertion:
    assertion_id: str
    source_workload_id: str
    target_workload_id: str | None
    relation: str
    state: str  # KNOWN or UNKNOWN
    source: str  # CMDB, GUEST, MONITORING, APPLICATION_OWNER
    source_reference: str
    observed_at: datetime
    unknown_reason: str | None = None


@dataclass(frozen=True, slots=True)
class OwnerReview:
    owner_id: str
    scope: PlanScope  # trusted API binds the verified owner's exact review scope
    review_reference: str
    reviewed_at: datetime
    proposal_digest: str


@dataclass(frozen=True, slots=True)
class GroupCandidate:
    draft: GroupDraft
    scope: PlanScope
    discovery_digest: str
    dependencies: tuple[DependencyAssertion, ...]
    review: OwnerReview
    digest: str
    unknown_edges: tuple[DependencyAssertion, ...]
    status: str  # REVIEWED_ASSESSMENT_ONLY or REVIEWED_WITH_UNKNOWNS
    ownership_accepted: bool = False
    execution_approved: bool = False


def proposal_digest(result: DiscoveryResult, draft: GroupDraft,
                    dependencies: tuple[DependencyAssertion, ...]) -> str:
    """Exact review input; it is a checksum, not a signature or owner identity."""
    if not isinstance(result, DiscoveryResult) or not isinstance(draft, GroupDraft):
        raise GroupingHeld('Discovery result and draft are required')
    if not isinstance(dependencies, tuple):
        raise GroupingHeld('Dependency assertions must be immutable')
    return _hash({
        'format': 'hosting-application-group-candidate/1',
        'discoveryDigest': result.digest,
        'scope': vars(result.scope),
        'draft': {
            'applicationGroupId': draft.application_group_id,
            'name': draft.name, 'ownerId': draft.owner_id,
            'members': [{'workloadId': member.workload_id,
                         'nativeVm': member.native_vm.key()}
                        for member in draft.members],
            'datasetIds': draft.dataset_ids,
            'consistencyGroups': [
                {'groupId': group.group_id, 'datasetIds': group.dataset_ids}
                for group in draft.consistency_groups],
            'startupOrder': draft.startup_order,
        },
        'dependencies': [
            {'assertionId': edge.assertion_id,
             'sourceWorkloadId': edge.source_workload_id,
             'targetWorkloadId': edge.target_workload_id,
             'relation': edge.relation, 'state': edge.state,
             'source': edge.source, 'sourceReference': edge.source_reference,
             'observedAt': edge.observed_at.isoformat(),
             'unknownReason': edge.unknown_reason}
            for edge in dependencies],
    })


def reviewed_candidate(result: DiscoveryResult, draft: GroupDraft,
                       dependencies: tuple[DependencyAssertion, ...],
                       review: OwnerReview, *, checked_at: datetime,
                       max_age: timedelta = timedelta(hours=1)) -> GroupCandidate:
    """Bind one reviewed candidate to current, complete VM observations.

    The trusted API must verify the owner subject and review reference outside
    this pure function. Unknown dependencies remain explicit and block a claim
    of a resolved graph; source assertions never become native observations.
    """
    if (not isinstance(result, DiscoveryResult) or result.completeness != 'COMPLETE'
            or not isinstance(draft, GroupDraft) or not isinstance(review, OwnerReview)
            or not isinstance(dependencies, tuple)
            or not _utc(checked_at) or not isinstance(max_age, timedelta)
            or not timedelta(0) < max_age <= timedelta(days=1)
            or not result.captured_at <= checked_at
            or checked_at - result.captured_at > max_age
            or not _utc(review.reviewed_at)
            or not result.captured_at <= review.reviewed_at <= checked_at
            or not _id(draft.application_group_id) or not _id(draft.owner_id)
            or not isinstance(draft.name, str) or not 1 <= len(draft.name) <= 256
            or draft.name != draft.name.strip()
            or any(ord(char) < 32 or ord(char) == 127 for char in draft.name)
            or review.owner_id != draft.owner_id or review.scope != result.scope
            or not _id(review.review_reference)
            or not isinstance(review.proposal_digest, str)
            or not _DIGEST.fullmatch(review.proposal_digest)):
        raise GroupingHeld('Current complete observations and exact owner review required')

    if (not isinstance(draft.members, tuple) or not 2 <= len(draft.members) <= 100
            or any(not isinstance(member, GroupMember)
                   or not _id(member.workload_id)
                   or not isinstance(member.native_vm, NativeIdentity)
                   or member.native_vm.resource_kind != 'vm'
                   or (member.native_vm.endpoint_id,
                       member.native_vm.native_scope_id,
                       member.native_vm.platform_family) !=
                      (result.scope.endpoint_id, result.scope.native_scope_id,
                       result.scope.platform_family)
                   for member in draft.members)):
        raise GroupingHeld('At least two exact-scope VM members are required')
    workload_ids = [member.workload_id for member in draft.members]
    native_ids = [member.native_vm.key() for member in draft.members]
    observed_ids = {obj.identity.key() for obj in result.objects
                    if obj.identity.resource_kind == 'vm'}
    if (len(set(workload_ids)) != len(workload_ids)
            or len(set(native_ids)) != len(native_ids)
            or not set(native_ids) <= observed_ids):
        raise GroupingHeld('Members must be distinct observed VMs')

    if (not isinstance(draft.startup_order, tuple)
            or len(draft.startup_order) != len(workload_ids)
            or set(draft.startup_order) != set(workload_ids)
            or not isinstance(draft.dataset_ids, tuple)
            or not draft.dataset_ids
            or len(set(draft.dataset_ids)) != len(draft.dataset_ids)
            or any(not _id(dataset) for dataset in draft.dataset_ids)
            or not isinstance(draft.consistency_groups, tuple)
            or not draft.consistency_groups
            or any(not isinstance(group, ConsistencyProposal)
                   or not _id(group.group_id)
                   or not isinstance(group.dataset_ids, tuple)
                   or not group.dataset_ids
                   or any(not _id(dataset) for dataset in group.dataset_ids)
                   for group in draft.consistency_groups)):
        raise GroupingHeld('Reviewed startup and dataset grouping are required')
    grouped = [dataset for group in draft.consistency_groups
               for dataset in group.dataset_ids]
    if (len({group.group_id for group in draft.consistency_groups}) !=
            len(draft.consistency_groups)
            or len(grouped) != len(set(grouped))
            or set(grouped) != set(draft.dataset_ids)):
        raise GroupingHeld('Every proposed dataset needs one consistency group')

    order = {workload: index for index, workload in enumerate(draft.startup_order)}
    seen_assertions = set()
    unknown = []
    if len(dependencies) > 500:
        raise GroupingHeld('Dependency assertion budget exceeded')
    for edge in dependencies:
        if (not isinstance(edge, DependencyAssertion)
                or not _id(edge.assertion_id)
                or edge.assertion_id in seen_assertions
                or edge.source_workload_id not in order
                or edge.relation not in _RELATIONS
                or edge.source not in _SOURCES
                or not _id(edge.source_reference)
                or not _utc(edge.observed_at)
                or not result.captured_at - max_age <= edge.observed_at <= checked_at):
            raise GroupingHeld('Dependency assertion has invalid provenance or scope')
        seen_assertions.add(edge.assertion_id)
        if edge.state == 'KNOWN':
            if (edge.target_workload_id not in order
                    or edge.target_workload_id == edge.source_workload_id
                    or edge.unknown_reason is not None):
                raise GroupingHeld('Known dependency needs another member')
            if (edge.relation == 'STARTS_AFTER'
                    and order[edge.target_workload_id] >=
                    order[edge.source_workload_id]):
                raise GroupingHeld('Startup order contradicts a known dependency')
        elif edge.state == 'UNKNOWN':
            if (edge.target_workload_id is not None
                    or edge.unknown_reason not in _UNKNOWN_REASONS):
                raise GroupingHeld('Unresolved dependency must not name an unscoped target')
            unknown.append(edge)
        else:
            raise GroupingHeld('Dependency needs a known or unknown state')

    expected = proposal_digest(result, draft, dependencies)
    if review.proposal_digest != expected:
        raise GroupingHeld('Owner review does not bind this observation and proposal')
    digest = _hash({'proposalDigest': expected,
                    'ownerId': review.owner_id,
                    'reviewScope': vars(review.scope),
                    'reviewReference': review.review_reference,
                    'reviewedAt': review.reviewed_at.isoformat()})
    return GroupCandidate(draft, result.scope, result.digest, dependencies, review,
                          digest, tuple(unknown),
                          'REVIEWED_WITH_UNKNOWNS' if unknown else
                          'REVIEWED_ASSESSMENT_ONLY')
