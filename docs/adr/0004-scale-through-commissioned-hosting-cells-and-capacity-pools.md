# ADR-0004 — Scale through commissioned hosting cells and capacity pools

**Status:** Proposed<br>
**Accountable role:** Architecture authority and responsible infrastructure service owner<br>
**Scope:** Portable hosting reference pattern; site/service adoption remains unrecorded<br>
**Original decision identifiers:** `AD-02`<br>
**Source chapters:** [RA §3](../architecture/reference/3-system-context-and-physical-hosting-topology.md) · [RA §4](../architecture/reference/4-hosting-cells-resource-pools-and-failure-boundaries.md) · [RA §5](../architecture/reference/5-physical-fabric-and-platform-attachment.md) · [QUAL §3](../assurance/site-qualification/3-capacity-service-envelopes-and-growth-triggers.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The linked record is not made authoritative by rendering it. Real adoption needs the stated scope, actual authority and independently protected decision evidence.

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

Related implementation areas are traceability targets, not proof of complete implementation:

- [terraform/roots](../../terraform/roots)

Review [the assertion allocation](../implementation/assertion-allocation.md) for enforcement owner, location, evidence class and unimplemented dependencies.

## Open decisions and acceptance

Site inventory, failure groups, usable capacities and expansion lead times are not supplied by the reference example.

**Deciding authority:** Not recorded<br>
**Decision date:** Not recorded<br>
**Decision record:** Not supplied<br>
**Evidence references:** Not supplied<br>
**Decision rationale:** No lifecycle decision recorded<br>
**Superseded by:** None

Evidence references require owner verification; this repository does not authenticate a signatory or issue native operating authorization. Source-derived Proposed records remain proposed until their genuine decision is recorded. Accepted and rejected records are retained, not overwritten out of history.

---

[Decision register](README.md) · [Maintained design workspace](../current/README.md)
