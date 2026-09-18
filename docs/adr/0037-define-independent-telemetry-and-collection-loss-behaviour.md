# ADR-0037 — Define independent telemetry and collection-loss behaviour

**Status:** Proposed<br>
**Accountable role:** Observability service and security operations owners<br>
**Scope:** Portable hosting infrastructure service and supporting privileged execution<br>
**Original decision identifiers:** Chapter-derived; no standalone source ID asserted.<br>
**Source chapters:** [RA §26](../architecture/reference/26-operating-model-capacity-and-observability.md) · [SVC §2](../architecture/shared-services/2-name-time-initialization-and-telemetry-profiles.md)

New source-backed proposed clarification from the named architecture sections; no historical acceptance is asserted. The linked record is not made authoritative by rendering it. Real adoption needs the stated scope, actual authority and independently protected decision evidence.

## Context

A healthy tenant or a reachable collector does not establish independently attributable, retained security telemetry. Logging loss can invalidate evidence while enforcement continues.

## Decision recorded in the source

Use versioned logging profiles identifying event coverage, stable identities, time integrity, minimization, forwarding delay, buffering, loss indication, retention and operator access. Define the permitted operation and restricted-change response during loss; never create a permissive fallback.

## Alternatives and limits recorded in the source

This record makes an existing source obligation explicit; it does not claim a previously held alternatives meeting. A vendor-specific implementation is accepted only with supported native evidence and the relevant owner decision.

## Consequences

Capacity and recovery design must include collectors, time sources and buffering. Separate consumption, collector administration and evidence authority. A local packet counter is not the central telemetry service.

## Engineering and implementation obligations

Assign the actual service owner, native mechanism, failure/recovery path, scoped access and independent verification for each requirement. Record unimplemented/external controls rather than linking a generic module as proof.

## Requirement and code traceability

[OBS-001](../assurance/requirements.md#OBS-001) · [OBS-002](../assurance/requirements.md#OBS-002) · [OBS-003](../assurance/requirements.md#OBS-003)

Related implementation areas are traceability targets, not proof of complete implementation:

- [docs/architecture/reference/26-operating-model-capacity-and-observability.md](../architecture/reference/26-operating-model-capacity-and-observability.md)
- [sources/implementation_backlog.csv](../../sources/implementation_backlog.csv)

Review [the assertion allocation](../implementation/assertion-allocation.md) for enforcement owner, location, evidence class and unimplemented dependencies.

## Open decisions and acceptance

Concrete service parameters, installed components and organizational acceptance remain open. Local tests and repository merge do not qualify the native capability.

**Deciding authority:** Not recorded<br>
**Decision date:** Not recorded<br>
**Decision record:** Not supplied<br>
**Evidence references:** Not supplied<br>
**Decision rationale:** No lifecycle decision recorded<br>
**Superseded by:** None

Evidence references require owner verification; this repository does not authenticate a signatory or issue native operating authorization. Source-derived Proposed records remain proposed until their genuine decision is recorded. Accepted and rejected records are retained, not overwritten out of history.

---

[Decision register](README.md) · [Maintained design workspace](../current/README.md)
