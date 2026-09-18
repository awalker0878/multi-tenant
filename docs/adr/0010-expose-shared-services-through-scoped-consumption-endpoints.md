# ADR-0010 — Expose shared services through scoped consumption endpoints

**Status:** Proposed — source-derived; organizational acceptance not recorded<br>
**Original decision identifiers:** `AD-08`<br>
**Source chapters:** [RA §9](../architecture/reference/9-shared-services-ingress-and-controlled-egress.md) · [SVC §1](../architecture/shared-services/1-shared-service-placement-and-consumption-boundaries.md) · [SDP §4](../solutions/design-method/4-turn-dependencies-into-explicit-service-interfaces.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting. The original source remains linked below; this ADR does not record an approval meeting or invent an acceptance date.

## Context

A tenant can need DNS, backup or key-use services without needing the service subnet, other tenants' data or the service's administrative API.

## Decision recorded in the source

Publish explicit service consumption interfaces with named consumers, operations, identity scope, directions and recovery expectations. Keep backing infrastructure and management separately governed.

## Alternatives and limits recorded in the source

Zone-aligned frontends or a shared backend are possible when their authorization, return-path and dependency boundaries are documented. Broad common-services supernet access is not the baseline.

## Consequences

Network reachability and data authorization are separate controls. Several endpoints sharing one backend are not independent failure domains. The true client may be a host, storage controller or backup executor rather than a guest.

## Engineering and implementation obligations

Issue the producer/consumer interface agreement: endpoint, permitted operation, resource scope, protocol, limits, failure effect, change owner and recovery owner.

## Requirement and code traceability

[SVC-001](../assurance/requirements.md#SVC-001) · [SVC-002](../assurance/requirements.md#SVC-002) · [SVC-003](../assurance/requirements.md#SVC-003) · [MODEL-002](../assurance/requirements.md#MODEL-002)

The following implementation areas are traceability targets, not proof that this decision has been qualified:

- [tools/dns_change.py](../../tools/dns_change.py)
- [lab/mtls_fixture.py](../../lab/mtls_fixture.py)

Review [the implementation coverage map](../implementation/code-map.md) and the target-specific evidence before asserting completion. A local fixture or static source check does not establish deployed behaviour.

## Open decisions and acceptance

Actual service endpoints, native authorization and backing-service resilience remain to be accepted; protocol fixtures are not production services.

Accepting authority: **not recorded**.<br>
Acceptance evidence: **not supplied by this conversion**.<br>
Supersession: no new source supersession is asserted. Record a future change explicitly rather than silently editing an accepted decision.

---

[Decision register](README.md) · [Source and maintenance rules](../DOCUMENTATION_MIGRATION.md)
