# ADR-0005 — Keep vendor overlays local and connect through controlled handoffs

**Status:** Proposed<br>
**Accountable role:** Architecture authority and responsible infrastructure service owner<br>
**Scope:** Portable hosting reference pattern; site/service adoption remains unrecorded<br>
**Original decision identifiers:** `AD-03`<br>
**Source chapters:** [RA §5](../architecture/reference/5-physical-fabric-and-platform-attachment.md) · [RA §15](../architecture/reference/15-cross-vendor-realization-model.md) · [NET §1](../engineering/fabric/1-transport-routing-and-overlay-ownership.md) · [VND §6](../engineering/platform-realizations/6-portable-composite-and-migrated-service-choices.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The linked record is not made authoritative by rendering it. Real adoption needs the stated scope, actual authority and independently protected decision evidence.

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

Related implementation areas are traceability targets, not proof of complete implementation:

- [terraform/modules/nutanix-domain](../../terraform/modules/nutanix-domain)
- [terraform/modules/nsx-domain](../../terraform/modules/nsx-domain)
- [terraform/modules/openstack-domain](../../terraform/modules/openstack-domain)

Review [the assertion allocation](../implementation/assertion-allocation.md) for enforcement owner, location, evidence class and unimplemented dependencies.

## Open decisions and acceptance

Actual multivendor interoperability, encapsulation behaviour and release-specific limitations need target qualification.

**Deciding authority:** Not recorded<br>
**Decision date:** Not recorded<br>
**Decision record:** Not supplied<br>
**Evidence references:** Not supplied<br>
**Decision rationale:** No lifecycle decision recorded<br>
**Superseded by:** None

Evidence references require owner verification; this repository does not authenticate a signatory or issue native operating authorization. Source-derived Proposed records remain proposed until their genuine decision is recorded. Accepted and rejected records are retained, not overwritten out of history.

---

[Decision register](README.md) · [Maintained design workspace](../current/README.md)
