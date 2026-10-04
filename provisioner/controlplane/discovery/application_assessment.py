"""Application-wide advice from retained drafts and independent signed reviews.

No user-supplied membership, owner acceptance, evidence or capacity can enter this
path. Every member is compared using the existing route/policy engine. Summed
logical VM demand is a baseline, not a reservation or a physical storage estimate.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from provisioner.controlplane.persistence.store import TenantContext

from .application_drafts import ApplicationDraftRepository, parse_content, _digest, _sha
from .application_review import MAX_REVIEW_AGE
from .application_reviews import ApplicationReviewService, ApplicationReviewUnavailable, REVIEW_STATUSES
from .grouping import OwnerReview, reviewed_candidate
from .model import NativeIdentity, _id, _json, _utc
from .service import AssessmentDestination, AssessmentMember, AssessmentSelection, AssessmentService
from .trust import _time
from .routes import METHODS, native_scope_key

MAX_RESPONSE_BYTES = 1024 * 1024
_MAX = 2**63 - 1
_READY = frozenset({'REVIEWED_ASSESSMENT_ONLY', 'REVIEWED_WITH_UNKNOWNS'})


@dataclass(frozen=True, slots=True)
class ApplicationMemberProfile:
    workload_id: str
    guest_profile: str

    def __post_init__(self):
        if not _id(self.workload_id) or not _id(self.guest_profile):
            raise ValueError('Exact logical workload and guest profile are required')


def _known(obj, name):
    fact = next((fact for fact in obj.facts if fact.name == name), None) if obj else None
    return fact.value() if fact is not None and fact.state == 'KNOWN' else None


def aggregate_capacity(inventory, members, target):
    """Sum *all* normalized VM requirements; never sum separate target pools.

    Missing values, zero-sized requirements and overflow remain unknown. This
    deliberately excludes guessed overcommit, deduplication, quotas-as-capacity,
    transient copies and N+1 headroom; these require the later reservation owner.
    """
    available_slots = _known(target, 'availableVmCount')
    if type(available_slots) is not int or not 0 <= available_slots <= _MAX:
        available_slots = None
    resources = {'VM_COUNT': {'required': len(members), 'available': available_slots}}
    issues = ([{'severity': 'UNKNOWN', 'code': 'APPLICATION_VM_COUNT_CAPACITY_UNKNOWN'}]
              if available_slots is None else
              [{'severity': 'BLOCKER', 'code': 'APPLICATION_VM_COUNT_CAPACITY_INSUFFICIENT'}]
              if available_slots < len(members) else [])
    objects = {obj.identity: obj for obj in inventory.objects} if inventory else {}
    for source_name, available_name, label in (
            ('vcpuCount', 'availableVcpu', 'VCPU'),
            ('memorySizeBytes', 'availableMemoryBytes', 'MEMORY'),
            ('diskCapacityBytes', 'availableStorageBytes', 'STORAGE')):
        values = [_known(objects.get(member), source_name) for member in members]
        required = (sum(values) if values and all(type(value) is int and 0 < value <= _MAX
                                                 for value in values) else None)
        if required is not None and required > _MAX:
            required = None
        available = _known(target, available_name)
        if type(available) is not int or not 0 <= available <= _MAX:
            available = None
        resources[label] = {'required': required, 'available': available}
        if required is None:
            issues.append({'severity': 'UNKNOWN', 'code': 'APPLICATION_' + label + '_DEMAND_UNKNOWN'})
        if available is None:
            issues.append({'severity': 'UNKNOWN', 'code': 'APPLICATION_' + label + '_CAPACITY_UNKNOWN'})
        elif required is not None and required > available:
            issues.append({'severity': 'BLOCKER', 'code': 'APPLICATION_' + label + '_CAPACITY_INSUFFICIENT'})
    return {'basis': 'SUM_OF_OBSERVED_LOGICAL_VM_REQUIREMENTS', 'memberCount': len(members),
            'resources': resources, 'reservationHeld': False,
            'transientAndRecoveryFootprintIncluded': False}, issues


class ApplicationAssessmentService:
    """Read-only composition of actual review, draft and comparison services."""

    def __init__(self, drafts: ApplicationDraftRepository, reviews: ApplicationReviewService,
                 assessments: AssessmentService):
        if (not isinstance(drafts, ApplicationDraftRepository)
                or not isinstance(reviews, ApplicationReviewService)
                or not isinstance(assessments, AssessmentService)):
            raise TypeError('Application assessment requires existing repository/service owners')
        self._drafts, self._reviews, self._assessments = drafts, reviews, assessments

    def compare(self, ctx: TenantContext, actor: str, source: AssessmentSelection,
                application_group_id: str, *, revision: int, record_digest: str,
                profiles: tuple[ApplicationMemberProfile, ...],
                destinations: tuple[AssessmentDestination, ...],
                method: str, network_mode: str, data_mode: str) -> dict:
        if (not isinstance(source, AssessmentSelection) or not _id(application_group_id)
                or type(revision) is not int or not 1 <= revision <= _MAX or not _sha(record_digest)
                or not isinstance(profiles, tuple) or not 2 <= len(profiles) <= 100
                or any(not isinstance(profile, ApplicationMemberProfile) for profile in profiles)
                or len({profile.workload_id for profile in profiles}) != len(profiles)
                or not isinstance(destinations, tuple) or not 2 <= len(destinations) <= 20
                or any(not isinstance(target, AssessmentDestination) for target in destinations)
                or len(profiles) * len(destinations) > 200):
            raise ValueError('Exact draft, complete member profiles and bounded destinations are required')
        service = self._assessments
        now = service._clock()
        if not _utc(now):
            raise ValueError('A trusted UTC assessment clock is required')
        origin = service._resolve(ctx, actor, source, 'SOURCE_READ', now)
        targets = tuple(service._resolve(ctx, actor, item.selection, 'DESTINATION_READ', now)
                        for item in destinations)
        scopes = (origin.installation.scope, *(target.installation.scope for target in targets))
        if (len({native_scope_key(scope) for scope in scopes}) != len(scopes)
                or len({source.environment_id, *(item.selection.environment_id for item in destinations)})
                   != len(destinations) + 1
                or method not in METHODS or not _id(network_mode) or not _id(data_mode)):
            raise ValueError('Distinct exact scopes and supported route selections are required')

        def authorize(scope, at: datetime):
            if service._resolve(ctx, actor, source, 'SOURCE_READ', at).installation != origin.installation:
                raise PermissionError('Application source authority changed')
            if scope != origin.installation.scope:
                raise PermissionError('Application read escaped the selected source')

        def read_review():
            view = self._reviews.get(ctx, scopes[0], source.environment_id, application_group_id,
                                     revision=revision, authorize=authorize)
            if view is None:
                raise LookupError('Application draft not found')
            if (view.get('scope') != vars(scopes[0]) or view.get('environmentId') != source.environment_id
                    or view.get('applicationGroupId') != application_group_id
                    or type(view.get('draftRevision')) is not int or view['draftRevision'] != revision
                    or view.get('draftRecordDigest') != record_digest
                    or type(view.get('generation')) is not int or view['generation'] != source.generation
                    or view.get('format') != 'hosting-application-review-status/1'
                    or view.get('status') not in REVIEW_STATUSES
                    or any(view.get(field) is not False for field in
                           ('ownershipAccepted', 'executionAuthorized', 'dependencyEvidenceVerified'))):
                raise ApplicationReviewUnavailable('Application review differs from the exact selection')
            return view

        review = read_review()
        selection = {'source': {'environmentId': source.environment_id, 'generation': source.generation},
            'applicationGroupId': application_group_id, 'draftRevision': revision,
            'draftRecordDigest': record_digest,
            'memberProfiles': [{'workloadId': item.workload_id, 'guestProfile': item.guest_profile}
                               for item in profiles],
            'destinations': [dict(environmentId=item.selection.environment_id,
                generation=item.selection.generation, **({'capacityKind': item.capacity_kind,
                'capacityNativeId': item.capacity_native_id} if item.capacity_kind is not None else {}))
                for item in destinations],
            'method': method, 'networkMode': network_mode, 'dataMode': data_mode}
        report = {'format': 'hosting-application-comparison/2', 'selectionDigest': _digest(selection),
            'applicationReview': review,
            'sourceInput': None, 'destinationInputs': [], 'assessments': [],
            'status': 'HELD_APPLICATION_REVIEW', 'consistency': 'PINNED_INPUTS_LIVE_RECHECKS',
            'ownershipAccepted': False, 'executionAuthorized': False,
            'dependencyEvidenceVerified': False, 'reservationHeld': False}
        if review['status'] not in _READY:
            return report
        document = self._drafts.get(ctx, scopes[0], source.environment_id, application_group_id,
                                    revision=revision, authorize=authorize)
        if (not isinstance(document, dict) or document.get('recordDigest') != record_digest
                or document.get('generation') != source.generation
                or document.get('resultDigest') != review['resultDigest']
                or document.get('proposalDigest') != review['proposalDigest']
                or _digest(document.get('proposal')) != review['proposalDigest']
                or document.get('status') != 'UNREVIEWED'
                or document.get('ownershipAccepted') is not False
                or document.get('executionAuthorized') is not False):
            raise ApplicationReviewUnavailable('Retained application proposal binding changed')
        proposal = document['proposal']
        draft, dependencies = parse_content({'draft': proposal['draft'], 'dependencies': proposal['dependencies']})
        selected = {profile.workload_id: profile.guest_profile for profile in profiles}
        if set(selected) != {member.workload_id for member in draft.members}:
            raise ValueError('Profiles must cover every retained member exactly once')
        members = tuple(AssessmentMember(member.native_vm.native_id, selected[member.workload_id])
                        for member in draft.members)
        comparisons = service.compare_many(ctx, actor, source, members, destinations,
                            method=method, network_mode=network_mode, data_mode=data_mode)
        first = comparisons[0]
        if (first.source.installation != origin.installation or first.source.discovery is None
                or first.source.discovery.original.digest != review['resultDigest']
                or tuple(pin.installation for pin in first.destinations) !=
                   tuple(target.installation for target in targets)):
            raise ApplicationReviewUnavailable('Comparison no longer matches the reviewed source and targets')
        candidate = reviewed_candidate(first.source.discovery.original, draft, dependencies,
            OwnerReview(review['ownerId'], scopes[0], review['reviewReference'],
                        _time(review['reviewedAt']), review['proposalDigest']),
            checked_at=_time(review['checkedAt']), max_age=MAX_REVIEW_AGE)
        if candidate.digest != review['candidateDigest']:
            raise ApplicationReviewUnavailable('Reviewed candidate no longer binds the retained proposal')
        for index, (destination, pin) in enumerate(zip(destinations, first.destinations)):
            inventory = pin.discovery.inventory if pin.discovery else None
            scope = pin.installation.scope
            identity = (NativeIdentity(scope.endpoint_id, scope.native_scope_id, scope.platform_family,
                        destination.capacity_kind, destination.capacity_native_id)
                        if destination.capacity_kind else None)
            pool = next((obj for obj in inventory.objects if obj.identity == identity), None) if inventory else None
            capacity, issues = aggregate_capacity(first.source.discovery.inventory,
                                        tuple(member.native_vm for member in draft.members), pool)
            # Single-VM checks never establish application-wide traffic, data
            # consistency or transient/reserve footprint, even with no unknown edges.
            issues.extend(({'severity': 'CONDITION', 'code': 'APPLICATION_POLICY_DATA_REVIEW_REQUIRED'},
                           {'severity': 'CONDITION', 'code': 'APPLICATION_RESERVATION_NOT_HELD'}))
            if candidate.unknown_edges:
                issues.append({'severity': 'UNKNOWN', 'code': 'APPLICATION_DEPENDENCIES_UNRESOLVED'})
            if any(edge.source != 'APPLICATION_OWNER' for edge in dependencies):
                issues.append({'severity': 'UNKNOWN', 'code': 'APPLICATION_DEPENDENCY_EVIDENCE_UNVERIFIED'})
            rows = []
            for member, comparison in zip(draft.members, comparisons):
                assessed = comparison.assessments[index]
                rows.append({'workloadId': member.workload_id, 'nativeVm': list(member.native_vm.key()),
                    'guestProfile': assessed.guest_profile, 'assessedAt': comparison.assessed_at.isoformat(),
                    'status': assessed.status, 'issues': [
                        {'severity': issue.severity, 'code': issue.code} for issue in assessed.issues],
                    'executionAuthorized': False})
            severity = {issue['severity'] for issue in issues}
            severity.update(issue['severity'] for row in rows for issue in row['issues'])
            status = 'BLOCKED' if 'BLOCKER' in severity else 'UNKNOWN' if 'UNKNOWN' in severity else 'CONDITIONAL'
            report['assessments'].append({'environmentId': destination.selection.environment_id,
                'status': status, 'capacity': capacity, 'capacityIdentity': list(identity.key()) if identity else None,
                'issues': issues, 'members': rows, 'executionAuthorized': False})
        # Re-read the independent decision after *all* member comparisons. A
        # revoked key, changed decision/draft/source or newly expired review
        # cannot leave previously computed application rows publishable.
        final_review = read_review()
        if {k: v for k, v in final_review.items() if k != 'checkedAt'} != {
                k: v for k, v in review.items() if k != 'checkedAt'}:
            raise ApplicationReviewUnavailable('Owner review or source changed during comparison')
        report.update(status='ASSESSED_NOT_AUTHORIZED', applicationReview=final_review,
            sourceInput=first.source.to_document(), destinationInputs=[pin.to_document() for pin in first.destinations],
            startupOrder=list(draft.startup_order), datasetCount=len(draft.dataset_ids),
            consistencyGroupCount=len(draft.consistency_groups))
        if len(_json(report).encode('ascii')) > MAX_RESPONSE_BYTES:
            raise ValueError('Application comparison exceeds the response bound; choose fewer destinations')
        return report
