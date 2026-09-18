# ICD-M01 — Infrastructure interface ownership and service agreements

**Version:** 0.1 · **Status:** Proposed · **Accountable role:** Producing and consuming infrastructure owners.

## Scope and authority

Per-interface working design obligations across independently governed infrastructure.

This is a newly authored maintained Markdown record, not a reconstruction of an unavailable Word original. Its creation date is not an acceptance date. Source basis: [RA §8](../architecture/reference/8-zone-interfaces-routing-and-security-edge-topology.md) · [NBD §6](../engineering/network-boundaries/6-issue-an-interface-control-and-handoff-record.md) · [SVC §1](../architecture/shared-services/1-shared-service-placement-and-consumption-boundaries.md).

## Design content

For each interface identify producer, actual client, native endpoint, permitted operation, address family, trust material, resource entitlement, initiation/reply path, MTU/packet budget, capacity and security boundary. Record data-path and management-path ownership separately. A shared endpoint does not authorize a tenant to administer its backing service.

The agreement identifies version/feature compatibility, failure detection, retry/backpressure, log attribution, identity/key expiry and recovery order. Define who can change a next hop, firewall scope, service credential or data object, and which observer can independently verify it.

Use a bounded allocation and lifecycle reference across owners rather than credentials or large state dumps. Include expected generation, operation identity and safe stopping conditions for partial success. Name release/retention conditions before reusing an address, attachment, service identity or data copy.

## Engineering and implementation handoff

Populate the controlled engineering schedule with exact native values and support evidence. Both owners review it. Link each field to the applicable assertion and actual procedure, and retain separately protected evidence. The repository’s examples do not supply those native values.

## Acceptance and open work

Unassigned endpoints, authority, recovery and version terms block the corresponding handoff. A local draft is not a signed agreement.

Adopting authority and approval evidence: **not recorded**. Link the actual design review and its conditions when they exist; a code merge does not authorize a site or service. Keep sensitive site parameters and private credentials in their approved systems.

[Maintained design register](README.md) · [Decision register](../adr/README.md)
