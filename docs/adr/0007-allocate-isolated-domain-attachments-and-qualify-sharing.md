# ADR-0007 — Allocate isolated domain attachments and qualify sharing

**Status:** Proposed<br>
**Accountable role:** Architecture authority and responsible infrastructure service owner<br>
**Scope:** Portable hosting reference pattern; site/service adoption remains unrecorded<br>
**Original decision identifiers:** `AD-05`<br>
**Source chapters:** [RA §5](../architecture/reference/5-physical-fabric-and-platform-attachment.md) · [RA §8](../architecture/reference/8-zone-interfaces-routing-and-security-edge-topology.md) · [NET §2](../engineering/fabric/2-isolated-attachment-units-and-bounded-capacity.md) · [NET §3](../engineering/fabric/3-worked-inter-zone-routing-and-enforcement-schedule.md) · [WD §5](../solutions/internal-protected-workload/5-dedicated-handoff-inventory-and-route-ownership.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The linked record is not made authoritative by rendering it. Real adoption needs the stated scope, actual authority and independently protected decision evidence.

## Context

Separate VPC or router names do not prevent direct traffic between connected interfaces on a shared external segment.

## Decision recorded in the source

Allocate independently isolated domain-to-edge handoffs from controlled capacity. A shared attachment is eligible only after its neighbour, connected-route, gateway, translation and failure behaviour preserve the boundary.

## Alternatives and limits recorded in the source

The source permits a shared attachment or proxy arrangement only through explicit path and identity analysis. Dedicated isolated contexts are the default where that evidence is absent.

## Consequences

Isolation contexts are finite resources with their own ownership and reuse lifecycle. Logical attachments, service-facing handoffs, firewall contexts and physical interfaces must not be counted as interchangeable units.

## Engineering and implementation obligations

Maintain the handoff inventory, allowed prefixes, route ownership, source validation, return path, capacity and safe reuse conditions. Reject or queue allocations when accepted isolated capacity is exhausted.

## Requirement and code traceability

[EDGE-001](../assurance/requirements.md#EDGE-001) · [EDGE-002](../assurance/requirements.md#EDGE-002) · [ZIP-002](../assurance/requirements.md#ZIP-002) · [NUT-002](../assurance/requirements.md#NUT-002)

Related implementation areas are traceability targets, not proof of complete implementation:

- [terraform/modules/nutanix-route](../../terraform/modules/nutanix-route)
- [terraform/modules/nsx-route](../../terraform/modules/nsx-route)
- [terraform/modules/openstack-route](../../terraform/modules/openstack-route)

Review [the assertion allocation](../implementation/assertion-allocation.md) for enforcement owner, location, evidence class and unimplemented dependencies.

## Open decisions and acceptance

Actual attachment construction and isolation measurements remain native engineering work; the route modules do not create or qualify their attachments.

**Deciding authority:** Not recorded<br>
**Decision date:** Not recorded<br>
**Decision record:** Not supplied<br>
**Evidence references:** Not supplied<br>
**Decision rationale:** No lifecycle decision recorded<br>
**Superseded by:** None

Evidence references require owner verification; this repository does not authenticate a signatory or issue native operating authorization. Source-derived Proposed records remain proposed until their genuine decision is recorded. Accepted and rejected records are retained, not overwritten out of history.

---

[Decision register](README.md) · [Maintained design workspace](../current/README.md)
