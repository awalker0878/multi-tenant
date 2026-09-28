"""Read-only brownfield mapping proposal; never an import or execution grant.

The caller obtains a verified owner review, the latest persisted discovery
digest, and native ownership through trusted services. This module validates
their consistency and produces only a review artifact. A later adoption writer
must independently recheck current generation and ownership in one transaction.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable, Literal

from provisioner.controlplane.authority.model import PlanScope
from provisioner.controlplane.discovery.model import (
    DiscoveryFact, DiscoveryResult, NativeIdentity,
)
from provisioner.domain.enterprise_records import validate_record
from provisioner.controlplane.persistence.store import canonical_record_digest


_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$')
_DIGEST = re.compile(r'^[0-9a-f]{64}$')
_REQUIRED = {
    'vm': ('cpuCount', 'memoryMiB', 'firmware'),
    'disk': ('sizeBytes', 'format'),
    'nic': ('network',),
    'volume': ('sizeBytes',),
    'dataset': ('sizeBytes',),
}


def _utc(value: datetime) -> bool:
    return (isinstance(value, datetime) and value.tzinfo is not None
            and value.utcoffset() == timedelta(0))


def _identity_json(identity: NativeIdentity) -> dict:
    return dict(endpointId=identity.endpoint_id,
                nativeScopeId=identity.native_scope_id,
                platformFamily=identity.platform_family,
                resourceKind=identity.resource_kind,
                nativeId=identity.native_id)


def _digest(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(',', ':'),
                     ensure_ascii=True, allow_nan=False).encode('utf-8')
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True, slots=True)
class WorkloadReview:
    """Exact owner-review record; constructing it does not verify the actor."""

    organization_id: str
    tenant_id: str
    security_domain_id: str
    workload_id: str
    revision: int
    workload_digest: str
    source_scope: PlanScope
    reviewer_subject: str
    reviewed_at: datetime
    expires_at: datetime

    def __post_init__(self) -> None:
        if (not all(isinstance(value, str) and _ID.fullmatch(value)
                    for value in (self.organization_id, self.tenant_id,
                                  self.security_domain_id, self.workload_id))
                or type(self.revision) is not int or self.revision < 1
                or not isinstance(self.workload_digest, str)
                or not _DIGEST.fullmatch(self.workload_digest)
                or not isinstance(self.source_scope, PlanScope)
                or (self.source_scope.organization_id,
                    self.source_scope.tenant_id,
                    self.source_scope.security_domain_id) != (
                        self.organization_id, self.tenant_id,
                        self.security_domain_id)
                or not isinstance(self.reviewer_subject, str)
                or not self.reviewer_subject.strip()
                or len(self.reviewer_subject) > 512
                or not _utc(self.reviewed_at) or not _utc(self.expires_at)
                or not self.reviewed_at < self.expires_at
                or self.expires_at - self.reviewed_at > timedelta(days=1)):
            raise ValueError('Invalid exact workload owner review')


@dataclass(frozen=True, slots=True)
class AdoptionSelection:
    machine_id: str | None
    component_id: str
    native: NativeIdentity

    def __post_init__(self) -> None:
        if ((self.machine_id is not None and
             (not isinstance(self.machine_id, str)
              or not _ID.fullmatch(self.machine_id)))
                or not isinstance(self.component_id, str)
                or not _ID.fullmatch(self.component_id)
                or not isinstance(self.native, NativeIdentity)
                or self.native.resource_kind not in _REQUIRED):
            raise ValueError('Invalid selected native component')

    def component_key(self) -> tuple[str | None, str, str]:
        return (self.machine_id, self.native.resource_kind, self.component_id)


@dataclass(frozen=True, slots=True)
class NativeOwner:
    """Current authoritative ownership lookup result, not a reservation."""

    organization_id: str
    tenant_id: str
    security_domain_id: str
    workload_id: str

    def __post_init__(self) -> None:
        if not all(isinstance(value, str) and _ID.fullmatch(value)
                   for value in (self.organization_id, self.tenant_id,
                                 self.security_domain_id, self.workload_id)):
            raise ValueError('Invalid authoritative native owner')


@dataclass(frozen=True, slots=True, order=True)
class AdoptionHold:
    code: str
    reference: str

    def __post_init__(self) -> None:
        if (not isinstance(self.code, str) or not _ID.fullmatch(self.code)
                or not isinstance(self.reference, str)
                or not self.reference or len(self.reference) > 1024
                or any(ord(char) < 32 or ord(char) == 127
                       for char in self.reference)):
            raise ValueError('Invalid adoption hold')


@dataclass(frozen=True, slots=True)
class AdoptionProposal:
    workload_id: str
    workload_revision: int
    workload_digest: str
    security_domain_id: str
    source_scope: PlanScope
    discovery_digest: str
    authorization_digest: str
    reviewer_subject: str
    checked_at: datetime
    selections: tuple[AdoptionSelection, ...]
    holds: tuple[AdoptionHold, ...]
    status: Literal['REVIEWABLE', 'HELD']
    action: Literal['NO_CHANGE_REVIEW'] = 'NO_CHANGE_REVIEW'
    digest: str = field(init=False)

    def __post_init__(self) -> None:
        if (not _ID.fullmatch(self.workload_id)
                or type(self.workload_revision) is not int
                or self.workload_revision < 1
                or not _DIGEST.fullmatch(self.workload_digest)
                or not _ID.fullmatch(self.security_domain_id)
                or not isinstance(self.source_scope, PlanScope)
                or not _DIGEST.fullmatch(self.discovery_digest)
                or not _DIGEST.fullmatch(self.authorization_digest)
                or not self.reviewer_subject or not _utc(self.checked_at)
                or not isinstance(self.selections, tuple)
                or any(not isinstance(item, AdoptionSelection)
                       for item in self.selections)
                or not isinstance(self.holds, tuple)
                or any(not isinstance(hold, AdoptionHold) for hold in self.holds)
                or self.status != ('HELD' if self.holds else 'REVIEWABLE')
                or self.action != 'NO_CHANGE_REVIEW'):
            raise ValueError('Invalid immutable no-change adoption proposal')
        payload = dict(format='hosting-adoption-proposal/1',
                       action=self.action, status=self.status,
                       workloadId=self.workload_id,
                       workloadRevision=self.workload_revision,
                       workloadDigest=self.workload_digest,
                       securityDomainId=self.security_domain_id,
                       sourceScope=dict(organizationId=self.source_scope.organization_id,
                                        tenantId=self.source_scope.tenant_id,
                                        siteId=self.source_scope.site_id,
                                        securityDomainId=self.source_scope.security_domain_id,
                                        endpointId=self.source_scope.endpoint_id,
                                        nativeScopeId=self.source_scope.native_scope_id,
                                        platformFamily=self.source_scope.platform_family),
                       discoveryDigest=self.discovery_digest,
                       authorizationDigest=self.authorization_digest,
                       reviewerSubject=self.reviewer_subject,
                       checkedAt=self.checked_at.isoformat(),
                       selections=[dict(machineId=s.machine_id,
                                        componentId=s.component_id,
                                        binding=_identity_json(s.native))
                                   for s in self.selections],
                       holds=[dict(code=h.code, reference=h.reference)
                              for h in self.holds])
        object.__setattr__(self, 'digest', _digest(payload))


def _components(workload: dict) -> tuple[dict, list[AdoptionHold]]:
    """Map every reviewed logical component to an allowed source binding."""
    expected: dict[tuple[str | None, str, str],
                   tuple[tuple[dict, ...], dict[str, object]]] = {}
    holds: list[AdoptionHold] = []
    for machine in workload['spec']['machines']:
        machine_id = machine['machineId']
        expected[(machine_id, 'vm', machine_id)] = (
            tuple(entry['binding'] for entry in machine['bindings']
                  if entry['role'] == 'SOURCE'),
            {name: machine[name]['value'] for name in _REQUIRED['vm']
             if machine[name]['state'] == 'KNOWN'})
        for required in ('guestProfile', 'cpuCount', 'memoryMiB', 'firmware'):
            if machine[required]['state'] != 'KNOWN':
                holds.append(AdoptionHold('REVIEWED_FACT_UNKNOWN',
                                          f'{machine_id}.{required}'))
        for kind, plural, component_name, requirements in (
                ('disk', 'disks', 'diskId', ('sizeBytes', 'format')),
                ('nic', 'nics', 'nicId', ('network',))):
            if not machine[plural + 'Complete']:
                holds.append(AdoptionHold('REVIEWED_COLLECTION_INCOMPLETE',
                                          f'{machine_id}.{plural}'))
            for item in machine[plural]:
                component = item[component_name]
                expected[(machine_id, kind, component)] = (
                    tuple(entry['binding'] for entry in item['bindings']
                          if entry['role'] == 'SOURCE'),
                    {name: item[name]['value'] for name in requirements
                     if item[name]['state'] == 'KNOWN'})
                for required in requirements:
                    if item[required]['state'] != 'KNOWN':
                        holds.append(AdoptionHold('REVIEWED_FACT_UNKNOWN',
                                                  f'{component}.{required}'))
    for dataset in workload['spec']['datasets']:
        sources = dataset['sourceBindings']
        if len(sources) != 1 or sources[0]['resourceKind'] not in ('volume', 'dataset'):
            holds.append(AdoptionHold('DATASET_MAPPING_AMBIGUOUS',
                                      dataset['datasetId']))
            continue
        kind = sources[0]['resourceKind']
        expected[(dataset['machineId'], kind, dataset['datasetId'])] = (
            (sources[0],),
            {'sizeBytes': dataset['sizeBytes']['value']}
            if dataset['sizeBytes']['state'] == 'KNOWN' else {})
        if dataset['sizeBytes']['state'] != 'KNOWN':
            holds.append(AdoptionHold('REVIEWED_FACT_UNKNOWN',
                                      f"{dataset['datasetId']}.sizeBytes"))
    return expected, holds


def _same_native(binding: dict, identity: NativeIdentity) -> bool:
    return (binding['endpointId'], binding['nativeScopeId'],
            binding['platformFamily'], binding['resourceKind'],
            binding['nativeId']) == identity.key()


def propose_brownfield_adoption(
    result: DiscoveryResult,
    reviewed_workload: dict,
    review: WorkloadReview,
    selections: tuple[AdoptionSelection, ...], *,
    current_result_digest: str | None,
    checked_at: datetime,
    max_observation_age: timedelta,
    owner_lookup: Callable[[NativeIdentity], NativeOwner | None],
) -> AdoptionProposal:
    """Produce a held or reviewable mapping without touching native state.

    A REVIEWABLE result means the displayed mapping has no detected conflict
    at `checked_at`. It is never an adoption, native ownership claim, approval,
    or authority to run a platform operation.
    """
    if (not isinstance(result, DiscoveryResult)
            or not isinstance(review, WorkloadReview)
            or not isinstance(selections, tuple) or not selections
            or len(selections) > 1000
            or any(not isinstance(s, AdoptionSelection) for s in selections)
            or not _utc(checked_at)
            or not isinstance(max_observation_age, timedelta)
            or not timedelta(0) < max_observation_age <= timedelta(hours=1)
            or not callable(owner_lookup)
            or current_result_digest is not None and (
                not isinstance(current_result_digest, str)
                or not _DIGEST.fullmatch(current_result_digest))):
        raise ValueError('Invalid bounded adoption proposal input')
    if not isinstance(reviewed_workload, dict) or validate_record(reviewed_workload):
        raise ValueError('A valid canonical reviewed Workload is required')
    if reviewed_workload['kind'] != 'Workload':
        raise ValueError('Review must select one Workload record')
    meta = reviewed_workload['metadata']
    workload_digest = canonical_record_digest(reviewed_workload)
    if ((meta['organizationId'], meta['tenantId'], meta['wsdId'],
         meta['workloadId'], meta['revision'], workload_digest) !=
        (review.organization_id, review.tenant_id,
         review.security_domain_id, review.workload_id,
         review.revision, review.workload_digest)):
        raise ValueError('Owner review does not bind the exact workload revision')
    holds: list[AdoptionHold] = []
    def hold(code: str, reference: str) -> None:
        holds.append(AdoptionHold(code, reference))

    if (reviewed_workload['spec']['state'] == 'MANAGED'
            or reviewed_workload['spec']['membership']['state'] != 'ACCEPTED'):
        hold('WORKLOAD_NOT_BROWNFIELD', review.workload_id)
    if not review.reviewed_at <= checked_at < review.expires_at:
        hold('OWNER_REVIEW_STALE', review.workload_id)
    scope = result.scope
    if scope != review.source_scope:
        hold('CROSS_SCOPE_DISCOVERY', result.campaign_id)
    if result.completeness != 'COMPLETE':
        hold('DISCOVERY_INCOMPLETE', result.campaign_id)
    if current_result_digest != result.digest:
        hold('DISCOVERY_NOT_CURRENT', result.campaign_id)
    if (result.captured_at > checked_at
            or checked_at - result.captured_at >= max_observation_age):
        hold('DISCOVERY_STALE', result.campaign_id)

    expected, component_holds = _components(reviewed_workload)
    holds.extend(component_holds)
    observed = {obj.identity.key(): obj for obj in result.objects}
    selected_components = set()
    selected_native = set()
    for selection in selections:
        key = selection.component_key()
        identity_key = selection.native.key()
        reference = f'{selection.native.resource_kind}:{selection.native.native_id}'
        duplicate = key in selected_components or identity_key in selected_native
        if duplicate:
            hold('DUPLICATE_SELECTION', reference)
        selected_components.add(key)
        selected_native.add(identity_key)
        reviewed = key in expected
        if key not in expected:
            hold('UNREVIEWED_COMPONENT', reference)
        elif expected[key][0] and not any(
                _same_native(binding, selection.native)
                for binding in expected[key][0]):
            hold('REVIEWED_BINDING_MISMATCH', reference)
            reviewed = False
        in_scope = (selection.native.endpoint_id,
                    selection.native.native_scope_id,
                    selection.native.platform_family) == (
                scope.endpoint_id, scope.native_scope_id, scope.platform_family)
        if not in_scope:
            hold('CROSS_SCOPE_BINDING', reference)
        resource = observed.get(identity_key)
        if resource is None:
            hold('NATIVE_IDENTITY_NOT_OBSERVED', reference)
        else:
            facts: dict[str, DiscoveryFact] = {f.name: f for f in resource.facts}
            for required in _REQUIRED[selection.native.resource_kind]:
                if required not in facts or facts[required].state != 'KNOWN':
                    hold('REQUIRED_FACT_UNKNOWN', f'{reference}.{required}')
                elif (key in expected and required in expected[key][1]
                      and (type(facts[required].value()) is not
                           type(expected[key][1][required])
                           or facts[required].value() !=
                           expected[key][1][required])):
                    hold('REVIEWED_FACT_MISMATCH', f'{reference}.{required}')
        # A caller may submit an arbitrary native ID. Do not make an
        # authoritative cross-tenant ownership oracle from such a selection.
        if reviewed and in_scope and resource is not None and not duplicate:
            try:
                owner = owner_lookup(selection.native)
            except Exception:
                hold('OWNERSHIP_LOOKUP_UNAVAILABLE', reference)
            else:
                if owner is not None and not isinstance(owner, NativeOwner):
                    hold('OWNERSHIP_LOOKUP_UNAVAILABLE', reference)
                elif owner is not None:
                    hold('NATIVE_OWNERSHIP_CONFLICT', reference)
    for key in expected.keys() - selected_components:
        hold('COMPONENT_NOT_SELECTED', ':'.join(str(item) for item in key))
    unique_holds = tuple(sorted(set(holds)))
    ordered = tuple(sorted(selections, key=lambda s:
                           (s.machine_id or '', s.native.resource_kind,
                            s.component_id, s.native.key())))
    return AdoptionProposal(review.workload_id, review.revision,
                            review.workload_digest, review.security_domain_id,
                            review.source_scope,
                            result.digest, result.authorization_digest,
                            review.reviewer_subject, checked_at, ordered,
                            unique_holds,
                            'HELD' if unique_holds else 'REVIEWABLE')
