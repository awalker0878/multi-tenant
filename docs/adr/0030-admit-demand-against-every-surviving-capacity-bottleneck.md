# ADR-0030 — Admit demand against every surviving-capacity bottleneck

**Status:** Proposed<br>
**Accountable role:** Architecture authority and responsible infrastructure service owner<br>
**Scope:** Portable hosting reference pattern; site/service adoption remains unrecorded<br>
**Original decision identifiers:** Chapter-derived; no standalone source ID asserted.<br>
**Source chapters:** [RA §4](../architecture/reference/4-hosting-cells-resource-pools-and-failure-boundaries.md) · [RA §26](../architecture/reference/26-operating-model-capacity-and-observability.md) · [QUAL §3](../assurance/site-qualification/3-capacity-service-envelopes-and-growth-triggers.md) · [SDP §5](../solutions/design-method/5-make-capacity-on-demand-and-exit-economically-explainable.md) · [WD §11](../solutions/internal-protected-workload/11-test-resource-capacity-and-mtu-accounting.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The linked record is not made authoritative by rendering it. Real adoption needs the stated scope, actual authority and independently protected decision evidence.

## Context

Free compute is insufficient when the required inspected edge, storage rebuild reserve, addresses, licences or operational dependency is exhausted.

## Decision recorded in the source

Evaluate accepted demand in each limiting unit against measured surviving qualified capacity minus operational reserve. Distinguish ordered, staged, commissioned, available, reserved and consumed capacity.

## Alternatives and limits recorded in the source

Queue the request or select another already eligible placement when the offer cannot be delivered. Do not weaken inspection or co-residency to make an allocation fit.

## Consequences

Quotas describe entitlement, not guaranteed aggregate capacity. Protection copies, provider overhead and temporary test probes consume resources separately from guest allocations.

## Engineering and implementation obligations

Maintain unit-specific calculations, workload/failure assumptions, capacity ownership, lead time and growth triggers. Explain service costs without inventing prices or savings.

## Requirement and code traceability

[CAP-001](../assurance/requirements.md#CAP-001) · [CAP-002](../assurance/requirements.md#CAP-002) · [CAP-003](../assurance/requirements.md#CAP-003) · [SVCM-001](../assurance/requirements.md#SVCM-001)

Related implementation areas are traceability targets, not proof of complete implementation:

- [reference/Portable_Hosting_Delivery_Kits_v1_1/02_Engineering/Engineering_Schedules.xlsx](../../reference/Portable_Hosting_Delivery_Kits_v1_1/02_Engineering/Engineering_Schedules.xlsx)

Review [the assertion allocation](../implementation/assertion-allocation.md) for enforcement owner, location, evidence class and unimplemented dependencies.

## Open decisions and acceptance

All actual inputs and measured safe limits remain unresolved; illustrative calculator values are not a purchased or qualified capacity promise.

**Deciding authority:** Not recorded<br>
**Decision date:** Not recorded<br>
**Decision record:** Not supplied<br>
**Evidence references:** Not supplied<br>
**Decision rationale:** No lifecycle decision recorded<br>
**Superseded by:** None

Evidence references require owner verification; this repository does not authenticate a signatory or issue native operating authorization. Source-derived Proposed records remain proposed until their genuine decision is recorded. Accepted and rejected records are retained, not overwritten out of history.

---

[Decision register](README.md) · [Maintained design workspace](../current/README.md)
