# Planning service

Status: P05 implements the assessment, immutable plan, review and source-owner contracts described in the [implementation record](../implementation/p05-planning.md). Native effects and operational readiness remain unavailable. Runtime: Python; source: `services/planning/`. Owner: infrastructure engineering with architecture/security and platform profile owners.

The private service package owns its manifest, dependency lock, wheel and installed `planning-health` diagnostic. It implements one-shot process liveness; dependency readiness deliberately exits unavailable. No HTTP API, compilation worker, task consumption, assessment, plan compilation, persistence or other business behavior is implemented. Native operations are disabled.

The [Planning package report](../implementation/p01-planning-bootstrap.md) records isolated wheel checks, installed-command tests and hosted CI. The [Python image report](../implementation/p01-image-foundations.md) records the actual restricted container build and diagnostics. These results establish a bootstrap boundary, not a running Planning API or application readiness.

## Purpose and responsibility boundary

Explain whether application intent can be realized on an exact destination and compile a reproducible proposal for the permitted path. Preserve why a candidate is eligible, conditional, unsupported or unknown, with remediation and the input versions behind the conclusion.

Planning does not approve, reserve resources, write native infrastructure or publish qualification. An adapter declaration is a capability claim to test; assurance evidence establishes scoped qualification. A plan grants no execution authority.

## Owned aggregates and invariants

| Aggregate | Rule |
| --- | --- |
| Requirement / ProfileVersion | Immutable vocabulary, operation constraints and all required profile dimensions; unknown/unsupported values remain explicit. |
| Assessment / assessment task | Pinned intent, observation generations, profile/policy/qualification references, candidate results and rule explanations. |
| Plan | Immutable canonical action graph, input versions, exact operation/scope, budgets, expiry, dependencies, recovery strategy and digest. |
| Compilation record | Compiler/artifact versions, canonicalization version, input digests and deterministic output provenance. |

All mandatory inputs must be present and sufficiently fresh to issue an executable proposal. Do not convert unknown security, capacity, ownership or qualification into eligible. Lab candidates use an explicit isolated campaign context and clearly identified missing qualification, never a production eligibility flag. Operational admission still rechecks current facts later.

Plan inputs pin catalogue revision, inventory generations, policy/profile revisions, qualification scope, adapters/automation artifacts, service contracts, state ownership, action graph, reservation intents and recovery boundaries. Secrets are referenced by approved scope, never embedded. Resource mappings preserve tenant, WSD, logical domain and native-instance distinctions.

## Implemented P05 API surface

The [published API](../../contracts/openapi/planning-v1.json) uses
`/v1/tenants/{tenant}/applications/{application}/environments/{environment}`.
Commands are synchronous and bounded to three destinations, 50 workloads,
800 requirements, 500 graph nodes, a 256 KiB request, a 900 KiB stored result
and 30 accepted commands per tenant per minute. The Console preserves exact
command identity when a post-commit reply is lost. A future asynchronous API
would require a separately versioned contract; no computation worker is implied.

| Method and suffix | Result |
| --- | --- |
| `POST /assessments` | `201` immutable pinned assessment receipt, after all destinations are authorized. |
| `GET /assessments/{id}` | Original findings, sources and candidate scope after current authority checks. |
| `POST /plans` | `201` immutable plan and content-bound approval digest. |
| `GET /plans/{id}` | Original plan plus a separate current validity evaluation. |
| `POST /plans/{id}/validity` | Current direct owner checks and conservative event invalidation holds. |
| `POST /plans/{id}/diff` | Material paths changed; both plans' destinations are currently authorized. |

Governance alone reads `/v1/plans/{id}/revisions/1` with a distinct workload
credential. The [owner read contract](../../contracts/openapi/planning-inputs-v1.json)
requires each source to recheck the original request-bound delegation. Versioned
profiles and policies are mounted in Planning custody; qualifications are read
from Assurance custody. No list, profile mutation or native dispatch route is exposed.

## Authorization and bootstrap

P08's [migration preparation API](../../contracts/openapi/planning-migration-v1.json)
re-reads an exact current confirmed Inventory review under the request's `plan.create`
delegation. It derives native identities, profile digests, capacities, method,
owner-input digest and complete datasets, and accepts only explicit target keys and
supported disk formats. The result is a binding for subsequent native plan composition,
not a persisted, approved or executable MigrationPlan. Lifecycle independently checks
the same current owner receipt before admission; no client-supplied native fact or
preparation response can confer write authority.

