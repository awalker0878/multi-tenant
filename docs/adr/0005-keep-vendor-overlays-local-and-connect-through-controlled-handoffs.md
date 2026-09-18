# ADR-0005 — Keep vendor overlays local and connect through controlled handoffs

**Status:** Proposed<br>
**Accountable role:** Platform engineering / Network engineering / Architecture authority<br>
**Scope:** Reusable reference decision; actual site adoption remains unissued<br>
**Record date:** 2026-09-17 (not an approval date)<br>
**Original decision identifiers:** `AD-03`<br>
**Source chapters:** [RA §5](../architecture/reference/5-physical-fabric-and-platform-attachment.md) · [RA §15](../architecture/reference/15-cross-vendor-realization-model.md) · [NET §1](../engineering/fabric/1-transport-routing-and-overlay-ownership.md) · [VND §6](../engineering/platform-realizations/6-portable-composite-and-migrated-service-choices.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting.

## Context

Matching encapsulation names do not establish interoperability or shared routing authority between native platforms.

## Decision

Keep each platform overlay under its native owner. Use qualified routed/security handoffs between platforms rather than importing vendor VNIs or route targets into a common overlay.

## Alternatives and source limitations

Direct overlay federation is a separately qualified interoperability architecture, not the baseline. Fabric EVPN remains an optional provider transport or physical-attachment mechanism.

## Consequences

Equivalent service and security outcomes do not require identical network objects. Cross-stack communication, portable deployment and migration remain distinct capabilities with distinct evidence.

## Engineering and implementation obligations

Document tunnel endpoint membership, underlay reachability, encapsulation budgets and the actual cross-vendor handoff. Do not infer route authority from a shared physical fabric.

## Requirement and code traceability

[OVL-001](../assurance/requirements.md#OVL-001) · [EVPN-001](../assurance/requirements.md#EVPN-001) · [EVPN-002](../assurance/requirements.md#EVPN-002) · [PORT-003](../assurance/requirements.md#PORT-003)

These are related implementation areas, not assertion-level evidence of native qualification:

- [terraform/modules/nutanix-domain](../../terraform/modules/nutanix-domain)
- [terraform/modules/nsx-domain](../../terraform/modules/nsx-domain)
- [terraform/modules/openstack-domain](../../terraform/modules/openstack-domain)

[Requirement/assertion allocation](../assurance/implementation-allocation.md) records partial, external and unimplemented controls separately.

## Open work

Actual multivendor interoperability, encapsulation behaviour and release-specific limitations need target qualification.

## Decision lifecycle and authority

- Deciding authority: Not recorded.
- Decision date: Not recorded.
- Decision evidence: Not supplied; no acceptance claim.
- Disposition rationale: No rejection or supersession recorded.
- Supersedes: None.
- Superseded by: None.

Record authenticity and the deciding authority's jurisdiction require independent review. Passing a record-schema check does not issue or authenticate an approval. The current record status is declared above; publication never grants decision authority.

[Decision register](README.md) · [Maintenance rules](../DOCUMENTATION_MIGRATION.md)
