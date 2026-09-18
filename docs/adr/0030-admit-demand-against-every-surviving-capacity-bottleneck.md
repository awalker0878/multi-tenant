# ADR-0030 — Admit demand against every surviving-capacity bottleneck

**Status:** Proposed — source-derived; organizational acceptance not recorded<br>
**Original decision identifiers:** No standalone source ID; extracted from the explicitly linked chapter decisions.<br>
**Source chapters:** [RA §4](../architecture/reference/4-hosting-cells-resource-pools-and-failure-boundaries.md) · [RA §26](../architecture/reference/26-operating-model-capacity-and-observability.md) · [QUAL §3](../assurance/site-qualification/3-capacity-service-envelopes-and-growth-triggers.md) · [SDP §5](../solutions/design-method/5-make-capacity-on-demand-and-exit-economically-explainable.md) · [WD §11](../solutions/internal-protected-workload/11-test-resource-capacity-and-mtu-accounting.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The original source remains linked below; this ADR does not record an approval meeting or invent an acceptance date.

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

The following implementation areas are traceability targets, not proof that this decision has been qualified:

- [reference/Portable_Hosting_Delivery_Kits_v1_1/02_Engineering/Engineering_Schedules.xlsx](../../reference/Portable_Hosting_Delivery_Kits_v1_1/02_Engineering/Engineering_Schedules.xlsx)

Review [the implementation coverage map](../implementation/code-map.md) and the target-specific evidence before asserting completion. A local fixture or static source check does not establish deployed behaviour.

## Open decisions and acceptance

All actual inputs and measured safe limits remain unresolved; illustrative calculator values are not a purchased or qualified capacity promise.

Accepting authority: **not recorded**.<br>
Acceptance evidence: **not supplied by this conversion**.<br>
Supersession: no new source supersession is asserted. Record a future change explicitly rather than silently editing an accepted decision.

---

[Decision register](README.md) · [Source and maintenance rules](../DOCUMENTATION_MIGRATION.md)
