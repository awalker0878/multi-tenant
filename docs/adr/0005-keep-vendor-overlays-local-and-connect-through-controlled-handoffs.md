# ADR-0005 — Keep vendor overlays local and connect through controlled handoffs

**Status:** Proposed — source-derived; organizational acceptance not recorded<br>
**Original decision identifiers:** `AD-03`<br>
**Source chapters:** [RA §5](../architecture/reference/5-physical-fabric-and-platform-attachment.md) · [RA §15](../architecture/reference/15-cross-vendor-realization-model.md) · [NET §1](../engineering/fabric/1-transport-routing-and-overlay-ownership.md) · [VND §6](../engineering/platform-realizations/6-portable-composite-and-migrated-service-choices.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The original source remains linked below; this ADR does not record an approval meeting or invent an acceptance date.

## Context

Matching encapsulation names do not establish interoperability or shared routing authority between native platforms.

## Decision recorded in the source

Keep each platform overlay under its native owner. Use qualified routed/security handoffs between platforms rather than importing vendor VNIs or route targets into a common overlay.

## Alternatives and limits recorded in the source

Direct overlay federation is a separately qualified interoperability architecture, not the baseline. Fabric EVPN remains an optional provider transport or physical-attachment mechanism.

## Consequences

Equivalent service and security outcomes do not require identical network objects. Cross-stack communication, portable deployment and migration remain distinct capabilities with distinct evidence.

## Engineering and implementation obligations

Document tunnel endpoint membership, underlay reachability, encapsulation budgets and the actual cross-vendor handoff. Do not infer route authority from a shared physical fabric.

## Requirement and code traceability

[OVL-001](../assurance/requirements.md#OVL-001) · [EVPN-001](../assurance/requirements.md#EVPN-001) · [EVPN-002](../assurance/requirements.md#EVPN-002) · [PORT-003](../assurance/requirements.md#PORT-003)

The following implementation areas are traceability targets, not proof that this decision has been qualified:

- [terraform/modules/nutanix-domain](../../terraform/modules/nutanix-domain)
- [terraform/modules/nsx-domain](../../terraform/modules/nsx-domain)
- [terraform/modules/openstack-domain](../../terraform/modules/openstack-domain)

Review [the implementation coverage map](../implementation/code-map.md) and the target-specific evidence before asserting completion. A local fixture or static source check does not establish deployed behaviour.

## Open decisions and acceptance

Actual multivendor interoperability, encapsulation behaviour and release-specific limitations need target qualification.

Accepting authority: **not recorded**.<br>
Acceptance evidence: **not supplied by this conversion**.<br>
Supersession: no new source supersession is asserted. Record a future change explicitly rather than silently editing an accepted decision.

---

[Decision register](README.md) · [Source and maintenance rules](../DOCUMENTATION_MIGRATION.md)
