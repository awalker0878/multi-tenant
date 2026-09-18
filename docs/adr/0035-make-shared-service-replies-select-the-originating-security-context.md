# ADR-0035 — Make shared-service replies select the originating security context

**Status:** Proposed — source-derived; organizational acceptance not recorded<br>
**Original decision identifiers:** `RD14-02`<br>
**Source chapters:** [WD §2](../solutions/internal-protected-workload/2-reference-decisions-and-infrastructure-boundaries.md) · [WD §5](../solutions/internal-protected-workload/5-dedicated-handoff-inventory-and-route-ownership.md) · [WD §6](../solutions/internal-protected-workload/6-worked-forwarding-and-return-route-schedule.md) · [WD §7](../solutions/internal-protected-workload/7-service-permissions-and-non-ip-storage-paths.md) · [NBD §3](../engineering/network-boundaries/3-make-service-replies-choose-the-originating-context.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The original source remains linked below; this ADR does not record an approval meeting or invent an acceptance date.

## Context

Filtering traffic on the way into a shared service is insufficient when replies can use another tenant's path or a compromised service can become a transit router.

## Decision recorded in the source

Use the worked design's dedicated tenant-to-service handoffs and origin-specific service-side return routes. Keep provider service endpoints separate from tenant gateways and prohibit general-purpose transit through service hosts.

## Alternatives and limits recorded in the source

A shared attachment, frontend or proxy design requires its own path, identity, management and failure analysis. The example does not choose a universal production routing product.

## Consequences

The service backend remains a disclosed shared availability and compromise dependency. Per-tenant route ownership, source validation and resource authorization must persist at that sharing point.

## Engineering and implementation obligations

Record the actual initiating client, endpoint, forward/reply route chain, authorised service and unavailable-next-hop behaviour. Exercise a missing reply route without borrowing another tenant's default.

## Requirement and code traceability

[SVC-001](../assurance/requirements.md#SVC-001) · [SVC-003](../assurance/requirements.md#SVC-003) · [EDGE-002](../assurance/requirements.md#EDGE-002) · [RTE-004](../assurance/requirements.md#RTE-004)

The following implementation areas are traceability targets, not proof that this decision has been qualified:

- [lab/run_namespace_lab.py](../../lab/run_namespace_lab.py)
- [tools/route_audit.py](../../tools/route_audit.py)

Review [the implementation coverage map](../implementation/code-map.md) and the target-specific evidence before asserting completion. A local fixture or static source check does not establish deployed behaviour.

## Open decisions and acceptance

Native service/gateway configuration and real endpoint no-transit/source-validation controls still require the chosen implementation.

Accepting authority: **not recorded**.<br>
Acceptance evidence: **not supplied by this conversion**.<br>
Supersession: no new source supersession is asserted. Record a future change explicitly rather than silently editing an accepted decision.

---

[Decision register](README.md) · [Source and maintenance rules](../DOCUMENTATION_MIGRATION.md)
