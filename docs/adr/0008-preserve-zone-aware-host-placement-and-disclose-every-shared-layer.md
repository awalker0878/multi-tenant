# ADR-0008 — Preserve zone-aware host placement and disclose every shared layer

**Status:** Proposed<br>
**Accountable role:** Platform engineering / Architecture authority / Security authority<br>
**Scope:** Reusable reference decision; actual site adoption remains unissued<br>
**Record date:** 2026-09-17 (not an approval date)<br>
**Original decision identifiers:** `AD-06`<br>
**Source chapters:** [RA §7](../architecture/reference/7-tenant-environments-and-security-domain-placement.md) · [RA §11](../architecture/reference/11-compute-pools-hypervisors-and-workload-placement.md) · [VND §2](../engineering/platform-realizations/2-physical-placement-and-the-sharing-decision.md) · [SDP §2](../solutions/design-method/2-choose-sharing-at-each-infrastructure-layer.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting.

## Context

A routing boundary does not establish a host-compromise boundary. HCI controllers, storage and management can remain shared when guest placement is separated.

## Decision

Retain the source zone-specific host-pool baseline. Express dedication and approved sharing separately for hosts, storage, edge, management, backup and key custody; enforce the same eligibility during placement, migration, restart and restore.

## Alternatives and source limitations

Cross-zone co-residency or wider consolidation requires explicit security analysis and authorized variation. Matching an RZ label is not that approval.

## Consequences

A dedicated workload host is not an independently administered platform. Failure reserve must exist in eligible pools; an unavailable compliant host cannot be replaced with an ineligible one just to preserve uptime.

## Engineering and implementation obligations

Provide the per-layer sharing matrix, scheduler constraints, disclosed controller/backend dependencies and migration/restart/restore tests.

## Requirement and code traceability

[CMP-001](../assurance/requirements.md#CMP-001) · [CMP-003](../assurance/requirements.md#CMP-003) · [ASSUR-001](../assurance/requirements.md#ASSUR-001) · [ASSUR-002](../assurance/requirements.md#ASSUR-002) · [SDI-004](../assurance/requirements.md#SDI-004)

These are related implementation areas, not assertion-level evidence of native qualification:

- [terraform/modules/nutanix-workload](../../terraform/modules/nutanix-workload)
- [terraform/modules/vsphere-workload](../../terraform/modules/vsphere-workload)
- [terraform/modules/openstack-workload](../../terraform/modules/openstack-workload)

[Requirement/assertion allocation](../assurance/implementation-allocation.md) records partial, external and unimplemented controls separately.

## Open work

Co-residency approval, physical pool assignment and native scheduler enforcement have not been established by document conversion.

## Decision lifecycle and authority

- Deciding authority: Not recorded.
- Decision date: Not recorded.
- Decision evidence: Not supplied; no acceptance claim.
- Disposition rationale: No rejection or supersession recorded.
- Supersedes: None.
- Superseded by: None.

Record authenticity and the deciding authority's jurisdiction require independent review. Passing a record-schema check does not issue or authenticate an approval. The current record status is declared above; publication never grants decision authority.

[Decision register](README.md) · [Maintenance rules](../DOCUMENTATION_MIGRATION.md)
