# ADR — Existing service authority error envelopes and retry semantics

Date: 2026-10-11  
Status: Accepted for the new authority-boundary contract releases. No producer runtime changes, except the separately approved removal of the unversioned Assurance planning-qualification route.

## Context

Existing Inventory, Planning and Lifecycle ASGI services emit JSON `{"error": "snake_case_code"}` for rejected requests. Governance and Catalogue custom exceptions also use `error`, while standard Laravel validation/HTTP exceptions can emit `{"message": "...", "errors": {...}}`. The former documentation's `application/problem+json` was a proposed format, not the behavior shipped by these services. Claiming one wire envelope would create false conformance.

## Decision

Publish `contracts/schemas/common/error-v1.json`. New authority-boundary OpenAPI operations embed the exact schema, with `application/json` for every documented non-2xx response. Preserve both shipped forms, keeping the stable `error` code when available and the Laravel `message` alternative for framework responses. Do not retrofit older published bundles or add a new runtime exception handler in this work. A future universal problem+json migration requires a separate version and producer/consumer release, not a documentation-only change.

A response from an owner is never a transferable authority grant. A `503` is an unverified dependency, not permission to proceed. Do not translate E2 fixture observations into E3/E4 provider evidence. Consumers revalidate current caller, actor, tenant, delegation, scope, resource and immutable input digests.

## Explicit retry and idempotency decisions

| Operation | Current implemented behavior | Decision for clients and future contracts |
| --- | --- | --- |
| Governance actor-delegation issuance | A successful call creates a new random token and delegation row. It has no `Idempotency-Key` contract. | **Not safe to automatically retry** after an ambiguous timeout. Reacquire authenticated session state or explicitly revoke unused grants; a future receipt-backed issuance command needs a new wire version. |
| Assurance evidence upload | Deduplicates on tenant, job and content digest; verifies stored content/fingerprint and rejects conflict with 409. | Identical content retry may return the same upload ID. No additional transport key required by this endpoint today. E2 custody only. |
| Assurance evidence finalization | Returns the existing immutable evidence receipt on repeat; verifies digest/custody integrity. | Retry only for the same evidence ID after validating current authority. Does not confer native support. |
| Assurance evidence review | Inserts a new review event/ID on each accepted invocation, with independent reviewer admission. | **Not idempotent**. Do not blindly retry a lost response. Read authorized evidence reviews first; adding a durable review-command ID is deferred to a separately versioned contract. |
| Lifecycle native-job `continue-transfer` | State/revision-conditional command requiring `expected_revision`; it does not take an `Idempotency-Key`. | Re-read current job state and revision after an ambiguous result, then determine whether a new command is appropriate. A `202` is acceptance, not native completion. |
| Native-effect worker commands | Signed, bound, journaled native grants provide the exactly-once effect authority. | **Do not introduce `Idempotency-Key`**. Never manufacture another effect identity to retry an uncertain result. |

## Error and status conformance

The owning controller/middleware remains the status source of truth. The OpenAPI release must explicitly list statuses it can emit; CI exercises representative authorized, denied, bounded and unavailable cases. A route count or schema-only test is not evidence every status has been independently exercised in a live producer. Record unexercised statuses as verification gaps rather than claiming full acceptance.

## Consequences and follow-up

The contract checker rejects new authority operations missing the shared error schema. A historical UUID exception is tied to the exact Git blob to prevent silent expansion. Retire the unversioned `planning-qualification` alias; only `planning-qualification-v2` is a live Assurance route. Existing clients already use the v2 path. This ADR does not authorize native writes or change operational admission.
