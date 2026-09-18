# ADR-0022 — Treat public access and egress as explicit service extensions

**Status:** Proposed<br>
**Accountable role:** Security-edge operations / Service owner<br>
**Scope:** Reusable reference decision; actual site adoption remains unissued<br>
**Record date:** 2026-09-17 (not an approval date)<br>
**Original decision identifiers:** Chapter-derived; no invented source decision identifier.<br>
**Source chapters:** [RA §8](../architecture/reference/8-zone-interfaces-routing-and-security-edge-topology.md) · [RA §9](../architecture/reference/9-shared-services-ingress-and-controlled-egress.md) · [SDP §1](../solutions/design-method/1-define-the-offered-service-before-choosing-the-build.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting.

## Context

A private circuit, floating address or external attachment can introduce access that bypasses the intended internal service boundary.

## Decision

Keep the base internal offer free of implicit public access and Internet egress. Public traffic uses an approved perimeter/PAZ service and a separately approved backend flow; partner and enterprise relationships retain named external authority.

## Alternatives and source limitations

Proxy, routed edge, translation and qualified combinations are possible explicit egress designs. NAT alone is not an access-control policy.

## Consequences

Exposure brings certificate, DNS, client-attribution, health-check, denial-of-service and operating dependencies. These are not enabled merely by setting a native public address.

## Engineering and implementation obligations

Record the external authority, ingress/egress service, TLS and backend trust, permitted flows, stateful reply and withdrawal behaviour before activation.

## Requirement and code traceability

[ING-001](../assurance/requirements.md#ING-001) · [ING-002](../assurance/requirements.md#ING-002) · [EGR-001](../assurance/requirements.md#EGR-001) · [EGR-002](../assurance/requirements.md#EGR-002) · [EXP-001](../assurance/requirements.md#EXP-001)

These are related implementation areas, not assertion-level evidence of native qualification:

- [terraform/modules/openstack-domain](../../terraform/modules/openstack-domain)
- [terraform/modules/nsx-gateway-quarantine](../../terraform/modules/nsx-gateway-quarantine)

[Requirement/assertion allocation](../assurance/implementation-allocation.md) records partial, external and unimplemented controls separately.

## Open work

A dedicated public-service solution document from the previously described RAD/TAD package is not present in the source bundle; this ADR uses only the available scope guidance.

## Decision lifecycle and authority

- Deciding authority: Not recorded.
- Decision date: Not recorded.
- Decision evidence: Not supplied; no acceptance claim.
- Disposition rationale: No rejection or supersession recorded.
- Supersedes: None.
- Superseded by: None.

Record authenticity and the deciding authority's jurisdiction require independent review. Passing a record-schema check does not issue or authenticate an approval. The current record status is declared above; publication never grants decision authority.

[Decision register](README.md) · [Maintenance rules](../DOCUMENTATION_MIGRATION.md)
