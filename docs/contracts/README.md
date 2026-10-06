# Contract conventions and ownership

Status: proposed product contract design for P00/P01. The examples in this document remain illustrative. A separate [P00 contract-tool experiment](../implementation/p00-contract-tooling-results.md) now executes synthetic OpenAPI and JSON Schema fixtures and generated PHP/Python/TypeScript clients; it defines no product API or AsyncAPI channel. Exact cardinalities, authentication delegation and canonicalization await ADR-009/012/013 decisions.

## Where contracts will live

| Artifact | Planned authoritative location | Owner / purpose |
| --- | --- | --- |
| HTTP definitions | `contracts/openapi/<service>.yaml` | Owning service; request/response, scope, errors and concurrency semantics. |
| Event envelopes and payloads | `contracts/asyncapi/<service>.yaml` and `contracts/schemas/events/` | Producer; versioned envelope and event schemas, ordering/replay expectations. |
| Shared scalar/problem schemas | `contracts/schemas/common/` | Architecture; narrow interoperable formats, not shared business data models. |
| Valid/invalid fixtures | `contracts/fixtures/{service}/` | Producer and consumer jointly; deterministic examples and rejection cases. |
| PHP / TypeScript / Python clients | `packages/generated/{language}/` | Generated from locked schemas; regeneration checked in CI, no manual semantic forks. |
| Compatibility tests | `tests/contracts/` | Quality and service owners; validate PHP/Python interpretation and producer/consumer versions. |

These paths are destinations to implement in P01.03, not evidence that the files are present. [Service specifications](../services/README.md) own business semantics. [Examples](examples.md) show proposed interactions without duplicating an authoritative future schema.

## HTTP conventions

- Each service has its own authenticated origin; `/v1/tenants/{tenant_id}` is the proposed tenant-scoped prefix. Any gateway mapping is deployment configuration, not a new domain owner.
- Use opaque stable IDs, explicit schema versions, UTC timestamps with timezone and typed units. Public sample IDs are synthetic; consumers must not parse business meaning out of real IDs.
- A tenant path/header is a selector. Validate the authenticated service, effective actor, delegation, audience and current action/resource scope independently. Never trust an `actor_id` supplied as an ordinary JSON field.
- Return `Location` for created/accepted resources and an authorized status link for asynchronous work. Catalogue revision creation is synchronous; discovery/assessment tasks and lifecycle execution jobs have distinct typed IDs.
- A completed assessment task yields an assessment; an execution job coordinates native operations. Only lifecycle owns native execution jobs. A `202` means accepted for processing, not successfully executed.
- Require `Idempotency-Key` for commands whose safe retry matters. Scope it by tenant, effective principal, command and relevant parent resource. Persist its canonical payload binding and result with the command's domain mutation.
- After checking current caller access, an identical accepted retry returns the original command receipt/IDs without dispatching work again. Different canonical payload under the same key returns `409`. Record whether a request was accepted; transient pre-admission errors must not masquerade as an accepted receipt.
- A duplicate still in acceptance processing returns a defined in-progress response and status reference when known. Do not start a second transaction path merely because the first response was lost. Exact response/header choices lock in P01.03.
- For catalogue appends, `If-Match` explicitly names the current parent application ETag, even though the target is the revision collection. An accepted retry is recognized before comparing its now-stale ETag. A new command missing the precondition returns `428`; a mismatched precondition returns `412`.
- Canonical command hashes include the semantic payload, command/parent identity and expected revision; exclude transport retry count and correlation metadata. Plan canonicalization has its own explicit version and executable-content boundary; P01.03 must publish cross-language golden vectors before relying on digests.
- Use bounded cursor pagination over a stated snapshot/order. Results include freshness/provenance where observations or projections are involved. Readers cannot infer a complete set from a partial page or scan.

Command-receipt retention must exceed the allowed retry window and preserve job/operation deduplication for retained effects. P00.05/P01.03 define bounds and tombstones; pruning a receipt must not make an old native effect eligible for blind replay. Error and retry policies document which failed commands can safely be retried with the same key.

## Error contract

Use the proposed `application/problem+json` body with stable `type`, `code`, HTTP `status`, safe `detail`, `correlation_id`, `retryable` and optional scoped field errors or status reference. Callers branch on code, not English text. Never include secrets, SQL, internal stack traces or another tenant's identifiers.

| Response | Meaning / client action |
| --- | --- |
| `401` | Missing/invalid/expired authentication; use the approved session flow, never broaden credentials. |
| `403` / `404` | Forbidden or deliberately non-disclosing resource lookup; use one documented existence-protection policy across services. |
| `409` | Idempotency payload mismatch, incompatible current state or resource ownership conflict; inspect the code before taking any action. |
| `412` / `428` | Stale or missing revision precondition; reload/compare and submit a deliberate new command. |
| `422` | Semantic/schema invalidity, unmet required plan conditions or invalid scope binding; change the request or satisfy blockers. |
| `429` | Budget exceeded; honor retry guidance with the same command identity. |
| `503` | Required authority/dependency unavailable; preserve known request/job identity and check status before retrying. |

An HTTP timeout is absence of a response, not a native operation result. An accepted job with `outcome_unknown` is normally a successful authorized status read (`200`) showing a hold; it is not a `500` instructing a client to create another job.

## Events and consistency

Use dotted names such as `catalogue.intent-revision.created` with a separate integer `schema_version`. The producer owns the schema. The envelope includes event ID, occurred time, producer/artifact version, tenant scope, aggregate type/ID/version and causation/correlation IDs. Payloads carry essential references/digests; consumers fetch additional authorized data when needed.

