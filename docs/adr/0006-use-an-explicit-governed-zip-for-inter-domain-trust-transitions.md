# ADR-0006 — Use an explicit governed ZIP for inter-domain trust transitions

**Status:** Proposed<br>
**Accountable role:** Architecture authority / Security-edge operations / Security authority<br>
**Scope:** Reusable reference decision; actual site adoption remains unissued<br>
**Record date:** 2026-09-17 (not an approval date)<br>
**Original decision identifiers:** `AD-04`, `DEV-ADR-01`, `RD14-01`<br>
**Source chapters:** [RA §8](../architecture/reference/8-zone-interfaces-routing-and-security-edge-topology.md) · [RA §29](../architecture/reference/29-architecture-decisions-and-alternatives.md) · [SDP §3](../solutions/design-method/3-develop-a-boundary-architecture-decision.md) · [WD §2](../solutions/internal-protected-workload/2-reference-decisions-and-infrastructure-boundaries.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting.

## Context

Native domain routing can create a path before a downstream firewall ever evaluates traffic. The required boundary includes policy, authority, attribution, inspection where required and failure behaviour.

## Decision

Use the reference routed stateful security-edge service with independent logical contexts and explicit adjacent-domain authority. No unrestricted general-purpose transit replaces that boundary.

## Alternatives and source limitations

The service-design example compares a provider routed edge, a qualified native/distributed boundary and common unrestricted transit. It retains the explicit edge, conditionally permits a complete native/distributed equivalent, and rejects unrestricted transit for the base service.

## Consequences

The edge consumes inspected throughput, session and logging capacity. A physical security cluster may host several pairwise relationships; the logical relationship is not a physical two-port or appliance-count rule.

## Engineering and implementation obligations

Trace forward, reverse, same-host, connected-route and failed-edge paths. Identify every required ZIP function and the component and authority that implement it.

## Requirement and code traceability

[ARCH-003](../assurance/requirements.md#ARCH-003) · [ZIP-001](../assurance/requirements.md#ZIP-001) · [ZIP-002](../assurance/requirements.md#ZIP-002) · [ZIP-003](../assurance/requirements.md#ZIP-003) · [ZIP-006](../assurance/requirements.md#ZIP-006) · [ZIP-007](../assurance/requirements.md#ZIP-007)

These are related implementation areas, not assertion-level evidence of native qualification:

- [terraform/modules/nsx-gateway-quarantine](../../terraform/modules/nsx-gateway-quarantine)
- [lab/run_namespace_lab.py](../../lab/run_namespace_lab.py)

[Requirement/assertion allocation](../assurance/implementation-allocation.md) records partial, external and unimplemented controls separately.

## Open work

The selected native firewall/context implementation, complete inspection functions and HA qualification remain open. A quarantine policy or Linux fixture is not a full ZIP.

## Decision lifecycle and authority

- Deciding authority: Not recorded.
- Decision date: Not recorded.
- Decision evidence: Not supplied; no acceptance claim.
- Disposition rationale: No rejection or supersession recorded.
- Supersedes: None.
- Superseded by: None.

Record authenticity and the deciding authority's jurisdiction require independent review. Passing a record-schema check does not issue or authenticate an approval. The current record status is declared above; publication never grants decision authority.

[Decision register](README.md) · [Maintenance rules](../DOCUMENTATION_MIGRATION.md)
