# SOL-M02 — Public service hosting design profile

**Version:** 0.1 · **Status:** Proposed · **Accountable role:** Security and hosting solution architects.

## Scope and authority

New design profile for a proposed PAZ/OZ/RZ extension; not the missing worked public-service solution and not an amendment enabling the internal fixture.

This is a newly authored maintained Markdown record, not a reconstruction of an unavailable Word original. Its creation date is not an acceptance date. Source basis: [RA §9](../architecture/reference/9-shared-services-ingress-and-controlled-egress.md) · [RA §7](../architecture/reference/7-tenant-environments-and-security-domain-placement.md) · [NET §2](../engineering/fabric/2-isolated-attachment-units-and-bounded-capacity.md).

## Design content

Public exposure is a separate approved service. External reachability terminates at the selected PAZ ingress function and permitted external boundary, with distinct backend permission to OZ and protected data access to RZ. Internal domains do not receive direct external attachments simply to publish an endpoint. Return paths and any address translation must preserve control and attribution.

Choose actual ingress/WAF/load-balancer functions, TLS termination/re-encryption, certificate and DNS ownership, trusted client attribution, health probes, upstream threat capacity and inspection. Each is a design decision requiring a supported implementation, not a default product recommendation. Administrative endpoints are excluded from the consumption path.

Document admission and withdrawal of exposure, backend failure behaviour, certificate/key loss and replacement, inspection capacity under node failure, log dependency loss, and recovery/failback. Egress is separately scoped; an inbound approval does not authorize arbitrary outbound communication.

## Engineering and implementation handoff

Produce the actual site LLD and interface agreements before a native implementation. Allocate each required upstream/ingress/backend/data control to its owner. Keep the base internal fixture disabled externally and build an explicitly isolated qualification scope for the extension.

## Acceptance and open work

This replaces no unavailable source by claim. It supplies a new profile for review. The actual public-service solution, components, addresses, tests, risk acceptance and native activation are not completed by it.

Adopting authority and approval evidence: **not recorded**. Link the actual design review and its conditions when they exist; a code merge does not authorize a site or service. Keep sensitive site parameters and private credentials in their approved systems.

[Maintained design register](README.md) · [Decision register](../adr/README.md)
