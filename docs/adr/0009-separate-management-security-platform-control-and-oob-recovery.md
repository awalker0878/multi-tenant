# ADR-0009 — Separate management security, platform control and OOB recovery

**Status:** Proposed — source-derived; organizational acceptance not recorded<br>
**Original decision identifiers:** `AD-07`<br>
**Source chapters:** [RA §6](../architecture/reference/6-management-platform-control-and-out-of-band-access.md) · [NET §6](../engineering/fabric/6-management-paths-and-interface-handover.md) · [SVC §3](../architecture/shared-services/3-identity-certificates-keys-and-independent-recovery.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The original source remains linked below; this ADR does not record an approval meeting or invent an acceptance date.

## Context

Workload access, infrastructure administration and recovery have different authority and availability needs. A management VLAN name does not prove physical independence.

## Decision recorded in the source

Use separately controlled management domains and privileged access paths. Treat MZ as security semantics, platform APIs as control interfaces and OOB as an explicitly designed transport/recovery property.

## Alternatives and limits recorded in the source

Shared transport or consolidated management is a disclosed variation; it cannot be labelled physically independent or become unrestricted MZ-to-MZ routing.

## Consequences

Shared tools and appliances may still expose distinct consumption and administration interfaces. Emergency access must survive its specified failure without becoming a standing unaccountable bypass.

## Engineering and implementation obligations

Map human, automation, tenant-guest and supplier administration separately. Document actual routes, role permissions, hardware recovery dependencies and post-use credential revocation.

## Requirement and code traceability

[ARCH-004](../assurance/requirements.md#ARCH-004) · [MGT-001](../assurance/requirements.md#MGT-001) · [MGT-002](../assurance/requirements.md#MGT-002) · [MGT-005](../assurance/requirements.md#MGT-005) · [IAM-002](../assurance/requirements.md#IAM-002)

The following implementation areas are traceability targets, not proof that this decision has been qualified:

- [tools/nsx_observe.py](../../tools/nsx_observe.py)
- [tools/nutanix_observe.py](../../tools/nutanix_observe.py)
- [tools/neutron_observe.py](../../tools/neutron_observe.py)

Review [the implementation coverage map](../implementation/code-map.md) and the target-specific evidence before asserting completion. A local fixture or static source check does not establish deployed behaviour.

## Open decisions and acceptance

Management/OOB independence, accepted principals, real access paths and break-glass exercises require the actual site.

Accepting authority: **not recorded**.<br>
Acceptance evidence: **not supplied by this conversion**.<br>
Supersession: no new source supersession is asserted. Record a future change explicitly rather than silently editing an accepted decision.

---

[Decision register](README.md) · [Source and maintenance rules](../DOCUMENTATION_MIGRATION.md)
