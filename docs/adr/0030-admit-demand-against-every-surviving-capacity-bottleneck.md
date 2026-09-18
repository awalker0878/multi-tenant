# ADR-0030 — Admit demand against every surviving-capacity bottleneck

**Status:** Proposed<br>
**Accountable role:** Capacity management / Service management / Service owner<br>
**Scope:** Reusable reference decision; actual site adoption remains unissued<br>
**Record date:** 2026-09-17 (not an approval date)<br>
**Original decision identifiers:** Chapter-derived; no invented source decision identifier.<br>
**Source chapters:** [RA §4](../architecture/reference/4-hosting-cells-resource-pools-and-failure-boundaries.md) · [RA §26](../architecture/reference/26-operating-model-capacity-and-observability.md) · [QUAL §3](../assurance/site-qualification/3-capacity-service-envelopes-and-growth-triggers.md) · [SDP §5](../solutions/design-method/5-make-capacity-on-demand-and-exit-economically-explainable.md) · [WD §11](../solutions/internal-protected-workload/11-test-resource-capacity-and-mtu-accounting.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting.

## Context

Free compute is insufficient when the required inspected edge, storage rebuild reserve, addresses, licences or operational dependency is exhausted.

## Decision

Evaluate accepted demand in each limiting unit against measured surviving qualified capacity minus operational reserve. Distinguish ordered, staged, commissioned, available, reserved and consumed capacity.

## Alternatives and source limitations

Queue the request or select another already eligible placement when the offer cannot be delivered. Do not weaken inspection or co-residency to make an allocation fit.

## Consequences

Quotas describe entitlement, not guaranteed aggregate capacity. Protection copies, provider overhead and temporary test probes consume resources separately from guest allocations.

## Engineering and implementation obligations

Maintain unit-specific calculations, workload/failure assumptions, capacity ownership, lead time and growth triggers. Explain service costs without inventing prices or savings.

## Requirement and code traceability

[CAP-001](../assurance/requirements.md#CAP-001) · [CAP-002](../assurance/requirements.md#CAP-002) · [CAP-003](../assurance/requirements.md#CAP-003) · [SVCM-001](../assurance/requirements.md#SVCM-001)

These are related implementation areas, not assertion-level evidence of native qualification:

- [reference/Portable_Hosting_Delivery_Kits_v1_1/02_Engineering/Engineering_Schedules.xlsx](../../reference/Portable_Hosting_Delivery_Kits_v1_1/02_Engineering/Engineering_Schedules.xlsx)

[Requirement/assertion allocation](../assurance/implementation-allocation.md) records partial, external and unimplemented controls separately.

## Open work

All actual inputs and measured safe limits remain unresolved; illustrative calculator values are not a purchased or qualified capacity promise.

## Decision lifecycle and authority

- Deciding authority: Not recorded.
- Decision date: Not recorded.
- Decision evidence: Not supplied; no acceptance claim.
- Disposition rationale: No rejection or supersession recorded.
- Supersedes: None.
- Superseded by: None.

Record authenticity and the deciding authority's jurisdiction require independent review. Passing a record-schema check does not issue or authenticate an approval. The current record status is declared above; publication never grants decision authority.

[Decision register](README.md) · [Maintenance rules](../DOCUMENTATION_MIGRATION.md)
