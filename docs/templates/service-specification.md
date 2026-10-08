# Service specification template

Record service name/path, owner role, design status, related requirement/package/ADR IDs and reviewed revision/date.

## Purpose and boundary

Explain the user outcome, authoritative decisions and explicit nonresponsibilities. Identify callers and why this service warrants independent deployment.

## Domain and persistence

List owned aggregates, tenant bindings, identity/revision rules, invariants, deletion/retention and database/migrator roles. Link the canonical domain model. Identify projections and their provenance/lag; forbid cross-service SQL ownership.

## Interfaces

List versioned commands/queries and produced/consumed events with owning schema paths. Define principal/tenant/scope validation, payload limits, concurrency, idempotency, retry ordering, errors, timeouts and backward compatibility. Link examples rather than duplicating large schemas.

## Dependencies and failures

For each dependency, identify why it is called, current versus cached facts, failure/timeout behavior and what can safely continue. Cover duplicates, stale data, revocation, partial persistence, unknown effects and recovery as applicable.

## Deployment and operations

Specify image/process roles, configuration versus secrets, trust/network flows, health/readiness, scaling/backpressure, telemetry, database evolution, upgrades, backup and restore. Link actual runbooks once rehearsed.

## Acceptance and delivery

Identify applicable [engineering controls](../engineering/coverage.md), owning implementation locations and justified exceptions. Include input/response bounds, query/cache/queue limits, schema evolution, request/job tenant cleanup and relevant browser/security checks. Link common standards; do not duplicate or silently weaken them.

Map requirements to package/gate IDs and positive, denied, conflicting and interrupted cases. Identify required evidence environments and known design decisions. Link status/evidence in the canonical register; do not add independently maintained completion flags.
