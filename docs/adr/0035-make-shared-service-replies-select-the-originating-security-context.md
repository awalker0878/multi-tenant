# ADR-0035 — Make shared-service replies select the originating security context

**Status:** Proposed<br>
**Accountable role:** Architecture authority and responsible infrastructure service owner<br>
**Scope:** Portable hosting reference pattern; site/service adoption remains unrecorded<br>
**Original decision identifiers:** `RD14-02`<br>
**Source chapters:** [WD §2](../solutions/internal-protected-workload/2-reference-decisions-and-infrastructure-boundaries.md) · [WD §5](../solutions/internal-protected-workload/5-dedicated-handoff-inventory-and-route-ownership.md) · [WD §6](../solutions/internal-protected-workload/6-worked-forwarding-and-return-route-schedule.md) · [WD §7](../solutions/internal-protected-workload/7-service-permissions-and-non-ip-storage-paths.md) · [NBD §3](../engineering/network-boundaries/3-make-service-replies-choose-the-originating-context.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The linked record is not made authoritative by rendering it. Real adoption needs the stated scope, actual authority and independently protected decision evidence.

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

Related implementation areas are traceability targets, not proof of complete implementation:

- [lab/run_namespace_lab.py](../../lab/run_namespace_lab.py)
- [tools/route_audit.py](../../tools/route_audit.py)

Review [the assertion allocation](../implementation/assertion-allocation.md) for enforcement owner, location, evidence class and unimplemented dependencies.

## Open decisions and acceptance

Native service/gateway configuration and real endpoint no-transit/source-validation controls still require the chosen implementation.

**Deciding authority:** Not recorded<br>
**Decision date:** Not recorded<br>
**Decision record:** Not supplied<br>
**Evidence references:** Not supplied<br>
**Decision rationale:** No lifecycle decision recorded<br>
**Superseded by:** None

Evidence references require owner verification; this repository does not authenticate a signatory or issue native operating authorization. Source-derived Proposed records remain proposed until their genuine decision is recorded. Accepted and rejected records are retained, not overwritten out of history.

---

[Decision register](README.md) · [Maintained design workspace](../current/README.md)
