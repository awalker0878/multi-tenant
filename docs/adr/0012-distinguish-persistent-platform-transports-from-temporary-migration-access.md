# ADR-0012 — Distinguish persistent platform transports from temporary migration access

**Status:** Proposed<br>
**Accountable role:** Architecture authority / Migration owner<br>
**Scope:** Reusable reference decision; actual site adoption remains unissued<br>
**Record date:** 2026-09-17 (not an approval date)<br>
**Original decision identifiers:** `AD-10`<br>
**Source chapters:** [RA §5](../architecture/reference/5-physical-fabric-and-platform-attachment.md) · [RA §10](../architecture/reference/10-addressing-name-services-and-end-to-end-traffic.md) · [RA §27](../architecture/reference/27-recovery-migration-and-retirement.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting.

## Context

The time-bound migration rule can be misread as requiring a new hypervisor mobility or storage-replication network for every operation.

## Decision

Allow persistent provider-owned live-mobility and replication transports where the platform needs them. Bound temporary cross-domain or cross-platform transfer access by purpose, authority, duration and teardown.

## Alternatives and source limitations

A physical routing context is justified by actual forwarding and isolation responsibility, not the function name migration, backup or platform.

## Consequences

Guest networks must not gain access to persistent privileged transports. A temporary connection becomes steady state only through an explicit new acceptance decision.

## Engineering and implementation obligations

Keep endpoint membership and transport ownership distinct from the temporary grant schedule. Verify relocation eligibility and removal of obsolete transfer routes and credentials.

## Requirement and code traceability

[FAB-003](../assurance/requirements.md#FAB-003) · [MIG-001](../assurance/requirements.md#MIG-001) · [MIG-002](../assurance/requirements.md#MIG-002) · [MIG-003](../assurance/requirements.md#MIG-003)

These are related implementation areas, not assertion-level evidence of native qualification:

- [terraform/modules/nutanix-route](../../terraform/modules/nutanix-route)
- [terraform/modules/nsx-route](../../terraform/modules/nsx-route)
- [terraform/modules/openstack-route](../../terraform/modules/openstack-route)

[Requirement/assertion allocation](../assurance/implementation-allocation.md) records partial, external and unimplemented controls separately.

## Open work

Supported native mobility transport and the approved migration connection remain site-specific records.

## Decision lifecycle and authority

- Deciding authority: Not recorded.
- Decision date: Not recorded.
- Decision evidence: Not supplied; no acceptance claim.
- Disposition rationale: No rejection or supersession recorded.
- Supersedes: None.
- Superseded by: None.

Record authenticity and the deciding authority's jurisdiction require independent review. Passing a record-schema check does not issue or authenticate an approval. The current record status is declared above; publication never grants decision authority.

[Decision register](README.md) · [Maintenance rules](../DOCUMENTATION_MIGRATION.md)
