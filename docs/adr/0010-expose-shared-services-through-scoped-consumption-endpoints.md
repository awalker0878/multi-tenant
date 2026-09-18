# ADR-0010 — Expose shared services through scoped consumption endpoints

**Status:** Proposed<br>
**Accountable role:** Service operations / Architecture authority<br>
**Scope:** Reusable reference decision; actual site adoption remains unissued<br>
**Record date:** 2026-09-17 (not an approval date)<br>
**Original decision identifiers:** `AD-08`<br>
**Source chapters:** [RA §9](../architecture/reference/9-shared-services-ingress-and-controlled-egress.md) · [SVC §1](../architecture/shared-services/1-shared-service-placement-and-consumption-boundaries.md) · [SDP §4](../solutions/design-method/4-turn-dependencies-into-explicit-service-interfaces.md)

Source-derived synthesis; not a new source standard or a reconstructed approval meeting.

## Context

A tenant can need DNS, backup or key-use services without needing the service subnet, other tenants' data or the service's administrative API.

## Decision

Publish explicit service consumption interfaces with named consumers, operations, identity scope, directions and recovery expectations. Keep backing infrastructure and management separately governed.

## Alternatives and source limitations

Zone-aligned frontends or a shared backend are possible when their authorization, return-path and dependency boundaries are documented. Broad common-services supernet access is not the baseline.

## Consequences

Network reachability and data authorization are separate controls. Several endpoints sharing one backend are not independent failure domains. The true client may be a host, storage controller or backup executor rather than a guest.

## Engineering and implementation obligations

Issue the producer/consumer interface agreement: endpoint, permitted operation, resource scope, protocol, limits, failure effect, change owner and recovery owner.

## Requirement and code traceability

[SVC-001](../assurance/requirements.md#SVC-001) · [SVC-002](../assurance/requirements.md#SVC-002) · [SVC-003](../assurance/requirements.md#SVC-003) · [MODEL-002](../assurance/requirements.md#MODEL-002)

These are related implementation areas, not assertion-level evidence of native qualification:

- [tools/dns_change.py](../../tools/dns_change.py)
- [lab/mtls_fixture.py](../../lab/mtls_fixture.py)

[Requirement/assertion allocation](../assurance/implementation-allocation.md) records partial, external and unimplemented controls separately.

## Open work

Actual service endpoints, native authorization and backing-service resilience remain to be accepted; protocol fixtures are not production services.

## Decision lifecycle and authority

- Deciding authority: Not recorded.
- Decision date: Not recorded.
- Decision evidence: Not supplied; no acceptance claim.
- Disposition rationale: No rejection or supersession recorded.
- Supersedes: None.
- Superseded by: None.

Record authenticity and the deciding authority's jurisdiction require independent review. Passing a record-schema check does not issue or authenticate an approval. The current record status is declared above; publication never grants decision authority.

[Decision register](README.md) · [Maintenance rules](../DOCUMENTATION_MIGRATION.md)
