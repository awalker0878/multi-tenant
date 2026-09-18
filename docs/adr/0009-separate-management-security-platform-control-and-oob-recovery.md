# ADR-0009 — Separate management security, platform control and OOB recovery

**Status:** Proposed<br>
**Accountable role:** Management infrastructure and security architecture owner<br>
**Scope:** Portable hosting reference pattern; site/service adoption remains unrecorded<br>
**Original decision identifiers:** `AD-07`<br>
**Source chapters:** [RA §6](../architecture/reference/6-management-platform-control-and-out-of-band-access.md) · [NET §6](../engineering/fabric/6-management-paths-and-interface-handover.md) · [SVC §3](../architecture/shared-services/3-identity-certificates-keys-and-independent-recovery.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The linked record is not made authoritative by rendering it. Real adoption needs the stated scope, actual authority and independently protected decision evidence.

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

Related implementation areas are traceability targets, not proof of complete implementation:

- [tools/nsx_observe.py](../../tools/nsx_observe.py)
- [tools/nutanix_observe.py](../../tools/nutanix_observe.py)
- [tools/neutron_observe.py](../../tools/neutron_observe.py)

Review [the assertion allocation](../implementation/assertion-allocation.md) for enforcement owner, location, evidence class and unimplemented dependencies.

## Open decisions and acceptance

Management/OOB independence, accepted principals, real access paths and break-glass exercises require the actual site.

**Deciding authority:** Not recorded<br>
**Decision date:** Not recorded<br>
**Decision record:** Not supplied<br>
**Evidence references:** Not supplied<br>
**Decision rationale:** No lifecycle decision recorded<br>
**Superseded by:** None

Evidence references require owner verification; this repository does not authenticate a signatory or issue native operating authorization. Source-derived Proposed records remain proposed until their genuine decision is recorded. Accepted and rejected records are retained, not overwritten out of history.

---

[Decision register](README.md) · [Maintained design workspace](../current/README.md)
