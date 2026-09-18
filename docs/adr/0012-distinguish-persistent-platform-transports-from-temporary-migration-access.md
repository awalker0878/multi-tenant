# ADR-0012 — Distinguish persistent platform transports from temporary migration access

**Status:** Proposed<br>
**Accountable role:** Architecture authority and responsible infrastructure service owner<br>
**Scope:** Portable hosting reference pattern; site/service adoption remains unrecorded<br>
**Original decision identifiers:** `AD-10`<br>
**Source chapters:** [RA §5](../architecture/reference/5-physical-fabric-and-platform-attachment.md) · [RA §10](../architecture/reference/10-addressing-name-services-and-end-to-end-traffic.md) · [RA §27](../architecture/reference/27-recovery-migration-and-retirement.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The linked record is not made authoritative by rendering it. Real adoption needs the stated scope, actual authority and independently protected decision evidence.

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

Related implementation areas are traceability targets, not proof of complete implementation:

- [terraform/modules/nutanix-route](../../terraform/modules/nutanix-route)
- [terraform/modules/nsx-route](../../terraform/modules/nsx-route)
- [terraform/modules/openstack-route](../../terraform/modules/openstack-route)

Review [the assertion allocation](../implementation/assertion-allocation.md) for enforcement owner, location, evidence class and unimplemented dependencies.

## Open decisions and acceptance

Supported native mobility transport and the approved migration connection remain site-specific records.

**Deciding authority:** Not recorded<br>
**Decision date:** Not recorded<br>
**Decision record:** Not supplied<br>
**Evidence references:** Not supplied<br>
**Decision rationale:** No lifecycle decision recorded<br>
**Superseded by:** None

Evidence references require owner verification; this repository does not authenticate a signatory or issue native operating authorization. Source-derived Proposed records remain proposed until their genuine decision is recorded. Accepted and rejected records are retained, not overwritten out of history.

---

[Decision register](README.md) · [Maintained design workspace](../current/README.md)
