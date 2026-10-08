# Catalogue service

Status: P03 aggregates, revision APIs and Console journeys pass their automated PostgreSQL/broker/three-engine qualification; representative-user and independent acceptance remain open. See [the implementation record](../implementation/p03-catalogue.md). Runtime: Laravel/PHP; source: `services/catalogue/`. Owner: product engineering, with product/architecture review of ADR-013.

The [package replay](../implementation/p01-laravel-foundations.md) and [image measurements](../implementation/p01-laravel-images.md) bind actual source, dependency and execution results. Diagnostic liveness does not establish application readiness; readiness remains HTTP 503 until real dependencies and their probes are implemented.

## Purpose and responsibility boundary

Capture what an application owner wants to run, where its logical components belong and what outcomes it requires. Preserve every accepted intent revision so planning and approval can refer to an exact, reproducible request.

Catalogue does not discover resources, select a platform, allocate addresses, approve a plan, own a workflow or declare support. Native VM identifiers are external references, never workload identities. An unsupported requirement is valid intent that planning must explain as blocked.

## Owned aggregates and invariants

| Aggregate / record | Implemented initial Catalogue behavior |
| --- | --- |
| Application | Stable tenant-bound ID, human name, service owner, accountable owner/acceptance criteria in immutable intent and current-revision index keyed by deployment. |
| IntentRevision | Append-only canonical intent for one application deployment/environment, parent revision, schema version, authenticated author, digest and creation time. |
| WorkloadDefinition | Stable application-owned logical component ID and role; native identities and environment-specific requirements do not redefine that identity. |
| ApplicationDeployment / WorkloadPlacement | Revision records associate a deployment with an environment and each workload placement with one WSD and one logical security domain plus effective compute/guest/dataset/service/recovery requirements; initial cardinalities follow accepted G00/DC03. |
| Environment, WSD, SecurityDomain | Tenant-owned reference aggregates with revisions and explicit retirement state. WSD is distinct from application, tenant and zone. |
| Command receipt / outbox | Tenant/principal/command-scoped retry binding and durable domain-event publication. |

All references must resolve within the authorized tenant and to the referenced catalogue version. Dependency edges name defined workloads; self-dependencies and cycles in execution-order dependencies are rejected. Runtime communication dependencies are a separate graph and may be bidirectional. ZIPs describe controlled interfaces, never workload placement zones. Deleting a referenced definition is rejected or handled by an explicit new revision; historical revisions remain readable under retention policy.

Each immutable revision contains the complete requested intent for one application deployment/environment, including all workload placements for that deployment. The application owns the revision index; its strong ETag serializes initial edits across deployment streams, and an append updates only the specified deployment's pointer. Revision bytes exclude passwords, private keys, native credentials and live observations. Cross-application dependency attachments remain a separately designed extension; the initial schema names workloads within its complete deployment snapshot. The [domain model](../product/domain-model.md) records initial vocabulary/cardinalities and separately scoped native refinements.

## Implemented API surface

All routes below follow `/v1/tenants/{tenant_id}`. The current OpenAPI artifact is [Catalogue 1.0.1](../../contracts/openapi/catalogue-v1.0.1.json); examples are in [contract examples](../contracts/examples.md).

| Method and route | Contract |
| --- | --- |
| `POST /applications` | Create application plus initial immutable intent; require `Idempotency-Key`; return `201`, application/revision IDs, digest, `Location` and strong application `ETag`. |
| `GET /applications` / `GET /applications/{id}` | Authorized, paginated list or detail; detail includes current revision and strong `ETag`; no stale projection masquerades as authoritative intent. |
| `POST /applications/{id}/intent-revisions` | Require `If-Match` against current application ETag and `Idempotency-Key`; append a complete deployment revision and update its current pointer atomically; `201`, new revision and ETag. |
| `GET /applications/{id}/intent-revisions/{revision_id}` | Return immutable canonical intent, parent/version and digest; enforce tenant authorization even for historical versions. |
| `GET /applications/{id}/intent-revisions` | Paginate history; comparison reads two immutable versions and exposes meaningful additions/removals. |
| `GET` / `POST /environments`, `/wsds`, `/security-domains` | List bounded reference pages or create authorized aggregates with versioned definitions. |
| `PUT /environments/{id}`, `/wsds/{id}`, `/security-domains/{id}` | Update reference definitions with `If-Match` and command identity; names/zones remain stable. |
| `POST /environments/{id}/retirement`, `/wsds/{id}/retirement`, `/security-domains/{id}/retirement` | Retire an unused current reference with `If-Match` and command identity; preserve historical version bytes. |

The revision command explicitly compares its parent application's ETag; this is an application concurrency rule even though the request targets the child collection. Missing precondition returns `428`; stale precondition returns `412`; invalid intent returns `422`; reused key with a different command payload returns `409`.

## Authorization and bootstrap

Governance supplies the authenticated tenant, membership and resource/action authorization decision. Catalogue enforces `application.read/write` and `reference.read/write` and separate reference-definition administration scopes, and checks environment/resource restrictions and same-tenant WSD/domain sharing rules. Author identity is server-derived; a submitted `owner_id` is validated as a permitted service-owner reference, not accepted as caller identity.

P02 governance bootstrap precedes integrated P03 acceptance. Catalogue has no default tenant, internal superuser or fallback grant when governance is unreachable. An unavailable authority produces a retryable hold/error for new writes; permitted read behavior must be expressly selected by ADR-009. Synthetic governance doubles are isolated tests only.

## Transactions, retries and events

Validate authenticated access before exposing a stored command receipt. Scope a retry key to tenant, effective actor, command and parent application; hash the canonical command including its expected revision. A matching completed retry returns its original result even though the application ETag has since advanced. Concurrent first attempts serialize the receipt and current-revision comparison in the local transaction.

