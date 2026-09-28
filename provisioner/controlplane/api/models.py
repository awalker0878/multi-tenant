"""Wire shapes for the first workload and job API routes.

The detailed nested workload contract remains the versioned B03 JSON Schema.
The HTTP boundary constrains its top-level shape and creation provenance, then
passes the complete document to that canonical validator in the record store.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', populate_by_name=False, strict=True)


_ID = r'^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$'


class KnownInteger(_StrictModel):
    state: Literal['KNOWN']
    value: int = Field(ge=0)


class UnknownInteger(_StrictModel):
    state: Literal['UNKNOWN']
    reason: str = Field(min_length=1)


class KnownString(_StrictModel):
    state: Literal['KNOWN']
    value: str = Field(min_length=1)


class UnknownString(_StrictModel):
    state: Literal['UNKNOWN']
    reason: str = Field(min_length=1)


class NativeBinding(_StrictModel):
    endpoint_id: str = Field(alias='endpointId', pattern=_ID)
    native_scope_id: str = Field(alias='nativeScopeId', min_length=1, max_length=512)
    native_id: str = Field(alias='nativeId', min_length=1, max_length=512)
    resource_kind: Literal['vm', 'disk', 'nic', 'volume', 'dataset', 'network'] = Field(alias='resourceKind')
    platform_family: Literal['vmware', 'nutanix', 'openstack'] = Field(alias='platformFamily')


class BindingHistory(_StrictModel):
    binding: NativeBinding
    role: Literal['SOURCE', 'TARGET', 'RETIRED']
    first_seen_snapshot_id: str = Field(alias='firstSeenSnapshotId', pattern=_ID)
    last_observed_snapshot_id: str = Field(alias='lastObservedSnapshotId', pattern=_ID)


class Disk(_StrictModel):
    disk_id: str = Field(alias='diskId', pattern=_ID)
    bindings: list[BindingHistory]
    slot: int = Field(ge=0)
    size_bytes: KnownInteger | UnknownInteger = Field(alias='sizeBytes')
    format: KnownString | UnknownString
    unknown_fields: list[str] = Field(alias='unknownFields')


class Nic(_StrictModel):
    nic_id: str = Field(alias='nicId', pattern=_ID)
    bindings: list[BindingHistory]
    slot: int = Field(ge=0)
    network: KnownString | UnknownString
    address: KnownString | UnknownString
    unknown_fields: list[str] = Field(alias='unknownFields')


class Machine(_StrictModel):
    machine_id: str = Field(alias='machineId', pattern=_ID)
    display_name: str = Field(alias='displayName', min_length=1)
    bindings: list[BindingHistory]
    guest_profile: KnownString | UnknownString = Field(alias='guestProfile')
    cpu_count: KnownInteger | UnknownInteger = Field(alias='cpuCount')
    memory_mib: KnownInteger | UnknownInteger = Field(alias='memoryMiB')
    firmware: KnownString | UnknownString
    disks: list[Disk]
    disks_complete: bool = Field(alias='disksComplete')
    nics: list[Nic]
    nics_complete: bool = Field(alias='nicsComplete')
    unknown_fields: list[str] = Field(alias='unknownFields')


class Dataset(_StrictModel):
    dataset_id: str = Field(alias='datasetId', pattern=_ID)
    kind: Literal['volume', 'file-tree', 'object', 'database']
    machine_id: str | None = Field(alias='machineId')
    source_bindings: list[NativeBinding] = Field(alias='sourceBindings')
    consistency_group_id: str = Field(alias='consistencyGroupId', pattern=_ID)
    size_bytes: KnownInteger | UnknownInteger = Field(alias='sizeBytes')
    unknown_fields: list[str] = Field(alias='unknownFields')


class WorkloadMetadata(_StrictModel):
    organization_id: str = Field(alias='organizationId', pattern=_ID)
    tenant_id: str = Field(alias='tenantId', pattern=_ID)
    workload_id: str = Field(alias='workloadId', pattern=_ID)
    wsd_id: str = Field(alias='wsdId', pattern=_ID)
    revision: Literal[1]
    owner_id: str = Field(alias='ownerId', pattern=_ID)
    criticality: Literal['low', 'moderate', 'high', 'unknown']


class InitialMembership(_StrictModel):
    state: Literal['ACCEPTED']
    candidate_wsd_id: None = Field(alias='candidateWsdId')
    transition: None
    history: list[dict[str, Any]] = Field(max_length=0)


class PlannedWorkloadSpec(_StrictModel):
    state: Literal['PLANNED']
    name: str = Field(min_length=1)
    membership: InitialMembership
    machines: list[Machine] = Field(min_length=1)
    datasets: list[Dataset]
    unknown_fields: list[str] = Field(alias='unknownFields')


class WorkloadCreate(_StrictModel):
    api_version: Literal['hosting.platform/v1'] = Field(alias='apiVersion')
    kind: Literal['Workload']
    metadata: WorkloadMetadata
    spec: PlannedWorkloadSpec

    def canonical_document(self) -> dict[str, Any]:
        return self.model_dump(by_alias=True, exclude_none=False)


class StoredWorkload(_StrictModel):
    record: dict[str, Any] = Field(description='Canonical hosting.platform/v1 Workload document.')
    revision: int = Field(ge=1)
    digest: str = Field(pattern='^[0-9a-f]{64}$')


class WorkloadPage(_StrictModel):
    items: list[StoredWorkload]
    next_after: str | None = Field(alias='nextAfter')


class EnvironmentCreate(_StrictModel):
    """Human-declared selector; the caller cannot assert observed readiness."""
    environment_id: str = Field(alias='environmentId', pattern=_ID)
    display_name: str = Field(alias='displayName', min_length=1, max_length=256,
                              pattern=r'^[^\x00-\x1f\x7f]+$')
    site_id: str = Field(alias='siteId', pattern=_ID)
    security_domain_id: str = Field(alias='securityDomainId', pattern=_ID)
    endpoint_id: str = Field(alias='endpointId', pattern=_ID)
    native_scope_id: str = Field(alias='nativeScopeId', min_length=1, max_length=512)
    platform_family: Literal['vmware', 'nutanix', 'openstack'] = Field(alias='platformFamily')

    @field_validator('native_scope_id')
    @classmethod
    def valid_native_scope(cls, value: str) -> str:
        if not value.strip() or any(ord(char) < 32 or ord(char) == 127 for char in value):
            raise ValueError('Native scope must be a bounded non-control selector')
        return value


class EnvironmentView(EnvironmentCreate):
    status: Literal['DECLARED_UNVERIFIED']
    record_digest: str = Field(alias='recordDigest', pattern='^[0-9a-f]{64}$')
    registered_at: datetime = Field(alias='registeredAt')


class EnvironmentPage(_StrictModel):
    items: list[EnvironmentView]
    next_after: str | None = Field(alias='nextAfter')


class ErrorDetail(_StrictModel):
    code: str
    message: str
    path: str | None = None


class ErrorResponse(_StrictModel):
    error: ErrorDetail


class JobView(_StrictModel):
    job_id: str = Field(alias='jobId')
    plan_id: str = Field(alias='planId')
    plan_revision: int = Field(alias='planRevision', ge=1)
    plan_digest: str = Field(alias='planDigest', pattern='^[0-9a-f]{64}$')
    status: str
    last_event_sequence: int = Field(alias='lastEventSequence', ge=1)
    created_at: datetime = Field(alias='createdAt')
    updated_at: datetime = Field(alias='updatedAt')


class JobEventView(_StrictModel):
    sequence: int = Field(ge=1)
    event_type: str = Field(alias='eventType')
    status: str
    recorded_at: datetime = Field(alias='recordedAt')


class JobEventPage(_StrictModel):
    items: list[JobEventView]
    next_after: int | None = Field(alias='nextAfter')


class PortfolioAccess(_StrictModel):
    kind: Literal['PORTFOLIO']
    role: str
    organization_id: str = Field(alias='organizationId')
    tenant_id: str = Field(alias='tenantId')
    security_domain_id: str = Field(alias='securityDomainId')
    expires_at: datetime = Field(alias='expiresAt')


class NativeAccess(_StrictModel):
    kind: Literal['NATIVE']
    role: str
    organization_id: str = Field(alias='organizationId')
    tenant_id: str = Field(alias='tenantId')
    site_id: str = Field(alias='siteId')
    security_domain_id: str = Field(alias='securityDomainId')
    endpoint_id: str = Field(alias='endpointId')
    native_scope_id: str = Field(alias='nativeScopeId')
    platform_family: str = Field(alias='platformFamily')
    expires_at: datetime = Field(alias='expiresAt')


class AccessPage(_StrictModel):
    """Verified role selectors, not a deployed environment inventory."""
    items: list[PortfolioAccess | NativeAccess]


class ReviewScope(_StrictModel):
    organization_id: str = Field(alias='organizationId')
    tenant_id: str = Field(alias='tenantId')
    site_id: str = Field(alias='siteId')
    security_domain_id: str = Field(alias='securityDomainId')
    endpoint_id: str = Field(alias='endpointId')
    native_scope_id: str = Field(alias='nativeScopeId')
    platform_family: str = Field(alias='platformFamily')


class PlanReview(_StrictModel):
    """Allowlisted decision facts from a current, authority-bound plan."""
    plan_id: str = Field(alias='planId')
    plan_revision: int = Field(alias='planRevision', ge=1)
    plan_digest: str = Field(alias='planDigest', pattern='^[0-9a-f]{64}$')
    frozen_at: datetime = Field(alias='frozenAt')
    workload_id: str = Field(alias='workloadId')
    workload_revision: int = Field(alias='workloadRevision', ge=1)
    source_snapshot_id: str = Field(alias='sourceSnapshotId')
    destination_snapshot_id: str = Field(alias='destinationSnapshotId')
    source: ReviewScope
    destination: ReviewScope
    route_method: str = Field(alias='routeMethod')
    selected_machine_count: int = Field(alias='selectedMachineCount', ge=1)
    selected_dataset_count: int = Field(alias='selectedDatasetCount', ge=0)
    max_downtime_seconds: int = Field(alias='maxDowntimeSeconds', ge=0)
    max_data_loss_seconds: int = Field(alias='maxDataLossSeconds', ge=0)
    rollback_window_seconds: int = Field(alias='rollbackWindowSeconds', ge=0)
    eligible_roles: list[Literal['SOURCE_OWNER', 'DESTINATION_OWNER',
                                 'SOURCE_SECURITY', 'DESTINATION_SECURITY']] = Field(alias='eligibleRoles')


class ApprovalRequest(_StrictModel):
    role: Literal['SOURCE_OWNER', 'DESTINATION_OWNER',
                  'SOURCE_SECURITY', 'DESTINATION_SECURITY']
    ttl_seconds: int = Field(alias='ttlSeconds', ge=1, le=28800)
    expected_plan_revision: int = Field(alias='expectedPlanRevision', ge=1)
    expected_plan_digest: str = Field(alias='expectedPlanDigest', pattern='^[0-9a-f]{64}$')


class ApprovalReceipt(_StrictModel):
    approval_id: str = Field(alias='approvalId')
    plan_id: str = Field(alias='planId')
    plan_revision: int = Field(alias='planRevision', ge=1)
    plan_digest: str = Field(alias='planDigest', pattern='^[0-9a-f]{64}$')
    role: str
    expires_at: datetime = Field(alias='expiresAt')


class RevocationRequest(_StrictModel):
    reason: str = Field(min_length=1, max_length=512,
                        pattern=r'^[^\x00-\x1f\x7f]+$')


class RevocationReceipt(_StrictModel):
    plan_id: str = Field(alias='planId')
    revocation_epoch: int = Field(alias='revocationEpoch', ge=1)