Mutation and outbox commit locally together; inbox deduplication and local consumer effects commit together. Delivery is at least once. Ordering is per documented aggregate/version, not global. Consumers detect gaps/out-of-order versions and refresh through the source API when required; timestamps alone do not establish causal order. Dead-letter/replay rules require redaction, restricted access and an owner.

Events carry facts, never reusable credentials or independent permission to run a native operation. Replayed approval/plan events may rebuild a projection but cannot bypass lifecycle admission or repeat a journaled side effect. Revocation events accelerate response; direct authority checks remain necessary.

## Compatibility and review

Framework adapters follow [Laravel conventions](../engineering/laravel-conventions.md), [data and messaging](../engineering/data-and-messaging.md) and [frontend rules](../engineering/frontend.md). Explicit resource serialization must match the owning schema rather than expose an Eloquent graph. Form validation never grants authority over referenced objects. Inertia browser forms use their redirect/error-bag protocol; the console maps safe service errors without changing this JSON API contract.

Each integration defines connect/total timeouts, permitted endpoints, payload and pagination bounds, rate-limit behavior and one coordinated retry budget. Record which operations are safe to retry and how accepted-but-unanswered commands are reconciled. Client, queue and workflow retries cannot multiply into unbounded attempts. Contract fixtures include old/new enum and nullable-field handling, precision boundaries, unknown fields, denied resource fields and sanitized dependency failures.

P01.03 locks initial contracts with both provider and consumer owners. Document additive-field handling, enum expansion, nullability, date/number precision and unknown-version behavior; do not assume every additive change is safe. HTTP breaking changes require a new supported major route or a reviewed compatibility bridge; event breaking changes require a new schema/version and migration/replay plan.

CI should regenerate clients, validate valid/invalid fixtures, compare schema compatibility and run both PHP and Python against digest/error/idempotency golden cases. New behavior links requirements, packages and evidence through the [status model](../implementation/status-model.md); passing these checks proves contract behavior, not native qualification.


## Measured tool candidate

[ADR-012](../decisions/adr-012-contracts-and-event-evolution.md) records the tested OpenAPI 3.0.4 subset, JSON Schema 2020-12 event envelope and OpenAPI Generator 7.25.0 candidate. The [isolated source](../../spikes/compatibility/contracts/README.md) supplies locked reproduction commands and negative fixtures. Generator outputs remain private Infrastructure adapters; wire-schema validation must precede domain translation because generated models and decoders do not enforce every constraint.

P01.03 must still publish the reviewed product schemas in this contract tree, choose AsyncAPI channels/bindings, implement the selected compatibility checker and golden digest/error/idempotency vectors, and execute real provider/consumer and outbox/inbox tests. Deterministic generation and synthetic fixture rejection do not complete those gates.

## Initial P01 owner contract

[Catalogue foundation facts](../../contracts/asyncapi/catalogue.yaml) and the
[versioned event schema](../../contracts/schemas/events/catalogue-foundation-recorded-v1.json)
are implemented for the [P01 messaging reference](../implementation/p01-messaging.md).
Private generated DTOs follow schema validation; `generate.py --check` rejects
drift. The 16 shared fixtures compare PHP/Python acceptance and canonical digests.
The preceding business APIs remain proposed; this reference does not publish them.

The [foundation HTTP contract](../../contracts/openapi/foundation-health-v1.json)
now describes the existing diagnostic routes. Its [implementation record](../implementation/p01-http-contracts.md)
documents locked client generation, PHP/Python fixture interpretation and the
conservative base/head rule that rejects mutation or deletion of published
contract artifacts. The rule requires a new artifact for a new version; it does
not turn proposed business APIs into implemented endpoints.

## P05 Planning owner and review contracts

The implemented [review API](../../contracts/openapi/planning-v1.json) and
[independent source-owner reads](../../contracts/openapi/planning-inputs-v1.json)
are bounded synchronous interfaces. The [v1.1 immutable binding](../../contracts/openapi/planning-immutable-plan-v1.1.json)
adds semantic content digest, canonicalization and authority lane to the exact
Governance approval binding. Historical v1 artifacts remain unchanged; the
corrected synthetic plan is explicitly [version 1.1](../../contracts/fixtures/planning/synthetic-plan-v1.1.json).

[Content](../../contracts/schemas/planning/content-v1.json),
[admission](../../contracts/schemas/planning/admission-record-v1.json),
[reservation receipt](../../contracts/schemas/planning/reservation-receipt-v1.json),
[qualification](../../contracts/schemas/planning/qualification-v1.json) and
[fact](../../contracts/schemas/planning/fact-v1.json) schemas keep observations,
qualification and authority separate. `scripts/p05/generate_contracts.py --check`
verifies exact consumer snapshots and component-owned test fixtures. See the
[implementation record](../implementation/p05-planning.md) for immutable semantic
versus approval identity and the separate P06 atomic admission obligation.

## P06 execution and custody contracts

The implemented [Lifecycle API](../../contracts/openapi/lifecycle-v1.json) binds
admission, current job projections and idempotent operator requests. Its exact
Console snapshot validates owner responses before rendering. The
[Assurance custody API](../../contracts/openapi/assurance-evidence-v1.json)
separates workload upload/finalization from delegated reads and independent review.
All receipts remain explicitly E2 simulation with no native support authority.
`scripts/p06/generate_contracts.py --check` checks owner artifacts and consumer
drift; the live campaign validates actual successful wire responses against them.
Use the [implementation record](../implementation/p06-execution.md) for effect
certainty, current authority and recovery behavior.
