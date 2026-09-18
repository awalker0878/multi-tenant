# ADR-0006 — Use an explicit governed ZIP for inter-domain trust transitions

**Status:** Proposed — source-derived; organizational acceptance not recorded<br>
**Original decision identifiers:** `AD-04`, `DEV-ADR-01`, `RD14-01`<br>
**Source chapters:** [RA §8](../architecture/reference/8-zone-interfaces-routing-and-security-edge-topology.md) · [RA §29](../architecture/reference/29-architecture-decisions-and-alternatives.md) · [SDP §3](../solutions/design-method/3-develop-a-boundary-architecture-decision.md) · [WD §2](../solutions/internal-protected-workload/2-reference-decisions-and-infrastructure-boundaries.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The original source remains linked below; this ADR does not record an approval meeting or invent an acceptance date.

## Context

Native domain routing can create a path before a downstream firewall ever evaluates traffic. The required boundary includes policy, authority, attribution, inspection where required and failure behaviour.

## Decision recorded in the source

Use the reference routed stateful security-edge service with independent logical contexts and explicit adjacent-domain authority. No unrestricted general-purpose transit replaces that boundary.

## Alternatives and limits recorded in the source

The service-design example compares a provider routed edge, a qualified native/distributed boundary and common unrestricted transit. It retains the explicit edge, conditionally permits a complete native/distributed equivalent, and rejects unrestricted transit for the base service.

## Consequences

The edge consumes inspected throughput, session and logging capacity. A physical security cluster may host several pairwise relationships; the logical relationship is not a physical two-port or appliance-count rule.

## Engineering and implementation obligations

Trace forward, reverse, same-host, connected-route and failed-edge paths. Identify every required ZIP function and the component and authority that implement it.

## Requirement and code traceability

[ARCH-003](../assurance/requirements.md#ARCH-003) · [ZIP-001](../assurance/requirements.md#ZIP-001) · [ZIP-002](../assurance/requirements.md#ZIP-002) · [ZIP-003](../assurance/requirements.md#ZIP-003) · [ZIP-006](../assurance/requirements.md#ZIP-006) · [ZIP-007](../assurance/requirements.md#ZIP-007)

The following implementation areas are traceability targets, not proof that this decision has been qualified:

- [terraform/modules/nsx-gateway-quarantine](../../terraform/modules/nsx-gateway-quarantine)
- [lab/run_namespace_lab.py](../../lab/run_namespace_lab.py)

Review [the implementation coverage map](../implementation/code-map.md) and the target-specific evidence before asserting completion. A local fixture or static source check does not establish deployed behaviour.

## Open decisions and acceptance

The selected native firewall/context implementation, complete inspection functions and HA qualification remain open. A quarantine policy or Linux fixture is not a full ZIP.

Accepting authority: **not recorded**.<br>
Acceptance evidence: **not supplied by this conversion**.<br>
Supersession: no new source supersession is asserted. Record a future change explicitly rather than silently editing an accepted decision.

---

[Decision register](README.md) · [Source and maintenance rules](../DOCUMENTATION_MIGRATION.md)
