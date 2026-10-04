"""Read-only, exact-scope comparison of observed workloads and destinations.

The caller must authenticate campaign results, installed tuple provenance and
independent review artifacts before invoking this module, and authorize each
source and destination read for the requesting operator. Constructing these
values is not that verification. An assessment cannot grant a native operation,
approve a plan, adopt a discovered workload or make a downtime guarantee.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

from provisioner.controlplane.authority.model import PlanScope

from .compatibility import check_compatibility
from .model import DiscoveryFact, DiscoveryObject, DiscoveryResult, NativeIdentity
from .routes import (METHODS, InstalledTuple, RouteCatalogue, RouteKey,
                     _utc, native_scope_key)


_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$')
_DIGEST = re.compile(r'^[0-9a-f]{64}$')
_CONTROLS = ('POLICY_TRANSLATION', 'SECURITY_EQUIVALENCE', 'RECOVERY_READINESS')
_SEVERITIES = {'BLOCKER', 'UNKNOWN', 'CONDITION'}
_MAX_BYTES = 2**63 - 1


@dataclass(frozen=True, slots=True)
class AssessmentScopeAccess:
    """Service-verified read selection for one exact native scope and actor.

    This must come from the authoritative directory/access service, not from
    an HTTP body or a discovered platform fact. The read selection carries no
    campaign, adoption, migration or provisioning authority.
    """

    scope: PlanScope
    purpose: Literal['SOURCE_READ', 'DESTINATION_READ']
    actor_subject: str
    authorization_reference: str
    observed_at: datetime
    expires_at: datetime

    def __post_init__(self) -> None:
        if (not isinstance(self.scope, PlanScope)
                or self.purpose not in ('SOURCE_READ', 'DESTINATION_READ')
                or not isinstance(self.actor_subject, str)
                or not 1 <= len(self.actor_subject) <= 512
                or any(ord(char) < 32 or ord(char) == 127 for char in self.actor_subject)
                or not isinstance(self.authorization_reference, str)
                or not _ID.fullmatch(self.authorization_reference)
                or not _utc(self.observed_at) or not _utc(self.expires_at)
                or self.expires_at <= self.observed_at):
            raise ValueError('Invalid exact-scope read selection')


@dataclass(frozen=True, slots=True)
class ReviewedFinding:
    """One current, independently verified claim, bound to both observations.

    The service verifies the issuer, signature, reviewer authority and custody
    before passing this record in. The value itself is not a trust credential.
    """

    control: Literal['POLICY_TRANSLATION', 'SECURITY_EQUIVALENCE',
                     'RECOVERY_READINESS']
    route: RouteKey
    source_snapshot_digest: str
    destination_snapshot_digest: str
    outcome: Literal['PASS', 'FAIL']
    evidence_id: str
    evidence_digest: str
    observed_at: datetime
    expires_at: datetime

    def __post_init__(self) -> None:
        if (self.control not in _CONTROLS or not isinstance(self.route, RouteKey)
                or self.outcome not in ('PASS', 'FAIL')
                or not all(isinstance(value, str) and _DIGEST.fullmatch(value)
                           for value in (self.source_snapshot_digest,
                                         self.destination_snapshot_digest,
                                         self.evidence_digest))
                or not isinstance(self.evidence_id, str)
                or not _ID.fullmatch(self.evidence_id)
                or not _utc(self.observed_at) or not _utc(self.expires_at)
                or self.expires_at <= self.observed_at):
            raise ValueError('Invalid reviewed finding or snapshot binding')


@dataclass(frozen=True, slots=True)
class DestinationOption:
    installation: InstalledTuple
    inventory: DiscoveryResult | None
    capacity_identity: NativeIdentity | None
    findings: tuple[ReviewedFinding, ...] = ()
    access: AssessmentScopeAccess | None = None

    def __post_init__(self) -> None:
        if (not isinstance(self.installation, InstalledTuple)
                or self.inventory is not None
                and (not isinstance(self.inventory, DiscoveryResult)
                     or self.inventory.scope != self.installation.scope)
                or self.capacity_identity is not None
                and (not isinstance(self.capacity_identity, NativeIdentity)
                     or self.capacity_identity.resource_kind not in
                     {'pool', 'cluster', 'quota', 'datastore'}
                     or not _matches(self.installation, self.capacity_identity))
                or not isinstance(self.findings, tuple)
                or any(not isinstance(item, ReviewedFinding)
                       for item in self.findings)
                or self.access is not None
                and not isinstance(self.access, AssessmentScopeAccess)):
            raise ValueError('Destination facts must bind one exact installed scope')


@dataclass(frozen=True, slots=True)
class AssessmentIssue:
    severity: Literal['BLOCKER', 'UNKNOWN', 'CONDITION']
    code: str
    reason: str
    remediation: str

    def __post_init__(self) -> None:
        if (self.severity not in _SEVERITIES or not isinstance(self.code, str)
                or not _ID.fullmatch(self.code)
                or not isinstance(self.reason, str) or not self.reason
                or not isinstance(self.remediation, str) or not self.remediation):
            raise ValueError('Invalid assessment issue')


@dataclass(frozen=True, slots=True)
class TransferEstimate:
    """Copy-phase arithmetic only; never an outage or completion promise."""

    transfer_bytes: int | None
    copy_phase_seconds: int | None
    confidence: Literal['NONE', 'LOW']
    basis: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DestinationAssessment:
    source: InstalledTuple
    destination: InstalledTuple
    workload: NativeIdentity
    method: str
    guest_profile: str
    network_mode: str
    data_mode: str
    source_snapshot_digest: str | None
    destination_snapshot_digest: str | None
    route_maturity: str
    status: Literal['ELIGIBLE', 'CONDITIONAL', 'BLOCKED', 'UNKNOWN']
    issues: tuple[AssessmentIssue, ...]
    estimate: TransferEstimate
    execution_authorized: bool = False

    def __post_init__(self) -> None:
        if self.execution_authorized is not False:
            raise ValueError('Assessments cannot authorize execution')

    @property
    def blockers(self) -> tuple[str, ...]:
        return tuple(item.code for item in self.issues if item.severity == 'BLOCKER')

    @property
    def unknowns(self) -> tuple[str, ...]:
        return tuple(item.code for item in self.issues if item.severity == 'UNKNOWN')

    @property
    def conditions(self) -> tuple[str, ...]:
        return tuple(item.code for item in self.issues if item.severity == 'CONDITION')

    def to_document(self) -> dict:
        """A presentation record; the API must enforce scoped read permission."""
        return {
            'format': 'hosting-destination-assessment/1',
            'source': _installation_doc(self.source),
            'destination': _installation_doc(self.destination),
            'workload': {'endpointId': self.workload.endpoint_id,
                         'nativeScopeId': self.workload.native_scope_id,
                         'platformFamily': self.workload.platform_family,
                         'resourceKind': self.workload.resource_kind,
                         'nativeId': self.workload.native_id},
            'method': self.method, 'guestProfile': self.guest_profile,
            'networkMode': self.network_mode, 'dataMode': self.data_mode,
            'sourceSnapshotDigest': self.source_snapshot_digest,
            'destinationSnapshotDigest': self.destination_snapshot_digest,
            'routeMaturity': self.route_maturity, 'status': self.status,
            'issues': [{'severity': issue.severity, 'code': issue.code,
                        'reason': issue.reason, 'remediation': issue.remediation}
                       for issue in self.issues],
            'estimate': {'transferBytes': self.estimate.transfer_bytes,
                         'copyPhaseSeconds': self.estimate.copy_phase_seconds,
                         'confidence': self.estimate.confidence,
                         'basis': list(self.estimate.basis)},
            'executionAuthorized': False,
        }


def _installation_doc(installed: InstalledTuple) -> dict:
    scope = installed.scope
    return {'organizationId': scope.organization_id, 'tenantId': scope.tenant_id,
            'locationId': scope.site_id,
            'securityDomainId': scope.security_domain_id,
            'endpointId': scope.endpoint_id, 'nativeScopeId': scope.native_scope_id,
            'platformFamily': scope.platform_family,
            'productTupleId': installed.product_tuple_id,
            'productTupleDigest': installed.product_tuple_digest}


def _matches(installed: InstalledTuple, identity: NativeIdentity) -> bool:
    scope = installed.scope
    return (scope.endpoint_id, scope.native_scope_id, scope.platform_family) == (
        identity.endpoint_id, identity.native_scope_id, identity.platform_family)


def _fact(obj: DiscoveryObject, name: str) -> object | None:
    selected = next((fact for fact in obj.facts if fact.name == name), None)
    return selected.value() if selected is not None and selected.state == 'KNOWN' else None


def _positive(value: object) -> bool:
    return type(value) is int and 0 < value <= _MAX_BYTES


def _available(value: object) -> bool:
    return type(value) is int and 0 <= value <= _MAX_BYTES


def _option_key(option: DestinationOption) -> tuple:
    installed = option.installation
    scope = installed.scope
    return (scope.organization_id, scope.tenant_id, scope.site_id,
            scope.security_domain_id, scope.endpoint_id, scope.native_scope_id,
            scope.platform_family, installed.product_tuple_id,
            installed.product_tuple_digest)


class AssessmentEngine:
    """Pure comparison over already authenticated, authorized observations."""

    def __init__(self, routes: RouteCatalogue) -> None:
        if not isinstance(routes, RouteCatalogue):
            raise ValueError('A directed route catalogue is required')
        self.routes = routes

    def compare(
        self, source: InstalledTuple, source_inventory: DiscoveryResult | None,
        workload: NativeIdentity, destinations: tuple[DestinationOption, ...], *,
        method: str, guest_profile: str, network_mode: str, data_mode: str,
        as_of: datetime, source_access: AssessmentScopeAccess | None,
        max_snapshot_age: timedelta = timedelta(hours=24),
    ) -> tuple[DestinationAssessment, ...]:
        """Compare at least two distinct exact destinations in stable tuple order.

        Freshness checks use the service's trusted UTC clock. `ELIGIBLE` means
        the supplied, independently verified claims meet these read-only
        comparison rules. It cannot be used as a grant or plan admission.
        """
        if (not isinstance(source, InstalledTuple)
                or source_inventory is not None and
                (not isinstance(source_inventory, DiscoveryResult)
                 or source_inventory.scope != source.scope)
                or not isinstance(workload, NativeIdentity)
                or workload.resource_kind != 'vm' or not _matches(source, workload)
                or not isinstance(destinations, tuple) or len(destinations) < 2
                or any(not isinstance(option, DestinationOption)
                       for option in destinations)
                or len({native_scope_key(option.installation.scope) for option in destinations})
                != len(destinations)
                or any(native_scope_key(option.installation.scope) == native_scope_key(source.scope)
                       for option in destinations)
                or not all(isinstance(value, str) and _ID.fullmatch(value)
                           for value in (method, guest_profile, network_mode, data_mode))
                or not _utc(as_of)
                or source_access is not None
                and not isinstance(source_access, AssessmentScopeAccess)
                or not isinstance(max_snapshot_age, timedelta)
                or not timedelta(0) < max_snapshot_age <= timedelta(days=7)):
            raise ValueError('Exact source, workload, two destinations and UTC time required')
        return tuple(self._assess(source, source_inventory, workload, option,
                                  method, guest_profile, network_mode, data_mode,
                                  as_of, max_snapshot_age, source_access)
                     for option in sorted(destinations, key=_option_key))

    def _assess(self, source: InstalledTuple,
                source_inventory: DiscoveryResult | None,
                workload: NativeIdentity, option: DestinationOption,
                method: str, guest: str, network: str, data: str,
                as_of: datetime, max_age: timedelta,
                source_access: AssessmentScopeAccess | None) -> DestinationAssessment:
        issues: list[AssessmentIssue] = []

        def add(severity: str, code: str, reason: str, remediation: str) -> None:
            issues.append(AssessmentIssue(severity, code, reason, remediation))

        if source_access is None:
            add('UNKNOWN', 'SOURCE_ACCESS_UNVERIFIED',
                'The operator has no verified source native-scope read selection.',
                'Verify current source access in the authoritative directory.')
        elif (source_access.purpose != 'SOURCE_READ'
              or source_access.scope != source.scope):
            add('BLOCKER', 'SOURCE_ACCESS_SCOPE_MISMATCH',
                'The source access selection does not match the exact native scope.',
                'Select the authorized source endpoint and native scope.')
        elif not source_access.observed_at <= as_of < source_access.expires_at:
            add('UNKNOWN', 'SOURCE_ACCESS_EXPIRED',
                'The source read selection is not current.',
                'Refresh the verified source access selection.')
        if (source.scope.organization_id != option.installation.scope.organization_id
                or source.scope.tenant_id != option.installation.scope.tenant_id):
            add('BLOCKER', 'CROSS_TENANT_DESTINATION',
                'The destination belongs to a different organization or tenant.',
                'Use an in-tenant destination; handle tenant transfer in a separate reviewed process.')
        if option.access is None:
            add('UNKNOWN', 'DESTINATION_ACCESS_UNVERIFIED',
                'The operator has no verified destination native-scope read selection.',
                'Verify current access for this selected destination endpoint and native scope.')
        elif (option.access.purpose != 'DESTINATION_READ'
              or option.access.scope != option.installation.scope
              or source_access is not None
              and option.access.actor_subject != source_access.actor_subject):
            add('BLOCKER', 'DESTINATION_ACCESS_SCOPE_MISMATCH',
                'Destination access belongs to another scope, actor or purpose.',
                'Select a destination authorized for the same operator and exact native scope.')
        elif not option.access.observed_at <= as_of < option.access.expires_at:
            add('UNKNOWN', 'DESTINATION_ACCESS_EXPIRED',
                'The destination read selection is not current.',
                'Refresh the verified destination access selection.')

        key = None
        route = None
        maturity = 'UNKNOWN'
        if method not in METHODS:
            add('BLOCKER', 'METHOD_UNSUPPORTED', 'The migration method is unsupported.',
                'Choose a supported method and qualify an exact directed route.')
        elif (method == 'SAME_PLATFORM_RELOCATION'
              and source.scope.platform_family != option.installation.scope.platform_family):
            add('BLOCKER', 'RELOCATION_REQUIRES_SAME_PLATFORM',
                'Native relocation is not cross-hypervisor migration.',
                'Select and qualify a directed conversion or rebuild route.')
        else:
            key = RouteKey(source, option.installation, method, guest, network, data)
            route = self.routes.evaluate(key, as_of=as_of)
            maturity = route.maturity
            for code in route.blockers:
                severity = ('BLOCKER' if route.status == 'BLOCKED' else
                            'UNKNOWN' if route.status == 'UNKNOWN' else 'CONDITION')
                add(severity, code, 'The exact directed route has a qualification gap.',
                    'Review a current independent source and destination route qualification.')

        selected = None
        if source_inventory is None:
            add('UNKNOWN', 'SOURCE_SNAPSHOT_MISSING', 'No source observation is available.',
                'Run an authorized read-only source discovery campaign.')
        elif not _fresh(source_inventory, as_of, max_age):
            add('UNKNOWN', 'SOURCE_SNAPSHOT_STALE', 'The source observation is not current.',
                'Collect a new exact-scope source generation.')
        else:
            if source_inventory.completeness != 'COMPLETE':
                add('UNKNOWN', 'SOURCE_SNAPSHOT_INCOMPLETE',
                    'The source inventory has collection gaps.',
                    'Resolve missing privileges and collect a complete generation.')
            selected = next((obj for obj in source_inventory.objects
                             if obj.identity == workload), None)
            if selected is None:
                add('UNKNOWN', 'SOURCE_WORKLOAD_NOT_OBSERVED',
                    'The native VM is absent from this source generation.',
                    'Reconcile the native identity against a complete source generation.')

        vcpu = memory = disk = None
        if selected is not None:
            vcpu = _fact(selected, 'vcpuCount')
            if vcpu is None:
                sockets = _fact(selected, 'numSockets')
                cores = _fact(selected, 'numCoresPerSocket')
                vcpu = sockets * cores if _positive(sockets) and _positive(cores) else None
            for name, value in (('VCPU', vcpu),
                                ('MEMORY', _fact(selected, 'memorySizeBytes')),
                                ('DISK', _fact(selected, 'diskCapacityBytes'))):
                if not _positive(value):
                    add('UNKNOWN', 'SOURCE_' + name + '_UNKNOWN',
                        'The source VM lacks a usable ' + name.lower() + ' observation.',
                        'Collect and verify this VM resource requirement.')
            memory = _fact(selected, 'memorySizeBytes')
            disk = _fact(selected, 'diskCapacityBytes')
            for name, expected, code in (('guestProfile', guest, 'GUEST'),
                                         ('networkMode', network, 'NETWORK'),
                                         ('dataMode', data, 'DATA')):
                observed = _fact(selected, name)
                if not isinstance(observed, str) or not observed:
                    add('UNKNOWN', 'SOURCE_' + code + '_UNKNOWN',
                        'The source ' + name + ' is not observed.',
                        'Enrich the source profile with reviewed native facts.')
                elif observed != expected:
                    add('BLOCKER', 'SOURCE_' + code + '_MISMATCH',
                        'The selected route differs from the observed source ' + name + '.',
                        'Select a route for the observed profile or reconcile the observation.')

        target = None
        if option.inventory is None:
            add('UNKNOWN', 'DESTINATION_SNAPSHOT_MISSING',
                'No destination observation is available.',
                'Run an authorized read-only destination discovery campaign.')
        elif not _fresh(option.inventory, as_of, max_age):
            add('UNKNOWN', 'DESTINATION_SNAPSHOT_STALE',
                'The destination observation is not current.',
                'Collect a new exact-scope destination generation.')
        else:
            if option.inventory.completeness != 'COMPLETE':
                add('UNKNOWN', 'DESTINATION_SNAPSHOT_INCOMPLETE',
                    'The destination inventory has collection gaps.',
                    'Resolve missing privileges and collect a complete generation.')
            if option.capacity_identity is None:
                add('UNKNOWN', 'CAPACITY_POOL_UNSELECTED',
                    'No exact destination capacity pool was selected.',
                    'Select an observed native pool, quota, cluster or datastore.')
            else:
                target = next((obj for obj in option.inventory.objects
                               if obj.identity == option.capacity_identity), None)
                if target is None:
                    add('UNKNOWN', 'CAPACITY_POOL_NOT_OBSERVED',
                        'The selected native capacity scope is not observed.',
                        'Reconcile the exact native pool identity and refresh discovery.')

        if target is not None:
            for name, requested, code in (
                ('availableVcpu', vcpu, 'VCPU'),
                ('availableMemoryBytes', memory, 'MEMORY'),
                ('availableStorageBytes', disk, 'STORAGE'),
            ):
                available = _fact(target, name)
                if not _available(available):
                    add('UNKNOWN', 'CAPACITY_' + code + '_UNKNOWN',
                        'The selected pool lacks verified available ' + name + '.',
                        'Refresh capacity and reservation observations for this pool.')
                elif _positive(requested) and available < requested:
                    add('BLOCKER', 'CAPACITY_' + code + '_INSUFFICIENT',
                        'The selected pool cannot fit the observed source requirement.',
                        'Select another pool or add and verify available capacity.')
            for name, expected, code in (
                ('supportedGuestProfiles', guest, 'GUEST_UNSUPPORTED'),
                ('supportedNetworkModes', network, 'NETWORK_MODE_UNSUPPORTED'),
                ('supportedDataModes', data, 'DATA_MODE_UNSUPPORTED'),
            ):
                values = _fact(target, name)
                if (not isinstance(values, list)
                        or any(not isinstance(value, str) or not value for value in values)):
                    add('UNKNOWN', name.upper() + '_UNKNOWN',
                        'Native compatibility for ' + name + ' is not observed.',
                        'Verify this installed destination profile and its native support.')
                elif expected not in values:
                    add('BLOCKER', code,
                        'The destination does not support the selected profile or mode.',
                        'Choose a supported route or an independently qualified destination.')

        for severity, code, reason, remediation in check_compatibility(selected, target, method):
            add(severity, code, reason, remediation)

        findings = {control: [finding for finding in option.findings
                              if finding.control == control]
                    for control in _CONTROLS}
        for control in _CONTROLS:
            artifacts = findings[control]
            if len(artifacts) != 1:
                add('UNKNOWN', control + '_EVIDENCE_' +
                    ('MISSING' if not artifacts else 'DUPLICATE'),
                    'There is no single current ' + control.lower() + ' review.',
                    'Obtain one independently reviewed finding for this exact route and snapshots.')
                continue
            finding = artifacts[0]
            if (key is None or finding.route != key
                    or source_inventory is None or option.inventory is None
                    or finding.source_snapshot_digest != source_inventory.digest
                    or finding.destination_snapshot_digest != option.inventory.digest):
                add('UNKNOWN', control + '_SCOPE_MISMATCH',
                    'The review refers to another route or observation generation.',
                    'Review this exact route against the selected source and target generations.')
            elif (finding.observed_at > as_of or finding.expires_at <= as_of
                  or finding.observed_at < max(source_inventory.captured_at,
                                               option.inventory.captured_at)):
                add('UNKNOWN', control + '_EVIDENCE_EXPIRED',
                    'The review is not current for these observation generations.',
                    'Renew and verify this exact-scope review after both observations.')
            elif finding.outcome == 'FAIL':
                add('BLOCKER', control + '_FAILED',
                    'The independent review rejected this destination control.',
                    'Resolve the finding and obtain a new reviewed artifact.')
        artifacts = [item for items in findings.values() for item in items]
        if (len({item.evidence_digest for item in artifacts}) != len(artifacts)
                or len({item.evidence_id for item in artifacts}) != len(artifacts)):
            add('UNKNOWN', 'CONTROL_EVIDENCE_NOT_INDEPENDENT',
                'The control reviews reuse a single evidence identity.',
                'Obtain separately reviewed policy, security and recovery evidence.')
        route_evidence = ({route.source_evidence_digest,
                           route.target_evidence_digest} - {None}) if route else set()
        if any(item.evidence_digest in route_evidence for item in artifacts):
            add('UNKNOWN', 'CONTROL_ROUTE_EVIDENCE_REUSED',
                'A control review reuses native route qualification evidence.',
                'Obtain an independent policy, security or recovery review.')

        estimate = _estimate(selected, target, method)
        severity = {issue.severity for issue in issues}
        status = ('BLOCKED' if 'BLOCKER' in severity else
                  'UNKNOWN' if 'UNKNOWN' in severity else
                  'CONDITIONAL' if 'CONDITION' in severity else 'ELIGIBLE')
        return DestinationAssessment(
            source, option.installation, workload, method, guest, network, data,
            source_inventory.digest if source_inventory else None,
            option.inventory.digest if option.inventory else None,
            maturity, status, tuple(issues), estimate)


def _fresh(inventory: DiscoveryResult, as_of: datetime, max_age: timedelta) -> bool:
    return as_of - max_age <= inventory.captured_at <= as_of


def _estimate(source: DiscoveryObject | None, destination: DiscoveryObject | None,
              method: str) -> TransferEstimate:
    if source is None or method not in {'COLD_VM_CONVERSION', 'WARM_VM_TRANSFER'}:
        return TransferEstimate(None, None, 'NONE', ())
    size = _fact(source, 'measuredTransferBytes')
    if not _positive(size):
        return TransferEstimate(None, None, 'NONE', ())
    speed = _fact(destination, 'measuredTransferBytesPerSecond') if destination else None
    if not _positive(speed):
        return TransferEstimate(size, None, 'LOW', ('MEASURED_TRANSFER_BYTES',))
    return TransferEstimate(size, (size + speed - 1) // speed, 'LOW',
                            ('MEASURED_TRANSFER_BYTES', 'MEASURED_THROUGHPUT',
                             'COPY_PHASE_ONLY'))