Require authenticated actor plus service delegation and `plan.create` and `plan.read` scopes over both the application and candidate destinations. Fetch catalogue/inventory through scoped APIs; a broader planning service credential is not permission to expose all site data to the requester.

Bootstrap uses reviewed profile versions, not an empty-registry “allow all” mode. P05 requires P03 intent and P04 provenance. All three platform profiles cover the required dimensions; only the selected path needs a feasible first execution plan. Missing real inputs may support simulation design but never an E3 claim.

## Consistency, retries and events

Tenant/principal/command-scoped idempotency covers assessment and compilation requests, including input-selection rules. Resolve and persist selected versions once; retries return the same pinned request rather than silently picking fresher inventory. A new key can request reassessment, which yields a new record.

Persist compute task and dispatch outbox atomically. Canonical output excludes declared variable request metadata or binds it separately; canonicalization/version rules must be implemented identically in PHP/Python verifiers. Same pinned semantic inputs produce the same executable content digest. Never approve a digest computed from display HTML or a mutable database serialization.

Publish `planning.assessment.completed` and `planning.plan.created` with version/digest references. Consume catalogue, inventory and assurance changes to flag affected validity projections. Those projections do not mutate historical plan bytes or replace lifecycle's direct admission rechecks.

## Dependencies and failure behavior

Dependencies: catalogue, inventory, assurance qualifications, governance, policy/profile repository and local database/task infrastructure. Unavailable or stale mandatory sources yield explicit unknown/blocked results or a retryable task error; partial successful checks cannot hide failed checks. An assessment error does not cancel a previously admitted lifecycle job.

Planning emits reservation requirements and expiry/revalidation rules. Lifecycle owns the reservation journal and approved external acquisition; P05 simulation tests races using those contracts. Do not pretend distributed capacity has been reserved because an assessment found it available.

## Deployment and operation

Deploy the bounded API and confirmed fact processes independently under Planning ownership. Isolate compilation from native credentials and mutation networks. Set input-size, graph complexity, runtime and per-tenant resource budgets to prevent a large intent blocking other tenants; values are P00/P05 decisions.

Measure task age, rule evaluation time, stale/unknown input rates, deterministic-digest failures and blocked candidate reasons. Preserve immutable plan/profile artifacts and canonicalization code versions under retention; restore current validity as unknown until authoritative inputs are rechecked. Record compiler artifact digests with evidence.

## Verification and delivery

P05.01 profiles; P05.02 policy/assessment; P05.03 reservation design; P05.04 compilation; P05.05 review; P05.06 admission binding. Requirements R06–R08/R12–R14/R17/R19–R21/R32; campaigns Q03/Q06.

Test equivalent pinned inputs across runtimes, stale/incomplete inventory, revoked qualification, unsupported required capabilities, hidden destination denial, domain/interface mapping, changed policy/profile digest, capacity race, cyclic action graph and post-target-write recovery omissions. A readable dry run does not prove the compiled actions are safe or executable.

## Context source ownership and code control

Owned source root: `services/planning/src/planning/`. Capability/profile interpretation, placement/assessment and immutable plan compilation capabilities. Provider-neutral rules stay separate from observation and contract clients.

Use the [context code structure](../architecture/context-code-structure.md), [context registry](../../architecture/context-map.yaml) and [code-control policy](../engineering/code-control.md). This Python service retains `domain/`, `application/`, `infrastructure/` and `interfaces/` with the documented dependency direction. Its capability modules may collaborate within the same owning context. Composition binds adapters; public API/event schemas define cross-service access. Internal models, use cases and migrations are not exported as shared business packages. The pragmatic Laravel convention in ADR-024 applies to PHP services and does not relocate this Python source.

The service owner reviews source/dependency changes and maintains legal/forbidden import fixtures, contract consumers and isolated build inputs. Runtime data-access denials remain separate tests. Registration or a static check does not grant a worker additional native authority.

## P01 messaging increment

The [transactional messaging foundation](../implementation/p01-messaging.md) adds a
service-owned reference fact/outbox (Catalogue) and inbox/projection (Planning).
It exposes no product API or authorization decision. See that record for the exact
contract, retry, isolation and verification scope.
