# Contract conventions and ownership

The current source of truth is [the active contract catalogue](../../contracts/README.md).
All deployed interfaces are registered in
`architecture/contract-consumers.json`; retired paths and review status are
recorded in `architecture/retired-contract-releases.json`.
Do not use historical contract paths or unpublished proposals as live interfaces.

## Design rules

- The owning bounded context defines each request, response, event payload,
  error code and eligibility decision. Consumers must not infer authorization
  from a returned identifier or a claimed qualification level.
- HTTP contracts specify authentication, exact tenant/resource scope, methods,
  status/error envelopes, freshness, idempotency where implemented, rate/retry
  bounds and immutable request or digest bindings.
- JSON Schema 2020-12 and versioned OpenAPI/AsyncAPI artifacts define wire
  shapes. Check validated producer responses against consumers' installed
  contracts before converting them into domain values.
- Use stable opaque IDs, explicit units, bounded pagination and truthful
  unknown/partial results. Reject unsupported versions or incomplete evidence.
- Native write eligibility is never inferred from simulated E2 validation.
  Independent E3/E4 qualification, signed custody and current authority remain
  separate requirements.

## Active ownership examples

- Catalogue: `contracts/openapi/catalogue-v1.0.1.json` plus current internal
  planning-intent reads.
- Inventory: `contracts/openapi/inventory-v1.9.json` and
  `contracts/openapi/inventory-native-input-v1.3.json`.
- Planning: `contracts/openapi/planning-v1.2.json`,
  `contracts/openapi/planning-migration-v1.6.json` and
  `contracts/openapi/planning-immutable-plan-v1.1.json`.
- Lifecycle: `contracts/openapi/lifecycle-v1.json`, active native job,
  migration boundary and internal authority releases.
- Governance and Assurance: versioned approval, support, evidence custody
  and qualification owner interfaces.
- Foundation event: `contracts/schemas/events/catalogue-foundation-recorded-v1.json`
  with two installed consumer names pinned to that source.

See the active registry for the complete authoritative inventory and installed
artifact locations. Console and Planning must validate bounded service-owner
responses, not accept untyped or guessed schema compatibility.

## Versioning, retirement and verification

Current published canonical files are immutable against the review base.
Changing the wire contract requires a new version; old canonical paths are
removed from the working tree once retirement is authorized, rather than copied
into historical folders. Source fragments and test fixtures are not separately
published releases. No legacy adapters or historical replay tests are needed
for an unused version.

Each retirement records the removed exact path, reason, internal review and
external-consumer verification status. A repository-only scan is not evidence
that independently deployed clients have been migrated.

`scripts/contracts/check.py`, `scripts/contracts/retirement_integrity.py`,
`scripts/contracts/runtime_inventory.py` and the
[contract-integrity workflow](../../.github/workflows/contracts-integrity.yml)
check active canonical coverage, executable references, runtime consumers,
wire/schema projections and safety-negative cases. P05/P08 and Capability
Assurance check current contracts only.

See [the service error/idempotency ADR](adr-service-authority-errors-idempotency-2026-10-11.md)
and the [implementation records](../implementation/) for operational details.

## Retirement clearance after the active-only cleanup

The native API duplicates were eliminated: only Lifecycle migration boundary v2
and worker migration effect v2.1 claim their current native operations. Security
negative tests still reject obsolete provision-only grants. The retirement checker
also rejects newly retired canonical paths when their external-consumer status is
unverified. Fifty-three older owner-directed removals remain explicitly
unverified and frozen as a historical review backlog; this is not external
clearance. See `architecture/retirement-unverified-baseline.txt` and the
retirement manifest before approving further deletions. Installed consumer-copy
checks now recognize actual JSON loader/import expressions and typed Planning
owner-operation mapping instead of filename mentions in comments.
