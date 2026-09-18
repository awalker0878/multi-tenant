# ADR-0022 — Treat public access and egress as explicit service extensions

**Status:** Proposed — source-derived; organizational acceptance not recorded<br>
**Original decision identifiers:** No standalone source ID; extracted from the explicitly linked chapter decisions.<br>
**Source chapters:** [RA §8](../architecture/reference/8-zone-interfaces-routing-and-security-edge-topology.md) · [RA §9](../architecture/reference/9-shared-services-ingress-and-controlled-egress.md) · [SDP §1](../solutions/design-method/1-define-the-offered-service-before-choosing-the-build.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The original source remains linked below; this ADR does not record an approval meeting or invent an acceptance date.

## Context

A private circuit, floating address or external attachment can introduce access that bypasses the intended internal service boundary.

## Decision recorded in the source

Keep the base internal offer free of implicit public access and Internet egress. Public traffic uses an approved perimeter/PAZ service and a separately approved backend flow; partner and enterprise relationships retain named external authority.

## Alternatives and limits recorded in the source

Proxy, routed edge, translation and qualified combinations are possible explicit egress designs. NAT alone is not an access-control policy.

## Consequences

Exposure brings certificate, DNS, client-attribution, health-check, denial-of-service and operating dependencies. These are not enabled merely by setting a native public address.

## Engineering and implementation obligations

Record the external authority, ingress/egress service, TLS and backend trust, permitted flows, stateful reply and withdrawal behaviour before activation.

## Requirement and code traceability

[ING-001](../assurance/requirements.md#ING-001) · [ING-002](../assurance/requirements.md#ING-002) · [EGR-001](../assurance/requirements.md#EGR-001) · [EGR-002](../assurance/requirements.md#EGR-002) · [EXP-001](../assurance/requirements.md#EXP-001)

The following implementation areas are traceability targets, not proof that this decision has been qualified:

- [terraform/modules/openstack-domain](../../terraform/modules/openstack-domain)
- [terraform/modules/nsx-gateway-quarantine](../../terraform/modules/nsx-gateway-quarantine)

Review [the implementation coverage map](../implementation/code-map.md) and the target-specific evidence before asserting completion. A local fixture or static source check does not establish deployed behaviour.

## Open decisions and acceptance

A dedicated public-service solution document from the previously described RAD/TAD package is not present in the source bundle; this ADR uses only the available scope guidance.

Accepting authority: **not recorded**.<br>
Acceptance evidence: **not supplied by this conversion**.<br>
Supersession: no new source supersession is asserted. Record a future change explicitly rather than silently editing an accepted decision.

---

[Decision register](README.md) · [Source and maintenance rules](../DOCUMENTATION_MIGRATION.md)
