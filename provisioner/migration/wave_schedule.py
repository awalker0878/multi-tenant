"""Bounded tenant-local dependency scheduling over the B09 admission owner.

A saved wave is immutable planning data, never an approval or native grant.
One separately enrolled native-domain budget serializes all its wave admissions.
Jobs and their existing outbox are committed with the member's resource claims.
Uncertain, held and expired work retains every charge until the independent
operating/reconciliation owner accepts its exact release evidence.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import json
import re
from typing import Callable

from provisioner.controlplane.authority.model import (
    AuthorizedPlan, PlanScope, PortfolioScope, VerifiedPrincipal)
from provisioner.controlplane.authority.service import (
    AuthorityDenied, EXECUTION_OPERATOR, WORKLOAD_EDITOR, require_scoped_role,
    require_workload_role)
from provisioner.controlplane.jobs.repository import (
    AdmissionRefused, Job, JobRepository, _digest, _ensure_plan, _ensure_workload,
    _json, _tenant)
from provisioner.controlplane.persistence import TenantContext
from provisioner.controlplane.workflow.execution_selection import FileExecutionSelectionStore
from provisioner.domain.enterprise_records import validate_record
from provisioner.execution.neutron_observe import strict_loads
from provisioner.qualification.action_gate import SelectedQualificationGate, bundle_digest
from provisioner.qualification.directed_mobility import PLAN_METHODS, WAVE_ASSERTIONS
from provisioner.qualification.mobility import (
    MobilityCampaign, assess, from_document as campaign_from_document)

from .resources import TransferLimits

_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$')
_SHA = re.compile(r'^[0-9a-f]{64}$')
_SCOPE_FIELDS = frozenset({'organizationId', 'tenantId', 'locationId',
    'securityDomainId', 'endpointId', 'nativeScopeId', 'platformFamily'})
_PLATFORM = {'vmware': 'vmware-nsx', 'nutanix': 'nutanix', 'openstack': 'openstack'}
_ADMISSION_ACTIONS = {
    'APPLICATION_REBUILD_RESTORE': ('DISCOVER_READ', 'VM_CREATE', 'DISK_ATTACH',
        'NETWORK_ATTACH', 'GUEST_CONFIG', 'POLICY_APPLY', 'RESTORE_DATA',
        'SOURCE_FENCE', 'DESTINATION_ACTIVATE', 'DNS_CHANGE'),
}
MAX_MEMBERS = 64
MAX_DOMAIN_MEMBERS = 1024
MAX_DOCUMENT_BYTES = 2 * 1024**2
FORMAT = 'hosting-migration-wave/1'
DOMAIN_FORMAT = 'hosting-migration-wave-domain/1'


class WaveHeld(AdmissionRefused):
    """Current scheduling scope, evidence, budgets or window cannot be proved."""


def _require(condition, message):
    if not condition:
        raise WaveHeld(message)


def _identifier(value):
    _require(type(value) is str and _ID.fullmatch(value), 'Exact bounded identity required')
    return value


def _sha(value):
    _require(type(value) is str and _SHA.fullmatch(value), 'Exact content digest required')
    return value


def _instant(value):
    _require(isinstance(value, datetime) and value.tzinfo is not None
             and value.utcoffset() == timedelta(0), 'An exact UTC scheduling instant is required')
    return value


def _parse_instant(value):
    _require(type(value) is str and len(value) <= 40, 'A bounded UTC instant is required')
    try:
        return _instant(datetime.fromisoformat(value.replace('Z', '+00:00')))
    except (ValueError, TypeError):
        raise WaveHeld('A valid UTC scheduling instant is required') from None


def _integer(value, low=1, high=10**12):
    _require(type(value) is int and low <= value <= high, 'Bounded exact integer required')
    return value


def _scope(value):
    _require(type(value) is dict and value.keys() == _SCOPE_FIELDS,
             'Every enrolled scheduling scope needs all canonical native identities')
    result = PlanScope.from_record(value)
    _require(result.platform_family in _PLATFORM,
             'The scheduling domain has an undeclared native family')
    return result


def _scope_record(value):
    return dict(organizationId=value.organization_id, tenantId=value.tenant_id,
        locationId=value.site_id, securityDomainId=value.security_domain_id,
        endpointId=value.endpoint_id, nativeScopeId=value.native_scope_id,
        platformFamily=value.platform_family)


def native_domain_key(scope: PlanScope) -> str:
    """One physical endpoint/scope cannot enroll twice under other WSD labels."""
    return _digest({'platformFamily': scope.platform_family,
        'endpointId': scope.endpoint_id, 'nativeScopeId': scope.native_scope_id})


@dataclass(frozen=True)
class WaveBudget:
    concurrent_jobs: int
    exposed_workloads: int
    downtime_seconds: int
    risk_units: int
    download_kib_per_second: int
    block_iops: int
    stage_bytes: int

    def __post_init__(self):
        for name in ('concurrent_jobs', 'exposed_workloads'):
            _integer(getattr(self, name), high=MAX_DOMAIN_MEMBERS)
        _integer(self.downtime_seconds, low=0, high=31 * 86400 * MAX_DOMAIN_MEMBERS)
        _integer(self.risk_units, high=10**9)
        _integer(self.download_kib_per_second, high=1024 * 1024 * MAX_DOMAIN_MEMBERS)
        _integer(self.block_iops, high=1000000 * MAX_DOMAIN_MEMBERS)
        _integer(self.stage_bytes, high=2**60)


@dataclass(frozen=True)
class WaveDomain:
    organization_id: str
    tenant_id: str
    domain_id: str
    scopes: tuple[tuple[PlanScope, str], ...]
    budget: WaveBudget
    shared_risk_limits: tuple[tuple[str, int], ...]
    native_budget_evidence_digest: str
    observed_at: datetime
    expires_at: datetime

    def __post_init__(self):
        for value in (self.organization_id, self.tenant_id, self.domain_id):
            _identifier(value)
        _require(isinstance(self.budget, WaveBudget) and type(self.scopes) is tuple
                 and 2 <= len(self.scopes) <= 64, 'A bounded enrolled native domain is required')
        physical, declared, groups = {}, set(), set()
        for scope, group in self.scopes:
            _require(isinstance(scope, PlanScope) and (scope.organization_id, scope.tenant_id) ==
                     (self.organization_id, self.tenant_id), 'Native domain cannot cross tenants')
            key = native_domain_key(scope)
            group = _identifier(group)
            _require(scope not in declared and (key not in physical or physical[key] == group),
                     'A native scope cannot enroll twice or split its shared-risk owner')
            declared.add(scope)
            physical[key] = group
            groups.add(group)
        _require(type(self.shared_risk_limits) is tuple and
                 {key for key, _ in self.shared_risk_limits} == groups and
                 len(self.shared_risk_limits) == len(groups), 'Every native risk group needs a separate cap')
        for _, cap in self.shared_risk_limits:
            _integer(cap, high=self.budget.risk_units)
        _sha(self.native_budget_evidence_digest)
        _instant(self.observed_at)
        _instant(self.expires_at)
        _require(self.observed_at < self.expires_at <= self.observed_at + timedelta(days=31),
                 'Native scheduling budget must have a finite reviewed lifetime')

    def to_record(self):
        return dict(format=DOMAIN_FORMAT, organizationId=self.organization_id,
            tenantId=self.tenant_id, domainId=self.domain_id,
            scopes=[{'scope': _scope_record(scope), 'sharedRiskGroup': group}
                    for scope, group in sorted(self.scopes,
                        key=lambda row: (native_domain_key(row[0]), _canonical(_scope_record(row[0]))))],
            budget=asdict(self.budget), sharedRiskLimits=dict(sorted(self.shared_risk_limits)),
            nativeBudgetEvidenceDigest=self.native_budget_evidence_digest,
            observedAt=self.observed_at.isoformat(), expiresAt=self.expires_at.isoformat())

    @property
    def digest(self):
        return _digest(self.to_record())

    @classmethod
    def from_record(cls, value):
        _require(type(value) is dict and value.keys() == {'format', 'organizationId',
            'tenantId', 'domainId', 'scopes', 'budget', 'sharedRiskLimits',
            'nativeBudgetEvidenceDigest', 'observedAt', 'expiresAt'} and
            value['format'] == DOMAIN_FORMAT, 'Exact enrolled scheduling budget record required')
        _require(type(value['scopes']) is list and type(value['budget']) is dict and
                 value['budget'].keys() == WaveBudget.__dataclass_fields__.keys() and
                 type(value['sharedRiskLimits']) is dict, 'Malformed scheduling budget')
        scopes = []
        for row in value['scopes']:
            _require(type(row) is dict and row.keys() == {'scope', 'sharedRiskGroup'},
                     'Malformed native-domain scope declaration')
            scopes.append((_scope(row['scope']), row['sharedRiskGroup']))
        return cls(value['organizationId'], value['tenantId'], value['domainId'],
            tuple(scopes), WaveBudget(**value['budget']), tuple(value['sharedRiskLimits'].items()),
            value['nativeBudgetEvidenceDigest'], _parse_instant(value['observedAt']),
            _parse_instant(value['expiresAt']))

    def groups_for(self, member):
        declared = dict(self.scopes)
        _require(member.source in declared and member.destination in declared,
                 'Both exact native scopes must belong to one commissioned budget owner')
        return tuple(sorted({declared[member.source], declared[member.destination]}))


@dataclass(frozen=True)
class WaveMember:
    member_id: str
    plan_json: str
    campaign: MobilityCampaign
    depends_on: tuple[str, ...]
    window_start: datetime
    window_end: datetime
    runtime_seconds: int
    transfer_limits: TransferLimits
    downtime_seconds: int
    risk_units: int

    def __post_init__(self):
        _identifier(self.member_id)
        _require(type(self.plan_json) is str and len(self.plan_json.encode()) <= 256 * 1024,
                 'A bounded immutable canonical plan is required')
        record = strict_loads(self.plan_json.encode())
        _require(_canonical(record) == self.plan_json and record.get('kind') == 'MigrationPlan'
                 and not validate_record(record), 'Wave member must retain an exact valid canonical plan')
        _require(isinstance(self.campaign, MobilityCampaign) and
                 (self.campaign.method, self.campaign.guest_profile,
                  self.campaign.source.platform, self.campaign.destination.platform) ==
                 (PLAN_METHODS[record['spec']['route']['method']], record['spec']['route']['guestProfile'],
                  _PLATFORM[self.source.platform_family], _PLATFORM[self.destination.platform_family]),
                 'Every member needs separately selected exact direction/method/guest qualification')
        _require(type(self.depends_on) is tuple and len(self.depends_on) <= MAX_MEMBERS
                 and len(set(self.depends_on)) == len(self.depends_on), 'Distinct bounded dependency identities required')
        for value in self.depends_on:
            _identifier(value)
            _require(value != self.member_id, 'A wave member cannot depend on itself')
        _instant(self.window_start)
        _instant(self.window_end)
        _integer(self.runtime_seconds, high=31 * 86400)
        _require(self.window_start < self.window_end <= self.window_start + timedelta(days=31)
                 and self.window_start + timedelta(seconds=self.runtime_seconds) <= self.window_end,
                 'A finite window must cover the full conservative runtime bound')
        _require(isinstance(self.transfer_limits, TransferLimits), 'Existing transfer-resource limits required')
        _integer(self.downtime_seconds, low=0, high=31 * 86400)
        _require(self.downtime_seconds >= record['spec']['maxDowntimeSeconds'],
                 'The wave must reserve the full approved maximum downtime')
        _integer(self.risk_units, high=10**9)

    @classmethod
    def from_plan(cls, member_id, plan, campaign, *, depends_on=(), window_start,
                  window_end, runtime_seconds, transfer_limits, risk_units,
                  downtime_seconds=None):
        return cls(member_id, _canonical(plan), campaign, tuple(depends_on), window_start,
                   window_end, runtime_seconds, transfer_limits,
                   plan['spec']['maxDowntimeSeconds'] if downtime_seconds is None else downtime_seconds,
                   risk_units)

    @property
    def plan(self):
        return strict_loads(self.plan_json.encode())

    @property
    def plan_id(self):
        return self.plan['metadata']['planId']

    @property
    def plan_revision(self):
        return self.plan['metadata']['revision']

    @property
    def plan_digest(self):
        return self.plan['metadata']['planDigest']

    @property
    def source(self):
        return PlanScope.from_record(self.plan['spec']['source'])

    @property
    def destination(self):
        return PlanScope.from_record(self.plan['spec']['destination'])

    @property
    def cohort(self):
        # Fairness is within current verified tenant/WSD scopes. A caller cannot
        # manufacture another tenant or an arbitrary label to gain more turns.
        return self.source.security_domain_id

    @property
    def demand(self):
        return WaveBudget(1, 1, self.downtime_seconds, self.risk_units,
            self.transfer_limits.download_kib_per_second, self.transfer_limits.block_iops,
            self.transfer_limits.stage_bytes)

    def to_record(self):
        return dict(memberId=self.member_id, plan=self.plan, campaign=asdict(self.campaign),
            dependsOn=sorted(self.depends_on), windowStart=self.window_start.isoformat(),
            windowEnd=self.window_end.isoformat(), runtimeSeconds=self.runtime_seconds,
            transferLimits=self.transfer_limits.to_dict(), downtimeSeconds=self.downtime_seconds,
            riskUnits=self.risk_units)

    @classmethod
    def from_record(cls, value):
        _require(type(value) is dict and value.keys() == {'memberId', 'plan', 'campaign',
            'dependsOn', 'windowStart', 'windowEnd', 'runtimeSeconds', 'transferLimits',
            'downtimeSeconds', 'riskUnits'} and type(value['dependsOn']) is list and
            type(value['transferLimits']) is dict and value['transferLimits'].keys() ==
            TransferLimits.__dataclass_fields__.keys(), 'Exact immutable wave member required')
        return cls.from_plan(value['memberId'], value['plan'], campaign_from_document(value['campaign']),
            depends_on=tuple(value['dependsOn']), window_start=_parse_instant(value['windowStart']),
            window_end=_parse_instant(value['windowEnd']), runtime_seconds=value['runtimeSeconds'],
            transfer_limits=TransferLimits(**value['transferLimits']),
            downtime_seconds=value['downtimeSeconds'], risk_units=value['riskUnits'])


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)


@dataclass(frozen=True)
class WaveDefinition:
    organization_id: str
    tenant_id: str
    domain_id: str
    domain_digest: str
    members: tuple[WaveMember, ...]

    def __post_init__(self):
        for value in (self.organization_id, self.tenant_id, self.domain_id):
            _identifier(value)
        _sha(self.domain_digest)
        _require(type(self.members) is tuple and 1 <= len(self.members) <= MAX_MEMBERS
                 and all(isinstance(member, WaveMember) for member in self.members),
                 'One to sixty-four exact wave members required')
        names, plans, workloads = set(), set(), set()
        for member in self.members:
            _require((member.source.organization_id, member.source.tenant_id) ==
                     (self.organization_id, self.tenant_id) ==
                     (member.destination.organization_id, member.destination.tenant_id),
                     'A saved wave cannot cross tenant authority boundaries')
            workload = member.plan['spec']['workloadId']
            _require(member.member_id not in names and member.plan_id not in plans
                     and workload not in workloads, 'Wave members cannot repeat identities, plans or workloads')
            names.add(member.member_id)
            plans.add(member.plan_id)
            workloads.add(workload)
        _require(all(set(member.depends_on) <= names for member in self.members),
                 'Every wave dependency must name a retained member')
        visited = set()
        while len(visited) < len(names):
            ready = {member.member_id for member in self.members
                     if set(member.depends_on) <= visited} - visited
            _require(bool(ready), 'A dependency cycle cannot be scheduled')
            visited.update(ready)
        _require(len(_canonical(self.to_record()).encode()) <= MAX_DOCUMENT_BYTES,
                 'Saved wave exceeds its immutable document bound')

    def to_record(self):
        return dict(format=FORMAT, organizationId=self.organization_id, tenantId=self.tenant_id,
            domainId=self.domain_id, domainDigest=self.domain_digest,
            members=[member.to_record() for member in sorted(self.members, key=lambda row: row.member_id)])

    @classmethod
    def from_record(cls, value):
        _require(type(value) is dict and value.keys() == {'format', 'organizationId', 'tenantId',
            'domainId', 'domainDigest', 'members'} and value['format'] == FORMAT
            and type(value['members']) is list, 'Exact versioned wave definition required')
        return cls(value['organizationId'], value['tenantId'], value['domainId'],
            value['domainDigest'], tuple(WaveMember.from_record(row) for row in value['members']))

    @property
    def digest(self):
        return _digest(self.to_record())

    @property
    def reference(self):
        return 'wave-' + self.digest

    def run_sheet(self):
        return {'format': 'hosting-migration-wave-run-sheet/1', 'scheduleRef': self.reference,
            'scheduleDigest': self.digest, 'domainDigest': self.domain_digest,
            'variantRef': 'controlled-migration-wave:' + self.digest,
            'members': [{'memberId': member.member_id, 'planDigest': member.plan_digest,
                'qualificationCampaignVariantRef': member.campaign.variant_ref} for member in self.members],
            'requiredNativeAssertions': dict(WAVE_ASSERTIONS),
            'nativeCampaignRun': False, 'qualificationIssued': False, 'mutationAuthorized': False}


@dataclass(frozen=True)
class MemberState:
    schedule_digest: str
    member: WaveMember
    status: str
    resource_keys: tuple[str, ...]
    risk_groups: tuple[str, ...]
    created_at: datetime
    job_id: str | None = None

    @property
    def key(self):
        return self.schedule_digest, self.member.member_id


@dataclass(frozen=True)
class WaveAdmission:
    status: str
    schedule_ref: str | None
    member_id: str | None
    job_id: str | None
    reason: str
    active_charges: dict
    mutation_authorized: bool = False


def active_charges(states):
    totals = {key: 0 for key in WaveBudget.__dataclass_fields__}
    groups, resources = {}, set()
    for state in states:
        if state.job_id is None or state.status == 'SUCCEEDED':
            continue
        for key, value in asdict(state.member.demand).items():
            totals[key] += value
        for group in state.risk_groups:
            groups[group] = groups.get(group, 0) + state.member.risk_units
        resources.update(state.resource_keys)
    return totals, groups, resources


def candidate_decisions(states, domain: WaveDomain, now: datetime, last_cohort: str | None,
                        *, permitted_scopes: frozenset[PlanScope] | None = None):
    """Deterministic round-robin within verified scopes, then oldest member first.

    Returns all candidate/hold reasons for operator inspection. Pending admission
    fairness is domain-wide, so splitting a WSD into many waves gains no turns.
    A blocked cohort does not prevent another ready cohort from making progress.
    """
    _instant(now)
    _require(len(states) <= MAX_DOMAIN_MEMBERS, 'Native domain scheduling inventory is too large')
    for state in states:
        _require(domain.groups_for(state.member) == state.risk_groups and bool(state.resource_keys),
                 'Every member requires a complete inventory in its known native budget owner')
    totals, groups, resources = active_charges(states)
    by_key, ready, reasons = {state.key: state for state in states}, [], {}
    _require(len(by_key) == len(states), 'Scheduling projections contain duplicate members')
    _require(domain.observed_at <= now < domain.expires_at, 'Native scheduling budget is not current')
    for state in states:
        if state.status != 'PENDING':
            continue
        member = state.member
        if permitted_scopes is not None and (member.source not in permitted_scopes or
                                            member.destination not in permitted_scopes):
            reasons[state.key] = 'CURRENT_SCOPE_AUTHORITY_REQUIRED'
        elif now + timedelta(seconds=member.runtime_seconds) > member.window_end:
            reasons[state.key] = 'WINDOW_EXPIRED'
        elif now < member.window_start:
            reasons[state.key] = 'WAITING_WINDOW'
        elif any(by_key.get((state.schedule_digest, dependency)) is None or
                 by_key[state.schedule_digest, dependency].status != 'SUCCEEDED'
                 for dependency in member.depends_on):
            reasons[state.key] = 'DEPENDENCY_NOT_ACCEPTED'
        elif set(state.resource_keys) & resources:
            reasons[state.key] = 'NATIVE_RESOURCE_OVERLAP'
        elif any(totals[key] + value > getattr(domain.budget, key)
                 for key, value in asdict(member.demand).items()):
            reasons[state.key] = 'DOMAIN_BUDGET_UNAVAILABLE'
        elif any(groups.get(group, 0) + member.risk_units > dict(domain.shared_risk_limits)[group]
                 for group in state.risk_groups):
            reasons[state.key] = 'SHARED_RISK_BUDGET_UNAVAILABLE'
        else:
            ready.append(state)
            reasons[state.key] = 'READY_FOR_CURRENT_AUTHORITY'
    cohorts = sorted({state.member.cohort for state in ready})
    # Rotate after the last admitted scope even if it currently has no ready work.
    cohorts = [key for key in cohorts if last_cohort is not None and key > last_cohort] + [
        key for key in cohorts if last_cohort is None or key <= last_cohort]
    rank = {key: index for index, key in enumerate(cohorts)}
    ready.sort(key=lambda state: (rank[state.member.cohort], state.created_at,
                                 state.schedule_digest, state.member.member_id))
    return ready, reasons, totals


def _resource_keys(member, workload):
    """Observe the complete selected source bindings; no caller overlap labels."""
    plan = member.plan
    _require(not validate_record(plan, workload=workload),
             'Every member still needs the exact canonical source workload')
    bindings = [row['sourceBinding'] for row in plan['spec']['machineMappings']]
    selected = set(plan['spec']['selectedMachineIds'])
    for machine in workload['spec']['machines']:
        if machine['machineId'] not in selected:
            continue
        for item in (*machine['disks'], *machine['nics']):
            bindings.extend(row['binding'] for row in item['bindings'] if row['role'] == 'SOURCE')
    datasets = set(plan['spec']['selectedDatasetIds'])
    for item in workload['spec']['datasets']:
        if item['datasetId'] in datasets:
            bindings.extend(item['sourceBindings'])
    _require(bool(bindings), 'Missing native resource inventory cannot mean zero retained resources')
    return tuple(sorted({_digest(binding) for binding in bindings}))


class SelectedWaveQualification:
    """Current per-member evidence through the existing five-index owners."""
    def __init__(self, gate: SelectedQualificationGate, selections: FileExecutionSelectionStore,
                 migration_selections):
        from .activities import FileMigrationSelectionStore
        _require(isinstance(gate, SelectedQualificationGate)
                 and isinstance(selections, FileExecutionSelectionStore)
                 and isinstance(migration_selections, FileMigrationSelectionStore),
                 'Current qualification, execution and actual dataset-selection owners are required')
        self.gate, self.selections, self.migration_selections = gate, selections, migration_selections

    def _selected(self, member):
        plan = member.plan
        execution = plan['spec'].get('execution')
        _require(type(execution) is dict and execution.keys() == {'format', 'driver', 'artifactDigest'}
                 and execution['format'] == 'hosting-execution-selection/1',
                 'A wave cannot schedule a gate-only or unimplemented plan')
        selection = self.selections.load_verified(execution['artifactDigest'])
        _require((selection['source'], selection['destination'], selection['workloadId'],
                  selection['workloadRevision'], selection['guestProfile'], selection['sourceCommit'],
                  selection['driver'], selection['qualificationDigest']) ==
                 (plan['spec']['source'], plan['spec']['destination'], plan['spec']['workloadId'],
                  plan['spec']['workloadRevision'], member.campaign.guest_profile,
                  member.campaign.code_revision, execution['driver'],
                  plan['spec']['route']['qualificationDigest']),
                 'Exact execution code, workload, method and native scopes changed')
        return selection

    def transfer_resource_keys(self, member):
        """Bind scheduler charges to the installed kernel-limited data owners.

        Conservative sum covers every selected child, including staged data
        retained after a child returns. The scheduler cannot lower immutable
        worker bandwidth/IOPS/staging ceilings or reuse a commissioned cgroup.
        """
        selection = self._selected(member)
        descriptor = self.migration_selections.datasets(selection['datasetSelectionDigest']).to_dict()
        plan = member.plan
        _require((descriptor['source_scope'], descriptor['destination_scope'], descriptor['guest_profile']) ==
                 (plan['spec']['source'], plan['spec']['destination'], member.campaign.guest_profile)
                 and {(row['dataset_id'], row['target_ref'], row['consistency_group_id'])
                      for row in descriptor['datasets']} ==
                 {(row['datasetId'], row['targetRef'], row['consistencyGroupId'])
                      for row in plan['spec']['datasetMappings']},
                 'Scheduling resources must cover every exact approved application dataset')
        totals = {key: 0 for key in TransferLimits.__dataclass_fields__}
        keys = set()
        for row in descriptor['datasets']:
            resources = row['resources']
            for key, amount in resources['limits'].items():
                totals[key] += amount
            for kind, identity in (('stage-volume', resources['stage_parent']),
                    ('staging-block-device', resources['block_device']),
                    ('transfer-cgroup', resources['cgroup']), ('restore-root', row['target_root'])):
                # Current Linux controls are local to one commissioned worker
                # host. Do not partition its physical resources by project or
                # WSD: separate native-scope labels must not duplicate a charge.
                # Identical local names on other hosts conservatively conflict
                # until a separately authenticated multi-host binding exists.
                keys.add(_digest({'kind': kind, 'identity': identity}))
        _require(asdict(member.transfer_limits) == totals,
                 'Wave transfer demand differs from the approved workers hard resource ceilings')
        return tuple(sorted(keys))

    def require_member(self, cursor, context, member: WaveMember, now):
        selection = self._selected(member)
        self.transfer_resource_keys(member)
        bundle = self.gate.current_bundle()
        _require(bundle_digest(bundle) == selection['qualificationDigest'],
                 'Current per-member native qualification bundle changed')
        for side in ('source', 'destination'):
            endpoint = getattr(member.campaign, side)
            matching = [row for row in bundle['qualification']['records']
                if row['platform'] == endpoint.platform and
                row['product_tuple_id'] == endpoint.product_tuple_id]
            _require(len(matching) == 1 and matching[0]['product_tuple'] == selection[side + 'Tuple'],
                     'Per-member campaign and installed action select different exact product tuples')
        result = assess(member.campaign, qualification_index=bundle['qualification'],
            provenance_index=bundle['provenance'], campaign_index=bundle['campaign'],
            selection_index=bundle['targetSelection'], as_of=now, root=self.gate.root)
        _require(result['status'] == 'CURRENT_NATIVE_EVIDENCE_SELECTED',
                 'No current exact direction/method/guest/tuple/code qualification for this member')
        actions = _ADMISSION_ACTIONS.get(member.campaign.method)
        _require(actions is not None, 'No installed wave method owner exists')
        # This value carries the tenant only. The qualification gate cannot issue
        # a job/grant; current approvals are checked by B09 later in this transaction.
        for action in actions:
            self.gate.require_action(cursor, context, selection, action)


class WaveScheduler:
    """Trusted service owner; no API-supplied SQL, permits, paths or callbacks.

    ``identity`` is the independently verified current IAM owner. The planner
    needs WORKLOAD_EDITOR in each exact WSD, while admission independently needs
    current native EXECUTION_OPERATOR scopes and the member's B07/B09 decision.
    Native domain/release enrollment uses other credentials and is never done here.
    """
    def __init__(self, connect: Callable, jobs: JobRepository, identity,
                 qualification: SelectedWaveQualification):
        _require(callable(connect) and isinstance(jobs, JobRepository)
                 and callable(getattr(identity, 'authenticate', None))
                 and isinstance(qualification, SelectedWaveQualification),
                 'Existing admission, IAM and selected qualification owners are required')
        self.connect, self.jobs, self.identity, self.qualification = connect, jobs, identity, qualification

    def _principal(self, credential, context, now):
        principal = self.identity.authenticate(credential)
        _require(isinstance(principal, VerifiedPrincipal) and principal.kind == 'HUMAN'
                 and (principal.organization_id, principal.tenant_id) ==
                 (context.organization_id, context.tenant_id)
                 and principal.issued_at <= now < principal.expires_at,
                 'Wave operations require current independently verified tenant identity')
        return principal

    def _domain(self, cursor, context, domain_id):
        _identifier(domain_id)
        cursor.execute('SELECT document_digest,document_json FROM '
            'hosting_controlplane.lock_migration_wave_domain(%s,%s,%s)',
            (context.organization_id, context.tenant_id, domain_id))
        row = cursor.fetchone()
        _require(row is not None, 'No current independently enrolled native-domain budget')
        domain = WaveDomain.from_record(strict_loads(row[1].encode()))
        _require(domain.digest == row[0] and (domain.organization_id, domain.tenant_id, domain.domain_id) ==
                 (context.organization_id, context.tenant_id, domain_id), 'Native domain custody changed')
        return domain

    def _current_member(self, cursor, context, member):
        cursor.execute('SELECT revision,record_digest,record_json FROM hosting_controlplane.enterprise_records '
            "WHERE organization_id=%s AND tenant_id=%s AND record_kind='MigrationPlan' AND record_id=%s FOR SHARE",
            (context.organization_id, context.tenant_id, member.plan_id))
        selected = _ensure_plan(cursor.fetchone(), context, member)
        _require(_canonical(selected) == member.plan_json, 'The saved exact wave plan changed')
        _ensure_workload(cursor, context, selected)
        cursor.execute('SELECT record_json FROM hosting_controlplane.enterprise_records '
            "WHERE organization_id=%s AND tenant_id=%s AND record_kind='Workload' AND record_id=%s FOR SHARE",
            (context.organization_id, context.tenant_id, selected['spec']['workloadId']))
        row = cursor.fetchone()
        _require(row is not None, 'Current source workload inventory is unavailable')
        return _resource_keys(member, _json(row[0]))

    def _event(self, cursor, context, domain_id, schedule_digest, member_id, event, reason, detail):
        cursor.execute('INSERT INTO hosting_controlplane.migration_wave_events '
            '(organization_id,tenant_id,domain_id,sequence,schedule_digest,member_id,event,reason,detail) '
            'SELECT %s,%s,%s,COALESCE(MAX(sequence),0)+1,%s,%s,%s,%s,%s::jsonb '
            'FROM hosting_controlplane.migration_wave_events '
            'WHERE organization_id=%s AND tenant_id=%s AND domain_id=%s',
            (context.organization_id, context.tenant_id, domain_id, schedule_digest,
             member_id, event, reason, _canonical(detail), context.organization_id, context.tenant_id, domain_id))

    def register(self, credential, context: TenantContext, definition: WaveDefinition):
        _require(isinstance(context, TenantContext) and isinstance(definition, WaveDefinition)
                 and (definition.organization_id, definition.tenant_id) ==
                 (context.organization_id, context.tenant_id), 'Wave and verified tenant scope differ')
        with self.connect() as connection, connection.cursor() as cursor:
            _tenant(cursor, context)
            domain = self._domain(cursor, context, definition.domain_id)
            cursor.execute('SELECT clock_timestamp()')
            now = cursor.fetchone()[0]
            _require(domain.observed_at <= now < domain.expires_at and domain.digest == definition.domain_digest,
                     'The independently enrolled domain budget is expired or changed')
            principal = self._principal(credential, context, now)
            resources = {}
            for member in definition.members:
                domain.groups_for(member)
                for scope in (member.source, member.destination):
                    require_workload_role(principal, WORKLOAD_EDITOR,
                        PortfolioScope(scope.organization_id, scope.tenant_id, scope.security_domain_id), now)
                resources[member.member_id] = self._current_member(cursor, context, member)
                resources[member.member_id] = tuple(sorted(set(resources[member.member_id]) |
                    set(self.qualification.transfer_resource_keys(member))))
            cursor.execute('INSERT INTO hosting_controlplane.migration_waves '
                '(organization_id,tenant_id,schedule_digest,domain_id,domain_digest,definition_json,created_by) '
                'VALUES (%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING RETURNING schedule_digest',
                (context.organization_id, context.tenant_id, definition.digest, definition.domain_id,
                 definition.domain_digest, _canonical(definition.to_record()), principal.subject))
            if cursor.fetchone() is None:
                cursor.execute('SELECT definition_json FROM hosting_controlplane.migration_waves '
                    'WHERE organization_id=%s AND tenant_id=%s AND schedule_digest=%s',
                    (context.organization_id, context.tenant_id, definition.digest))
                row = cursor.fetchone()
                _require(row is not None and row[0] == _canonical(definition.to_record()),
                         'Immutable schedule reference changed')
                return definition.reference
            for member in definition.members:
                cursor.execute('INSERT INTO hosting_controlplane.migration_wave_members '
                    '(organization_id,tenant_id,schedule_digest,member_id,cohort_id,resource_keys,risk_groups,demand) '
                    'VALUES (%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb)',
                    (context.organization_id, context.tenant_id, definition.digest, member.member_id,
                     member.cohort, _canonical(resources[member.member_id]),
                     _canonical(domain.groups_for(member)), _canonical(asdict(member.demand))))
            self._event(cursor, context, domain.domain_id, definition.digest, None,
                        'SCHEDULE_REGISTERED', 'PLANNING_ONLY', {'memberCount': len(definition.members)})
            return definition.reference

    def _states(self, cursor, context, domain_id):
        cursor.execute('SELECT w.schedule_digest,w.definition_json,w.created_at,m.member_id,m.status,'
            'm.resource_keys,m.risk_groups,m.job_id FROM hosting_controlplane.migration_waves w '
            'JOIN hosting_controlplane.migration_wave_members m USING(organization_id,tenant_id,schedule_digest) '
            'WHERE w.organization_id=%s AND w.tenant_id=%s AND w.domain_id=%s '
            'ORDER BY w.created_at,w.schedule_digest,m.member_id LIMIT %s',
            (context.organization_id, context.tenant_id, domain_id, MAX_DOMAIN_MEMBERS + 1))
        rows = cursor.fetchall()
        _require(len(rows) <= MAX_DOMAIN_MEMBERS, 'Native domain scheduling inventory exceeds its bound')
        definitions, result = {}, []
        for digest, raw, created, member_id, status, resources, groups, job_id in rows:
            if digest not in definitions:
                definition = WaveDefinition.from_record(strict_loads(raw.encode()))
                _require(definition.digest == digest, 'Retained immutable schedule digest changed')
                definitions[digest] = {member.member_id: member for member in definition.members}
            _require(member_id in definitions[digest], 'Scheduling member has no original definition')
            result.append(MemberState(digest, definitions[digest][member_id], status,
                tuple(_json(resources)), tuple(_json(groups)), created, job_id))
        return result

    def admit_next(self, credential, context: TenantContext, domain_id: str, *, authorizations: dict):
        _require(type(authorizations) is dict and len(authorizations) <= MAX_DOMAIN_MEMBERS,
                 'Fresh independently authorized member decisions are required')
        with self.connect() as connection, connection.cursor() as cursor:
            _tenant(cursor, context)
            domain = self._domain(cursor, context, domain_id)
            cursor.execute('SELECT clock_timestamp()')
            now = cursor.fetchone()[0]
            principal = self._principal(credential, context, now)
            states = self._states(cursor, context, domain_id)
            cursor.execute('SELECT detail FROM hosting_controlplane.migration_wave_events '
                "WHERE organization_id=%s AND tenant_id=%s AND domain_id=%s AND event='MEMBER_ADMITTED' "
                'ORDER BY sequence DESC LIMIT 1', (context.organization_id, context.tenant_id, domain_id))
            last = cursor.fetchone()
            ready, reasons, totals = candidate_decisions(states, domain, now,
                _json(last[0])['cohort'] if last is not None else None,
                permitted_scopes=frozenset(grant.scope for grant in principal.grants
                    if grant.role == EXECUTION_OPERATOR and grant.expires_at > now
                    and isinstance(grant.scope, PlanScope)))
            for state in states:
                if reasons.get(state.key) == 'WINDOW_EXPIRED':
                    cursor.execute("UPDATE hosting_controlplane.migration_wave_members SET status='HELD',"
                        "reason='WINDOW_EXPIRED' WHERE organization_id=%s AND tenant_id=%s AND schedule_digest=%s "
                        "AND member_id=%s AND status='PENDING'", (*_tenant_pair(context), *state.key))
                    self._event(cursor, context, domain_id, state.schedule_digest, state.member.member_id,
                        'MEMBER_HELD', 'WINDOW_EXPIRED', {})
            if not ready:
                return WaveAdmission('HELD_OR_WAITING', None, None, None,
                    'NO_CURRENT_READY_MEMBER', totals)
            state, member = ready[0], ready[0].member
            for scope in (member.source, member.destination):
                require_scoped_role(principal, EXECUTION_OPERATOR, scope, now)
            authorization = authorizations.get(state.key)
            if authorization is None:
                return WaveAdmission('WAITING_AUTHORITY', 'wave-' + state.schedule_digest,
                    member.member_id, None, 'FRESH_MEMBER_APPROVAL_REQUIRED', totals)
            _require(isinstance(authorization, AuthorizedPlan) and authorization.actor_subject == principal.subject
                     and (authorization.organization_id, authorization.tenant_id, authorization.plan_id,
                          authorization.plan_revision, authorization.plan_digest, authorization.source,
                          authorization.destination) ==
                     (context.organization_id, context.tenant_id, member.plan_id, member.plan_revision,
                      member.plan_digest, member.source, member.destination),
                     'A wave cannot inherit another member, scope or operator approval')
            resources = self._current_member(cursor, context, member)
            resources = tuple(sorted(set(resources) | set(self.qualification.transfer_resource_keys(member))))
            _require(resources == state.resource_keys and domain.groups_for(member) == state.risk_groups,
                     'The retained resource overlap or risk ownership binding changed')
            self.qualification.require_member(cursor, context, member, now)
            cursor.execute('SELECT clock_timestamp()')
            current = cursor.fetchone()[0]
            # Locks/file validation may have consumed the usable window/session.
            _require(current < principal.expires_at and current < domain.expires_at and
                     member.window_start <= current and
                     current + timedelta(seconds=member.runtime_seconds) <= member.window_end,
                     'Authority, budget or window expired while awaiting admission')
            for scope in (member.source, member.destination):
                require_scoped_role(principal, EXECUTION_OPERATOR, scope, current)
            from .enterprise_wave import require_pool_turn
            if not require_pool_turn(cursor, context, domain, state, principal, authorization, current):
                return WaveAdmission('WAITING_ENTERPRISE_TURN',
                    'wave-' + state.schedule_digest, member.member_id, None,
                    'ENTERPRISE_TENANT_TURN_OR_BUDGET_UNAVAILABLE', totals)
            key = 'wave-' + _digest({'scheduleDigest': state.schedule_digest, 'memberId': member.member_id})
            job = self.jobs.submit_in_transaction(cursor, context, authorization, idempotency_key=key)
            _require(job.status == 'QUEUED', 'A saved wave cannot adopt an already executing or terminal job')
            cursor.execute("UPDATE hosting_controlplane.migration_wave_members SET status='ADMITTED',"
                "reason='B09_ADMITTED',job_id=%s,claimed_at=clock_timestamp() WHERE organization_id=%s "
                "AND tenant_id=%s AND schedule_digest=%s AND member_id=%s AND status='PENDING'",
                (job.job_id, *_tenant_pair(context), *state.key))
            _require(cursor.rowcount == 1, 'Another admission owns this immutable member')
            for resource in resources:
                cursor.execute('INSERT INTO hosting_controlplane.migration_wave_resource_claims '
                    '(organization_id,tenant_id,resource_key,schedule_digest,member_id) VALUES(%s,%s,%s,%s,%s)',
                    (*_tenant_pair(context), resource, *state.key))
            self._event(cursor, context, domain_id, state.schedule_digest, member.member_id,
                'MEMBER_ADMITTED', 'B09_ADMITTED', {'jobId': job.job_id, 'cohort': member.cohort,
                    'planDigest': member.plan_digest, 'campaignDigest': member.campaign.digest})
            charged = {key: totals[key] + value for key, value in asdict(member.demand).items()}
            return WaveAdmission('JOB_QUEUED', 'wave-' + state.schedule_digest, member.member_id,
                                 job.job_id, 'B09_OUTBOX_COMMITTED', charged)

    def reconcile_release(self, credential, context: TenantContext, schedule_digest: str, member_id: str):
        """Consume independently accepted completion; never author that acceptance."""
        _sha(schedule_digest)
        _identifier(member_id)
        with self.connect() as connection, connection.cursor() as cursor:
            _tenant(cursor, context)
            cursor.execute('SELECT domain_id FROM hosting_controlplane.migration_waves '
                'WHERE organization_id=%s AND tenant_id=%s AND schedule_digest=%s',
                (*_tenant_pair(context), schedule_digest))
            row = cursor.fetchone()
            _require(row is not None, 'Unknown scoped immutable wave')
            domain_id = row[0]
            self._domain(cursor, context, domain_id)
            cursor.execute('SELECT clock_timestamp()')
            now = cursor.fetchone()[0]
            principal = self._principal(credential, context, now)
            states = self._states(cursor, context, domain_id)
            matches = [state for state in states if state.key == (schedule_digest, member_id)]
            _require(len(matches) == 1 and matches[0].job_id is not None, 'Member has no original admitted job')
            state = matches[0]
            for scope in (state.member.source, state.member.destination):
                require_scoped_role(principal, EXECUTION_OPERATOR, scope, now)
            if state.status == 'SUCCEEDED':
                return 'ALREADY_ACCEPTED_AND_RELEASED'
            cursor.execute('SELECT acceptance_digest FROM hosting_controlplane.migration_wave_release_acceptances '
                'WHERE organization_id=%s AND tenant_id=%s AND schedule_digest=%s AND member_id=%s '
                'AND job_id=%s AND observed_at<=%s AND expires_at>%s',
                (*_tenant_pair(context), schedule_digest, member_id, state.job_id, now, now))
            acceptance = cursor.fetchone()
            if acceptance is None:
                return 'HELD_NATIVE_RELEASE_ACCEPTANCE_REQUIRED'
            # SQL transition guard rechecks the current terminal job, its exact
            # start/event binding and independently resolved/quiesced native work.
            cursor.execute("UPDATE hosting_controlplane.migration_wave_members SET status='SUCCEEDED',"
                "reason='ACCEPTED_RELEASE',released_at=clock_timestamp() WHERE organization_id=%s "
                'AND tenant_id=%s AND schedule_digest=%s AND member_id=%s',
                (*_tenant_pair(context), schedule_digest, member_id))
            cursor.execute('UPDATE hosting_controlplane.migration_wave_resource_claims SET released_at=clock_timestamp() '
                'WHERE organization_id=%s AND tenant_id=%s AND schedule_digest=%s AND member_id=%s AND released_at IS NULL',
                (*_tenant_pair(context), schedule_digest, member_id))
            self._event(cursor, context, domain_id, schedule_digest, member_id, 'MEMBER_RELEASED',
                        'ACCEPTED_RELEASE', {'jobId': state.job_id, 'acceptanceDigest': acceptance[0]})
            return 'ACCEPTED_AND_RELEASED'


def _tenant_pair(context):
    return context.organization_id, context.tenant_id


def require_wave_window(cursor, job, at: datetime, *, starting=False):
    """Current B09/B10 transaction gate; unaffiliated jobs keep their old policy.

    Called again before grants/effects. Window expiry retains all reservations
    and requires containment/reconciliation; it never invents a completed job.
    A read-only observation may still inspect an expired/held original operation.
    """
    _require(isinstance(job, Job), 'Current wave checks require the exact persisted B09 job')
    _instant(at)
    cursor.execute('SELECT * FROM hosting_controlplane.migration_wave_job_window(%s,%s,%s)',
        (job.organization_id, job.tenant_id, job.job_id))
    row = cursor.fetchone()
    if row is None:
        return
    (status, selected_domain_digest, current_domain_digest, budget_start, budget_end,
     window_start, window_end, runtime_seconds, plan_id, plan_revision, plan_digest) = row
    _require(status == 'ADMITTED' and selected_domain_digest == current_domain_digest,
             'Wave member or commissioned budget is held or changed')
    remaining = runtime_seconds if starting else 0
    _require((plan_id, plan_revision, plan_digest) ==
             (job.plan_id, job.plan_revision, job.plan_digest)
             and budget_start <= at < budget_end
             and window_start <= at < window_end
             and at + timedelta(seconds=remaining) <= window_end,
             'Current wave execution window or original member binding expired')
