# ADR-0007 — Allocate isolated domain attachments and qualify sharing

**Status:** Proposed<br>
**Accountable role:** Network engineering / Security authority / Platform engineering<br>
**Scope:** Reusable reference decision; actual site adoption remains unissued<br>
**Record date:** 2026-09-17 (not an approval date)<br>
**Original decision identifiers:** `AD-05`<br>
**Source chapters:** [RA §5](../architecture/reference/5-physical-fabric-and-platform-attachment.md) · [RA §8](../architecture/reference/8-zone-interfaces-routing-and-security-edge-topology.md) · [NET §2](../engineering/fabric/2-isolated-attachment-units-and-bounded-capacity.md) · [NET §3](../engineering/fabric/3-worked-inter-zone-routing-and-enforcement-schedule.md) · [WD §5](../solutions/internal-protected-workload/5-dedicated-handoff-inventory-and-route-ownership.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting.

## Context

Separate VPC or router names do not prevent direct traffic between connected interfaces on a shared external segment.

## Decision

Allocate independently isolated domain-to-edge handoffs from controlled capacity. A shared attachment is eligible only after its neighbour, connected-route, gateway, translation and failure behaviour preserve the boundary.

## Alternatives and source limitations

The source permits a shared attachment or proxy arrangement only through explicit path and identity analysis. Dedicated isolated contexts are the default where that evidence is absent.

## Consequences

Isolation contexts are finite resources with their own ownership and reuse lifecycle. Logical attachments, service-facing handoffs, firewall contexts and physical interfaces must not be counted as interchangeable units.

## Engineering and implementation obligations

Maintain the handoff inventory, allowed prefixes, route ownership, source validation, return path, capacity and safe reuse conditions. Reject or queue allocations when accepted isolated capacity is exhausted.

## Requirement and code traceability

[EDGE-001](../assurance/requirements.md#EDGE-001) · [EDGE-002](../assurance/requirements.md#EDGE-002) · [ZIP-002](../assurance/requirements.md#ZIP-002) · [NUT-002](../assurance/requirements.md#NUT-002)

These are related implementation areas, not assertion-level evidence of native qualification:

- [terraform/modules/nutanix-route](../../terraform/modules/nutanix-route)
- [terraform/modules/nsx-route](../../terraform/modules/nsx-route)
- [terraform/modules/openstack-route](../../terraform/modules/openstack-route)

[Requirement/assertion allocation](../assurance/implementation-allocation.md) records partial, external and unimplemented controls separately.

## Open work

Actual attachment construction and isolation measurements remain native engineering work; the route modules do not create or qualify their attachments.

## Decision lifecycle and authority

- Deciding authority: Not recorded.
- Decision date: Not recorded.
- Decision evidence: Not supplied; no acceptance claim.
- Disposition rationale: No rejection or supersession recorded.
- Supersedes: None.
- Superseded by: None.

Record authenticity and the deciding authority's jurisdiction require independent review. Passing a record-schema check does not issue or authenticate an approval. The current record status is declared above; publication never grants decision authority.

[Decision register](README.md) · [Maintenance rules](../DOCUMENTATION_MIGRATION.md)
