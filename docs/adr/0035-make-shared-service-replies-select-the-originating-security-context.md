# ADR-0035 — Make shared-service replies select the originating security context

**Status:** Proposed<br>
**Accountable role:** Service operations / Security authority / Network engineering<br>
**Scope:** Reusable reference decision; actual site adoption remains unissued<br>
**Record date:** 2026-09-17 (not an approval date)<br>
**Original decision identifiers:** `RD14-02`<br>
**Source chapters:** [WD §2](../solutions/internal-protected-workload/2-reference-decisions-and-infrastructure-boundaries.md) · [WD §5](../solutions/internal-protected-workload/5-dedicated-handoff-inventory-and-route-ownership.md) · [WD §6](../solutions/internal-protected-workload/6-worked-forwarding-and-return-route-schedule.md) · [WD §7](../solutions/internal-protected-workload/7-service-permissions-and-non-ip-storage-paths.md) · [NBD §3](../engineering/network-boundaries/3-make-service-replies-choose-the-originating-context.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting.

## Context

Filtering traffic on the way into a shared service is insufficient when replies can use another tenant's path or a compromised service can become a transit router.

## Decision

Use the worked design's dedicated tenant-to-service handoffs and origin-specific service-side return routes. Keep provider service endpoints separate from tenant gateways and prohibit general-purpose transit through service hosts.

## Alternatives and source limitations

A shared attachment, frontend or proxy design requires its own path, identity, management and failure analysis. The example does not choose a universal production routing product.

## Consequences

The service backend remains a disclosed shared availability and compromise dependency. Per-tenant route ownership, source validation and resource authorization must persist at that sharing point.

## Engineering and implementation obligations

Record the actual initiating client, endpoint, forward/reply route chain, authorised service and unavailable-next-hop behaviour. Exercise a missing reply route without borrowing another tenant's default.

## Requirement and code traceability

[SVC-001](../assurance/requirements.md#SVC-001) · [SVC-003](../assurance/requirements.md#SVC-003) · [EDGE-002](../assurance/requirements.md#EDGE-002) · [RTE-004](../assurance/requirements.md#RTE-004)

These are related implementation areas, not assertion-level evidence of native qualification:

- [lab/run_namespace_lab.py](../../lab/run_namespace_lab.py)
- [tools/route_audit.py](../../tools/route_audit.py)

[Requirement/assertion allocation](../assurance/implementation-allocation.md) records partial, external and unimplemented controls separately.

## Open work

Native service/gateway configuration and real endpoint no-transit/source-validation controls still require the chosen implementation.

## Decision lifecycle and authority

- Deciding authority: Not recorded.
- Decision date: Not recorded.
- Decision evidence: Not supplied; no acceptance claim.
- Disposition rationale: No rejection or supersession recorded.
- Supersedes: None.
- Superseded by: None.

Record authenticity and the deciding authority's jurisdiction require independent review. Passing a record-schema check does not issue or authenticate an approval. The current record status is declared above; publication never grants decision authority.

[Decision register](README.md) · [Maintenance rules](../DOCUMENTATION_MIGRATION.md)
