# ADR-0004 — Scale through commissioned hosting cells and capacity pools

**Status:** Proposed<br>
**Accountable role:** Architecture authority / Network engineering / Capacity management<br>
**Scope:** Reusable reference decision; actual site adoption remains unissued<br>
**Record date:** 2026-09-17 (not an approval date)<br>
**Original decision identifiers:** `AD-02`<br>
**Source chapters:** [RA §3](../architecture/reference/3-system-context-and-physical-hosting-topology.md) · [RA §4](../architecture/reference/4-hosting-cells-resource-pools-and-failure-boundaries.md) · [RA §5](../architecture/reference/5-physical-fabric-and-platform-attachment.md) · [QUAL §3](../assurance/site-qualification/3-capacity-service-envelopes-and-growth-triggers.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting.

## Context

Tenant growth should not routinely force physical topology changes. A hosting cell groups qualified capacity, release control and disclosed failure dependencies; it is not a synonym for a vendor cluster or Nova cell.

## Decision

Commission transport, eligible compute/storage pools, security capacity and isolated attachments before routine allocations. Grow those foundations through separately owned infrastructure changes.

## Alternatives and source limitations

A smaller consolidated site is a documented variation only when its isolation and recovery design supports the offered scope.

## Consequences

Precommissioning requires reserve capacity and forecasting. An installed server without accepted storage, edge capacity, addressing, support or operational ownership is not allocatable service capacity.

## Engineering and implementation obligations

Record the cell boundary, bottlenecks, attachment slots, measured surviving capacity and expansion trigger. Classify a physical attachment or new host pool as a foundation change.

## Requirement and code traceability

[ARCH-002](../assurance/requirements.md#ARCH-002) · [FAB-001](../assurance/requirements.md#FAB-001) · [CAP-002](../assurance/requirements.md#CAP-002) · [SVCM-002](../assurance/requirements.md#SVCM-002)

These are related implementation areas, not assertion-level evidence of native qualification:

- [terraform/roots](../../terraform/roots)

[Requirement/assertion allocation](../assurance/implementation-allocation.md) records partial, external and unimplemented controls separately.

## Open work

Site inventory, failure groups, usable capacities and expansion lead times are not supplied by the reference example.

## Decision lifecycle and authority

- Deciding authority: Not recorded.
- Decision date: Not recorded.
- Decision evidence: Not supplied; no acceptance claim.
- Disposition rationale: No rejection or supersession recorded.
- Supersedes: None.
- Superseded by: None.

Record authenticity and the deciding authority's jurisdiction require independent review. Passing a record-schema check does not issue or authenticate an approval. The current record status is declared above; publication never grants decision authority.

[Decision register](README.md) · [Maintenance rules](../DOCUMENTATION_MIGRATION.md)
