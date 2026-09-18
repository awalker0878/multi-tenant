# ADR-0022 — Treat public access and egress as explicit service extensions

**Status:** Proposed<br>
**Accountable role:** Architecture authority and responsible infrastructure service owner<br>
**Scope:** Portable hosting reference pattern; site/service adoption remains unrecorded<br>
**Original decision identifiers:** Chapter-derived; no standalone source ID asserted.<br>
**Source chapters:** [RA §8](../architecture/reference/8-zone-interfaces-routing-and-security-edge-topology.md) · [RA §9](../architecture/reference/9-shared-services-ingress-and-controlled-egress.md) · [SDP §1](../solutions/design-method/1-define-the-offered-service-before-choosing-the-build.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The linked record is not made authoritative by rendering it. Real adoption needs the stated scope, actual authority and independently protected decision evidence.

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

Related implementation areas are traceability targets, not proof of complete implementation:

- [terraform/modules/openstack-domain](../../terraform/modules/openstack-domain)
- [terraform/modules/nsx-gateway-quarantine](../../terraform/modules/nsx-gateway-quarantine)

Review [the assertion allocation](../implementation/assertion-allocation.md) for enforcement owner, location, evidence class and unimplemented dependencies.

## Open decisions and acceptance

A dedicated public-service solution document from the previously described RAD/TAD package is not present in the source bundle; this ADR uses only the available scope guidance.

**Deciding authority:** Not recorded<br>
**Decision date:** Not recorded<br>
**Decision record:** Not supplied<br>
**Evidence references:** Not supplied<br>
**Decision rationale:** No lifecycle decision recorded<br>
**Superseded by:** None

Evidence references require owner verification; this repository does not authenticate a signatory or issue native operating authorization. Source-derived Proposed records remain proposed until their genuine decision is recorded. Accepted and rejected records are retained, not overwritten out of history.

---

[Decision register](README.md) · [Maintained design workspace](../current/README.md)
