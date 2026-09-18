# ADR-0009 — Separate management security, platform control and OOB recovery

**Status:** Proposed<br>
**Accountable role:** Architecture authority / Management operations / Identity operations<br>
**Scope:** Reusable reference decision; actual site adoption remains unissued<br>
**Record date:** 2026-09-17 (not an approval date)<br>
**Original decision identifiers:** `AD-07`<br>
**Source chapters:** [RA §6](../architecture/reference/6-management-platform-control-and-out-of-band-access.md) · [NET §6](../engineering/fabric/6-management-paths-and-interface-handover.md) · [SVC §3](../architecture/shared-services/3-identity-certificates-keys-and-independent-recovery.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting.

## Context

Workload access, infrastructure administration and recovery have different authority and availability needs. A management VLAN name does not prove physical independence.

## Decision

Use separately controlled management domains and privileged access paths. Treat MZ as security semantics, platform APIs as control interfaces and OOB as an explicitly designed transport/recovery property.

## Alternatives and source limitations

Shared transport or consolidated management is a disclosed variation; it cannot be labelled physically independent or become unrestricted MZ-to-MZ routing.

## Consequences

Shared tools and appliances may still expose distinct consumption and administration interfaces. Emergency access must survive its specified failure without becoming a standing unaccountable bypass.

## Engineering and implementation obligations

Map human, automation, tenant-guest and supplier administration separately. Document actual routes, role permissions, hardware recovery dependencies and post-use credential revocation.

## Requirement and code traceability

[ARCH-004](../assurance/requirements.md#ARCH-004) · [MGT-001](../assurance/requirements.md#MGT-001) · [MGT-002](../assurance/requirements.md#MGT-002) · [MGT-005](../assurance/requirements.md#MGT-005) · [IAM-002](../assurance/requirements.md#IAM-002)

These are related implementation areas, not assertion-level evidence of native qualification:

- [tools/nsx_observe.py](../../tools/nsx_observe.py)
- [tools/nutanix_observe.py](../../tools/nutanix_observe.py)
- [tools/neutron_observe.py](../../tools/neutron_observe.py)

[Requirement/assertion allocation](../assurance/implementation-allocation.md) records partial, external and unimplemented controls separately.

## Open work

Management/OOB independence, accepted principals, real access paths and break-glass exercises require the actual site.

## Decision lifecycle and authority

- Deciding authority: Not recorded.
- Decision date: Not recorded.
- Decision evidence: Not supplied; no acceptance claim.
- Disposition rationale: No rejection or supersession recorded.
- Supersedes: None.
- Superseded by: None.

Record authenticity and the deciding authority's jurisdiction require independent review. Passing a record-schema check does not issue or authenticate an approval. The current record status is declared above; publication never grants decision authority.

[Decision register](README.md) · [Maintenance rules](../DOCUMENTATION_MIGRATION.md)
