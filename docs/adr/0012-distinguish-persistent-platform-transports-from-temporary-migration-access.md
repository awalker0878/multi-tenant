# ADR-0012 — Distinguish persistent platform transports from temporary migration access

**Status:** Proposed — source-derived; organizational acceptance not recorded<br>
**Original decision identifiers:** `AD-10`<br>
**Source chapters:** [RA §5](../architecture/reference/5-physical-fabric-and-platform-attachment.md) · [RA §10](../architecture/reference/10-addressing-name-services-and-end-to-end-traffic.md) · [RA §27](../architecture/reference/27-recovery-migration-and-retirement.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The original source remains linked below; this ADR does not record an approval meeting or invent an acceptance date.

## Context

The time-bound migration rule can be misread as requiring a new hypervisor mobility or storage-replication network for every operation.

## Decision recorded in the source

Allow persistent provider-owned live-mobility and replication transports where the platform needs them. Bound temporary cross-domain or cross-platform transfer access by purpose, authority, duration and teardown.

## Alternatives and limits recorded in the source

A physical routing context is justified by actual forwarding and isolation responsibility, not the function name migration, backup or platform.

## Consequences

Guest networks must not gain access to persistent privileged transports. A temporary connection becomes steady state only through an explicit new acceptance decision.

## Engineering and implementation obligations

Keep endpoint membership and transport ownership distinct from the temporary grant schedule. Verify relocation eligibility and removal of obsolete transfer routes and credentials.

## Requirement and code traceability

[FAB-003](../assurance/requirements.md#FAB-003) · [MIG-001](../assurance/requirements.md#MIG-001) · [MIG-002](../assurance/requirements.md#MIG-002) · [MIG-003](../assurance/requirements.md#MIG-003)

The following implementation areas are traceability targets, not proof that this decision has been qualified:

- [terraform/modules/nutanix-route](../../terraform/modules/nutanix-route)
- [terraform/modules/nsx-route](../../terraform/modules/nsx-route)
- [terraform/modules/openstack-route](../../terraform/modules/openstack-route)

Review [the implementation coverage map](../implementation/code-map.md) and the target-specific evidence before asserting completion. A local fixture or static source check does not establish deployed behaviour.

## Open decisions and acceptance

Supported native mobility transport and the approved migration connection remain site-specific records.

Accepting authority: **not recorded**.<br>
Acceptance evidence: **not supplied by this conversion**.<br>
Supersession: no new source supersession is asserted. Record a future change explicitly rather than silently editing an accepted decision.

---

[Decision register](README.md) · [Source and maintenance rules](../DOCUMENTATION_MIGRATION.md)
