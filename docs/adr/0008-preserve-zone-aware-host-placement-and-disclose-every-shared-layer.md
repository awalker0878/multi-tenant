# ADR-0008 — Preserve zone-aware host placement and disclose every shared layer

**Status:** Proposed<br>
**Accountable role:** Architecture authority and responsible infrastructure service owner<br>
**Scope:** Portable hosting reference pattern; site/service adoption remains unrecorded<br>
**Original decision identifiers:** `AD-06`<br>
**Source chapters:** [RA §7](../architecture/reference/7-tenant-environments-and-security-domain-placement.md) · [RA §11](../architecture/reference/11-compute-pools-hypervisors-and-workload-placement.md) · [VND §2](../engineering/platform-realizations/2-physical-placement-and-the-sharing-decision.md) · [SDP §2](../solutions/design-method/2-choose-sharing-at-each-infrastructure-layer.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The linked record is not made authoritative by rendering it. Real adoption needs the stated scope, actual authority and independently protected decision evidence.

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

Related implementation areas are traceability targets, not proof of complete implementation:

- [terraform/modules/nutanix-workload](../../terraform/modules/nutanix-workload)
- [terraform/modules/vsphere-workload](../../terraform/modules/vsphere-workload)
- [terraform/modules/openstack-workload](../../terraform/modules/openstack-workload)

Review [the assertion allocation](../implementation/assertion-allocation.md) for enforcement owner, location, evidence class and unimplemented dependencies.

## Open decisions and acceptance

Co-residency approval, physical pool assignment and native scheduler enforcement have not been established by document conversion.

**Deciding authority:** Not recorded<br>
**Decision date:** Not recorded<br>
**Decision record:** Not supplied<br>
**Evidence references:** Not supplied<br>
**Decision rationale:** No lifecycle decision recorded<br>
**Superseded by:** None

Evidence references require owner verification; this repository does not authenticate a signatory or issue native operating authorization. Source-derived Proposed records remain proposed until their genuine decision is recorded. Accepted and rejected records are retained, not overwritten out of history.

---

[Decision register](README.md) · [Maintained design workspace](../current/README.md)
