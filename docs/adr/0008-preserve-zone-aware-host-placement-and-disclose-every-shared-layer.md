# ADR-0008 — Preserve zone-aware host placement and disclose every shared layer

**Status:** Proposed — source-derived; organizational acceptance not recorded<br>
**Original decision identifiers:** `AD-06`<br>
**Source chapters:** [RA §7](../architecture/reference/7-tenant-environments-and-security-domain-placement.md) · [RA §11](../architecture/reference/11-compute-pools-hypervisors-and-workload-placement.md) · [VND §2](../engineering/platform-realizations/2-physical-placement-and-the-sharing-decision.md) · [SDP §2](../solutions/design-method/2-choose-sharing-at-each-infrastructure-layer.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The original source remains linked below; this ADR does not record an approval meeting or invent an acceptance date.

## Context

A routing boundary does not establish a host-compromise boundary. HCI controllers, storage and management can remain shared when guest placement is separated.

## Decision recorded in the source

Retain the source zone-specific host-pool baseline. Express dedication and approved sharing separately for hosts, storage, edge, management, backup and key custody; enforce the same eligibility during placement, migration, restart and restore.

## Alternatives and limits recorded in the source

Cross-zone co-residency or wider consolidation requires explicit security analysis and authorized variation. Matching an RZ label is not that approval.

## Consequences

A dedicated workload host is not an independently administered platform. Failure reserve must exist in eligible pools; an unavailable compliant host cannot be replaced with an ineligible one just to preserve uptime.

## Engineering and implementation obligations

Provide the per-layer sharing matrix, scheduler constraints, disclosed controller/backend dependencies and migration/restart/restore tests.

## Requirement and code traceability

[CMP-001](../assurance/requirements.md#CMP-001) · [CMP-003](../assurance/requirements.md#CMP-003) · [ASSUR-001](../assurance/requirements.md#ASSUR-001) · [ASSUR-002](../assurance/requirements.md#ASSUR-002) · [SDI-004](../assurance/requirements.md#SDI-004)

The following implementation areas are traceability targets, not proof that this decision has been qualified:

- [terraform/modules/nutanix-workload](../../terraform/modules/nutanix-workload)
- [terraform/modules/vsphere-workload](../../terraform/modules/vsphere-workload)
- [terraform/modules/openstack-workload](../../terraform/modules/openstack-workload)

Review [the implementation coverage map](../implementation/code-map.md) and the target-specific evidence before asserting completion. A local fixture or static source check does not establish deployed behaviour.

## Open decisions and acceptance

Co-residency approval, physical pool assignment and native scheduler enforcement have not been established by document conversion.

Accepting authority: **not recorded**.<br>
Acceptance evidence: **not supplied by this conversion**.<br>
Supersession: no new source supersession is asserted. Record a future change explicitly rather than silently editing an accepted decision.

---

[Decision register](README.md) · [Source and maintenance rules](../DOCUMENTATION_MIGRATION.md)
