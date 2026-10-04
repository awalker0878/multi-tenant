# Lifecycle service

Status: proposed service specification. Runtime: Python with Temporal; destination: `services/lifecycle/` and scoped execution pools. Owner: infrastructure engineering with SRE/security and native resource owners.

## Purpose and responsibility boundary

Admit only authorized, sufficiently evidenced plans and coordinate their execution durably. Record every intended native effect, actual attempt, observed outcome and allowed recovery action so a crash or lost response cannot create a second uncontrolled mutation.

Lifecycle owns admission and native-operation authority, not requested intent, approval policy, inventory truth or qualification. Temporal owns workflow history/progress; the API's job view is a controlled projection, not a competing orchestration state machine. Workers obey lifecycle authority and report through its contracts.

## Owned aggregates and invariants

| Aggregate | Rule |
| --- | --- |
| Admission / Job | Stable tenant/actor/command identity, plan/approval binding, current checks and durable dispatch identity. |
| NativeOperation | Intended effect, target, plan digest, idempotency/request IDs, artifact versions, attempts, fencing scope/epoch and observed outcome. |
| ManagedDomainBinding / ownership | Approved link between logical intent and native scope with explicit fields/state owner; inventory remains observation owner. |
| Reservation journal | Local intent/attempt/receipt for authoritative external reservations, renewals and release; no fictitious distributed transaction. |
| Execution grant / resource hold | Bounded worker audience, tenant/action/resource scope, expiry and fencing; lease expiry alone never proves an old effect stopped. |
| Recovery decision | Attributable authorized reconciliation/compensation/forward-recovery instruction linked to observed facts. |

Native outcomes distinguish `not_started`, `confirmed_failed`, `confirmed_succeeded` and `outcome_unknown`. Job progress is separate: an unknown effect places the job on hold rather than falsely marking it failed or completed. Already dispatched effects remain observable after grant revocation or cancel request.

## Proposed API surface

Routes use `/v1/tenants/{tenant_id}`; execution workers use separately authenticated internal contracts with narrower audiences/scopes.

| Method and route | Contract |
| --- | --- |
| `POST /jobs` | Require idempotency key, exact plan/digest, approval and operation scope; current admission checks; `202` for one durable accepted job and status URL. |
| `GET /jobs/{id}` | Authorized progress projection, plan binding, freshness, holds and available recovery actions. |
| `GET /jobs/{id}/operations/{operation_id}` | Intended effect, attempt/outcome and reconciliation references; redact native secrets. |
| `POST /jobs/{id}/cancellation-requests` | Idempotent authenticated request; return request status, never claim in-flight effect was reversed. |
| `POST /jobs/{id}/reconciliation-requests` | Authorized bounded observation/reconciliation command with expected operation version; no arbitrary replay button. |
| `POST /jobs/{id}/recovery-requests` | Exact permitted recovery action/plan and distinct approval where required; preserve point-of-no-return rules. |

Payload examples are in [contract examples](../contracts/examples.md). Resource conflicts may prevent admission even with a new key; duplicate idempotency keys cannot sidestep a reservation/ownership hold.

## Authorization and bootstrap

Revalidate actor/delegation, tenant/resource scope, current grants/revocations, exact approval, expiry/change window, inventory freshness, commissioned site, reservations and exact qualification tuple. Ordinary operational admission requires current support evidence. An isolated lab campaign may execute a reviewed candidate with explicit endpoint/data/credential/impact limits; it never grants production permission.

Workers receive short-lived audience-bound authority and retrieve approved secrets just in time. Before each privileged boundary check applicable authority and resource ownership; record authorization version/time. Revocation stops subsequent effects, while reconciliation observes already dispatched work truthfully. Credential or governance failure cannot enable a fallback broad execution path.

## Durable dispatch, concurrency and events

Persist admission/job, idempotency receipt and dispatch outbox in one lifecycle transaction. Stable Temporal workflow ID derives from the admitted job. Dispatcher retries/reconciles ambiguous workflow starts; one job must not start two logical workflows. Reused key/different canonical payload returns `409`; matching accepted retry returns the same job without new admission or effect dispatch.

Before a native write, durably journal the operation and acquire the required field/resource fencing. Record native request IDs and enforce adapter-specific idempotency where supported. A timeout changes outcome to unknown until independent readback establishes the result; do not release holds or resubmit based solely on lease expiry. Competing ownership claims serialize locally and reconcile external owners.

Publish `lifecycle.job.admitted`, `lifecycle.job.held`, `lifecycle.job.completed` and `lifecycle.operation.outcome-recorded`. Consume grant/approval/qualification revocations for prompt holds; recheck authority directly at boundaries. Event replay cannot itself redispatch native effects; workflow/activity commands use the durable journal and authorization.

## Dependencies and failure behavior

Dependencies: governance, immutable planning records, inventory, assurance, lifecycle persistence, Temporal, identities/secrets and scoped native/service endpoints. New admission fails closed if mandatory checks are unavailable. Existing jobs follow their approved disconnection/safe-point policy; local observation buffers, if used, do not invent new authority.

Reservation acquisition uses approved idempotent owner contracts and durable receipts. Partial multi-owner outcomes trigger reconciliation/compensation; expiry cannot release an allocation independently observed as in use. After migration target writes, recovery cannot silently restart an old divergent source. Retirement has separate deletion, address/identity release and data-retention authority.

## Deployment and operation

Separate control API/dispatcher, Temporal workflow workers and site pools by trust/credential boundary. Pools for infrastructure, guests, shared services and data movement have distinct network/secret scopes. Keep workload payloads on approved source/target paths, outside the console, broker and job database.

Measure queue age, admission denials, unknown outcomes, held resources, fencing conflicts, reconciliation age, cancel latency and evidence backlog. Bind workflow/adapter versions to running histories and test compatible worker rollout. Restore into observation-only quarantine; reconcile actual native effects, authority epochs, reservations and accepted intent before resuming writes.

## Verification and delivery

P05.03/P05.06 establish contracts; P06.01–P06.03 admission/workflows/authority; P06.05 faults; P07 native provisioning; P08 migration/recovery; P09 expansion. Requirements R14–R18/R21–R30/R35/R36; Q03–Q05/Q07–Q10.

Test crash before/after acceptance, lost response, duplicate dispatch, old-worker resurrection, lease expiry, revoke during native call, partial reservation, cancel after point of no return, restore of stale ledger and target-first-write recovery. Completion requires independent native and application postconditions; a successful activity return alone is insufficient.

## Context source ownership and code control

Owned source root: `services/lifecycle/src/lifecycle/`. Admission, execution authority, operation journaling and recovery capabilities. Temporal workflows/activities and site execution adapters implement the reviewed lifecycle coordination boundary; deterministic domain decisions remain independently testable.

Use the [context code structure](../architecture/context-code-structure.md), [context registry](../../architecture/context-map.yaml) and [code-control policy](../engineering/code-control.md). This Python service retains `domain/`, `application/`, `infrastructure/` and `interfaces/` with the documented dependency direction. Its capability modules may collaborate within the same owning context. Composition binds adapters; public API/event schemas define cross-service access. Internal models, use cases and migrations are not exported as shared business packages. The pragmatic Laravel convention in ADR-024 applies to PHP services and does not relocate this Python source.

The service owner reviews source/dependency changes and maintains legal/forbidden import fixtures, contract consumers and isolated build inputs. Runtime data-access denials remain separate tests. Registration or a static check does not grant a worker additional native authority.