In one transaction persist the immutable revision, parent pointer/version, audit facts, command receipt and outbox event. Failure of any write rolls back all five. Publication is at least once; consumers deduplicate on event ID. No event receipt independently authorizes a downstream plan or native effect.

Publish `catalogue.application.created` and `catalogue.intent-revision.created` with application/revision IDs and digest; the authoritative revision contains pinned reference versions. Publish reference-change/retirement events with the affected version. Current requests query authoritative identity/grant policy; Catalogue maintains no permission-granting event projection. Payloads carry minimum metadata, not complete sensitive application specifications.

## Dependencies, failure behavior and operations

Required: catalogue database, governance authorization, trusted identities and configured outbox transport. Broker loss retains unsent outbox records; growth/backpressure thresholds are defined before release. Planning and lifecycle outages do not prevent permitted intent edits, and edits never alter an already pinned plan. Reference races resolve transactionally inside catalogue; cross-context grant changes are rechecked at subsequent privileged boundaries.

Deploy API and outbox publisher independently if required, sharing catalogue ownership only. Use tenant-indexed queries and opaque cursor pagination; an operated readiness boundary must check database/migration compatibility; the frozen foundation readiness route remains closed. Track revision conflicts, duplicate-command rates, authorization failures, outbox age and request latency. Logs include IDs and correlation, with intent bodies redacted. Recover revisions, command receipts and outbox consistently so restore cannot invent a new revision for an acknowledged command. RPO/RTO and payload limits are agreed in P00.05.

## Verification and delivery

P03.01/P03.02 implement aggregate invariants; P03.03 implements concurrency/atomicity; P03.04 delivers console create/edit/history; P03.05 verifies R04–R07 and R19 with Q01. P00.02/ADR-013 must resolve associations before schema lock; P01.03 supplies the contract framework.

Acceptance cases: create a two-workload application across two domains; reject foreign-tenant or retired references; preserve unsupported requested capability; reject dependency-order cycles; allow valid reply-flow edges; reject stale edit; deduplicate lost-response retry; reject key/payload mismatch; prove rollback when outbox persistence fails; deny revoked/cross-tenant history access; regenerate comparison from immutable versions after restart. Integrated evidence requires the actual governance contract and independent PHP/Python schema consumption. None of these tests proves native platform support.

## Context source ownership and code control

Owned source root: `services/catalogue/app/`. Application/deployment identity, workload/domain associations and immutable intent capabilities. Eloquent models may own revision and transition invariants. Actions coordinate authorization, tenant-scoped reads and writes, and the local transaction that commits a revision with its outbox records.

Use the [context code structure](../architecture/context-code-structure.md), [context registry](../../architecture/context-map.yaml) and [code-control policy](../engineering/code-control.md). This service owns its own `App\` namespace. Organize business behavior in `app/Domain/<Capability>/` and use cases in `app/Application/<Capability>/Actions/`, with `handle()` as the Action entrypoint. Keep external adapters in `app/Infrastructure/` and controllers, requests, jobs, listeners, policies and providers in normal Laravel directories. Domain code cannot depend on Application or Infrastructure; Eloquent and Laravel facilities remain available under [ADR-024](../decisions/adr-024-pragmatic-laravel-domain-convention.md). Same-context capabilities may collaborate directly; repositories and DTOs require a concrete reason. Public API/event schemas define cross-service access, and internal models, use cases and migrations remain private.

The service owner reviews source/dependency changes and maintains legal/forbidden import fixtures, contract consumers and isolated build inputs. Runtime data-access denials remain separate tests. Registration or a static check does not grant a worker additional native authority.

## P01 messaging increment

The [transactional messaging foundation](../implementation/p01-messaging.md) adds a
service-owned reference fact/outbox (Catalogue) and inbox/projection (Planning).
It exposes no product API or authorization decision. See that record for the exact
contract, retry, isolation and verification scope.

## P02 admission foundation

The [service delegation increment](../implementation/p02-service-delegation.md)
registers Catalogue-owned current-authority middleware and its verified-HTTPS
Governance client. P03 now binds that guard to actual application/reference routes with owned tenant/resource predicates. The original P02 protected synthetic-route results retain their narrower scope; P03 supplies live application evidence.

## P03 runtime contract

[Catalogue v1](../../contracts/openapi/catalogue-v1.0.1.json) and [the intent schema](../../contracts/schemas/catalogue/intent-v1.json) define the implemented wire surface. Separate `reference.read`/`reference.write` actions give tenant administrators reference administration without implicitly granting application authoring; ordinary application roles may read references. The requested service/data owners must be active Governance members in the admitted scope. Reference sharing is explicit; a non-shared WSD/domain cannot be used by another application's current deployment.

The Console uses contract-generated operation descriptors and exact response validation. Browser credentials and domain database access stay out of that client. The [P03 record](../implementation/p03-catalogue.md) distinguishes passing automated campaigns from outstanding operator and independent acceptance.

The original `catalogue-v1.json` artifact is retained unchanged as published history, but its 1.0.0 document omitted required tenant path declarations. Use 1.0.1 for generation and validation. API routes and accepted business command shapes are unchanged. [The correction record](../../verification/p03/corrections.md) retains the failed specification and immutable-artifact checks.

All accepted integer intent values are within ±9,007,199,254,740,991 so PHP, Python and browser clients can preserve them exactly. Use text for longer numeric identifiers. The Console preserves boolean/integer/text requirement types, nullable dependency ports and unsupported mandatory controls. Runtime queries have a 5-second statement, 3-second lock and 15-second idle-transaction limit; the outbox publisher applies its narrower statement deadline. [The operating procedure](../operations/runbooks/catalogue.md) describes trust, migrations, retry and retained event delivery.
