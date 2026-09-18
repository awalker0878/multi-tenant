# ADR-0004 — Scale through commissioned hosting cells and capacity pools

**Status:** Proposed — source-derived; organizational acceptance not recorded<br>
**Original decision identifiers:** `AD-02`<br>
**Source chapters:** [RA §3](../architecture/reference/3-system-context-and-physical-hosting-topology.md) · [RA §4](../architecture/reference/4-hosting-cells-resource-pools-and-failure-boundaries.md) · [RA §5](../architecture/reference/5-physical-fabric-and-platform-attachment.md) · [QUAL §3](../assurance/site-qualification/3-capacity-service-envelopes-and-growth-triggers.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The original source remains linked below; this ADR does not record an approval meeting or invent an acceptance date.

## Context

Tenant growth should not routinely force physical topology changes. A hosting cell groups qualified capacity, release control and disclosed failure dependencies; it is not a synonym for a vendor cluster or Nova cell.

## Decision recorded in the source

Commission transport, eligible compute/storage pools, security capacity and isolated attachments before routine allocations. Grow those foundations through separately owned infrastructure changes.

## Alternatives and limits recorded in the source

A smaller consolidated site is a documented variation only when its isolation and recovery design supports the offered scope.

## Consequences

Precommissioning requires reserve capacity and forecasting. An installed server without accepted storage, edge capacity, addressing, support or operational ownership is not allocatable service capacity.

## Engineering and implementation obligations

Record the cell boundary, bottlenecks, attachment slots, measured surviving capacity and expansion trigger. Classify a physical attachment or new host pool as a foundation change.

## Requirement and code traceability

[ARCH-002](../assurance/requirements.md#ARCH-002) · [FAB-001](../assurance/requirements.md#FAB-001) · [CAP-002](../assurance/requirements.md#CAP-002) · [SVCM-002](../assurance/requirements.md#SVCM-002)

The following implementation areas are traceability targets, not proof that this decision has been qualified:

- [terraform/roots](../../terraform/roots)

Review [the implementation coverage map](../implementation/code-map.md) and the target-specific evidence before asserting completion. A local fixture or static source check does not establish deployed behaviour.

## Open decisions and acceptance

Site inventory, failure groups, usable capacities and expansion lead times are not supplied by the reference example.

Accepting authority: **not recorded**.<br>
Acceptance evidence: **not supplied by this conversion**.<br>
Supersession: no new source supersession is asserted. Record a future change explicitly rather than silently editing an accepted decision.

---

[Decision register](README.md) · [Source and maintenance rules](../DOCUMENTATION_MIGRATION.md)
