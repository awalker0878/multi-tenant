# Data, messaging and background execution

Owners: context engineering, lifecycle and SRE; security reviews scope and replay controls. This is the implementation standard for the proposed service boundaries in [ADR-006](../decisions/adr-006-service-owned-persistence.md), [ADR-007](../decisions/adr-007-durable-workflow-engine.md) and [ADR-008](../decisions/adr-008-domain-event-transport.md). It does not select an unresolved queue driver, broker or database topology. Framework behavior below was checked against Laravel 13 documentation on 2026-10-04; the constraints applied to this product are project design decisions.

## 1. Service data ownership and tenant integrity

Each context owns its tables, migrations, database credentials and operational data dictionary. PostgreSQL is the proposed relational baseline; physical cluster sharing does not permit cross-context table access. Other contexts consume an owner API or explicitly versioned projection, with its source revision and freshness. Reporting and the console cannot join private databases directly. Runtime roles cannot migrate schemas or administer other services.

Every table is classified as tenant-owned, explicitly shared reference data or service operational state. The classification records owner, key, relationships, classification/residency, retention, deletion behavior, indexed access paths and recovery group. A nullable tenant column must not silently mean global access. Shared records require a separately authorized access path.

| Invariant | Required implementation treatment |
| --- | --- |
| Tenant identity | Resolve the tenant from verified actor/delegation context; scope reads and writes before loading a resource. Reject a conflicting body, route or message tenant |
| Tenant-local uniqueness | Express uniqueness in database constraints including `tenant_id`, such as `(tenant_id, application_name)` where that is the approved domain rule. Request validation improves feedback but cannot prevent races |
| Same-context relationships | When both rows are tenant-owned, constrain `(tenant_id, parent_id)` to a unique `(tenant_id, id)` on the parent. Keep Eloquent's supported single-column model primary key; composite database constraints do not require composite Eloquent primary keys |
| Cross-context relationships | Store an opaque owner-issued identifier and the necessary revision; validate through the owner contract. Do not introduce cross-service foreign keys or model relationships |
| State transitions | Enforce legal transitions in the application action and protect concurrent writes using a version precondition or transaction/row lock. Translate conflicts into the contract's stable conflict response |
| Scope helpers | Eloquent scopes reduce omissions but are not the authorization boundary. Policies and explicit tenant predicates cover route binding, raw queries, bulk actions, exports and background work |
| Deletion and retention | Specify cascade/restrict behavior deliberately. Soft deletion does not delete retained personal data or create an evidence retention policy; define purge, legal hold and restoration consequences |

PostgreSQL supports compound unique and foreign-key constraints; referencing columns need an index review because declaring a foreign key does not create their index automatically. Test the selected schema against the real PostgreSQL major, including null semantics, concurrency and restore, rather than relying on SQLite behavior. Optional row-level security requires an ADR covering privileged roles, connection pooling and session-context cleanup; it does not replace application policy. [PostgreSQL constraints](https://www.postgresql.org/docs/18/ddl-constraints.html)

## 2. Transactions, durable publication and idempotency

Keep transactions short and restricted to the owning database. Laravel can retry a transaction after deadlock; therefore its callback must be safe to repeat. Do not call native APIs, send messages, write external objects or send mail from that callback. Use an immutable operation identity created before the callback and reuse it through retries. Critical domain persistence, audit intent and outbox insertion commit together. [Laravel database transactions](https://laravel.com/docs/13.x/database#database-transactions)

`after_commit`/`afterCommit()` defers queue dispatch until the enclosing database commit. It avoids a worker reading uncommitted state; it does not atomically commit that database change with an external broker publish. This product therefore requires a transactional outbox for required domain notifications and accepted asynchronous commands. A post-commit callback may wake the relay as an optimization; periodic durable scanning must recover a lost wake-up. [Laravel queues](https://laravel.com/docs/13.x/queues#jobs-and-database-transactions)

The outbox/inbox protocol is a project-specific application of the [transactional outbox pattern](https://microservices.io/patterns/data/transactional-outbox.html):

1. The producer commits the domain change and an outbox record with stable event/command ID, schema version, tenant/scope, aggregate ID/revision, correlation/causation IDs, occurrence time and minimal payload. Do not embed bearer credentials.
2. A bounded relay claims records with a recoverable lease, publishes and records its observation. A crash between publication and acknowledgement can cause duplicates; transport acknowledgement is not a consumer or native-effect success receipt.
3. The consumer validates authenticated producer, schema, tenant/scope and supported revision. It inserts the stable message ID into a uniquely constrained inbox and applies its local state transition in one transaction. A duplicate commits no second transition.
4. If the consumer must call another service or initiate lifecycle work, its transaction persists another durable command/outbox record. Cross-service effects are not performed inside the inbox transaction.
5. Reconciliation monitors oldest unpublished age, backlog, repeated failures and sequence gaps. Retries preserve identity. Retention covers the longest admitted replay/restore interval; pruning is coordinated with release support and recovery watermarks.

Messages are ordered only within explicitly defined aggregate streams. A consumer detects old revisions and gaps, records the decision and refreshes the owner state or holds the dependent work. Do not assume global ordering across broker partitions, queues or concurrent consumers.

Command idempotency uses a durable service-owned record scoped by tenant, actor/client authority and operation. Store the canonical request digest and resulting operation ID; the same key with a different request conflicts. Concurrent repeats return the existing operation only after authorizing the caller to read it. Define expiry against the retry/reconciliation window and reject unsafe reuse. Database uniqueness and conditional state transitions protect this record; a cache lock alone is insufficient.

Neither unique jobs nor an inbox make remote effects exactly once. Lifecycle remains responsible for the operation ledger, effective fencing and independent observation when a native response is lost. An outcome-unknown operation stays held until reconciliation identifies a safe next action.

## 3. Eloquent and query contracts

Use Eloquent within the owning context's `Infrastructure/Persistence` adapters. Domain aggregates and Application use cases depend on their own types and ports, with explicit mapping to Eloquent persistence records. Application query handlers depend on read ports; Infrastructure implements optimized Eloquent/SQL queries and returns owned DTOs. Group repositories around aggregate consistency boundaries rather than generating a generic repository for every table. The [context structure](../architecture/context-code-structure.md) owns layer placement and allowed imports.

- Construct explicit field maps from validated input. Tenant ID, owner ID, approval status, grants, evidence status and internal state are assigned by authorized application actions, not by mass assignment. Use a deliberate model allowlist and fail on silently discarded attributes in development/tests. [Eloquent mass assignment](https://laravel.com/docs/13.x/eloquent#mass-assignment)
- Select required columns, eager-load only the necessary relationships and their fields, and use aggregate queries instead of loading collections to count them. Enable lazy-loading violations in development/tests; production handling must be chosen and observed rather than silently accepting growing query cost. [Eloquent relationships](https://laravel.com/docs/13.x/eloquent-relationships#preventing-lazy-loading)
- Use explicit API Resources or presentation DTOs for response fields. A hidden model field list is not a complete response schema. Conditional relationship output must not trigger unplanned queries or disclose data the caller cannot access. [API Resources](https://laravel.com/docs/13.x/eloquent-resources)
- Bound page size, filter count, search length, exported rows and query duration. Allowlist requested sort/filter columns; parameter binding does not make a user-selected SQL identifier safe. Prefer cursor pagination for large ordered feeds when a stable unique ordering is available; use offset pagination where page-number navigation and measured cost justify it. Cursor tokens never grant access. [Pagination](https://laravel.com/docs/13.x/pagination)
- Process large updates/backfills in resumable batches with a stable key or captured watermark. Do not use offset iteration over a result set that the operation changes. Keep database connections and transactions bounded while streaming exports.

Each service's high-volume endpoint records a query budget: representative tenant sizes, concurrent requests, maximum page/payload, expected query count, cumulative database time, memory and response target. Measure with production-like synthetic distributions, including a large tenant and skewed relationships. Review query plans and missing indexes; add indexes for proven access patterns, including tenant predicates. Do not adopt a universal query-count target or cache an inefficient unbounded query.

Use the writer or an explicitly consistency-qualified path for read-after-write confirmation and authorization-sensitive state. A lagging read replica or projection cannot establish that a grant, revocation or operation transition is current.

## 4. Online schema evolution and backfills

Each service owns a migration history and a release-specific migration plan. A deployment runs one controlled migration job with a dedicated database role; application replicas do not all migrate on startup. If Laravel `migrate --isolated` is used, all participants require the same reliable lock store, and a zero exit status must be followed by verification of the expected migration/schema state: a competing invocation can exit successfully without applying migrations. [Laravel migrations](https://laravel.com/docs/13.x/migrations#isolating-migration-execution)

| Stage | Required work and release condition |
| --- | --- |
| Expand | Add a shape compatible with both supported application versions. Review table size, lock level/duration, lock/statement timeout, disk headroom and replication effect before production execution |
| Backfill | Run a separate bounded, resumable job with tenant scope, stable progress, idempotent batches, rate limit and cancellation. Record counts, invalid rows and checksums/invariants; never hide a large rewrite inside ordinary request handling |
| Transition | Deploy compatible reads/writes; when dual writes are needed, specify their single authoritative source, same-service consistency and reconciliation. Compare old/new representations before switching reads |
| Validate | Prove completeness and constraints, assess tenant-negative cases and confirm that old instances/jobs cannot write an unsupported shape |
| Contract | Wait for rollback, event replay and retained workflow compatibility windows. Remove old shape only in a separately reviewed release step with the irreversible boundary recorded |

For PostgreSQL concurrent index creation, assess its transaction restrictions, failure cleanup and resulting index validity. A concurrent build can leave an invalid index; application readiness requires the expected valid schema, not only a migration journal entry. The selected PostgreSQL version's behavior and rollback/repair procedure belong in the migration record. [PostgreSQL CREATE INDEX](https://www.postgresql.org/docs/18/sql-createindex.html)

Migration acceptance includes a populated source-version database, concurrent reads/writes, interruption/resume, bounded locks and old/new application coexistence. A `down()` method does not demonstrate that destructive data conversion is safely reversible. Follow the [upgrade procedure](../operations/runbooks/upgrade.md) and publish the actual compatibility boundary.

## 5. Queue authority, payloads and retries

| Mechanism | Appropriate responsibility | Boundary |
| --- | --- | --- |
| Laravel local jobs | Bounded context-owned projection refresh, document/export generation, notifications and outbox relay work | No independent native orchestration, approval authority or second lifecycle state machine |
| Domain event transport | Durable delivery of versioned facts and explicit commands between owners | Delivery or replay does not approve an operation; consumer validates current authority where required |
| Temporal/lifecycle | Durable cross-service/native process, waits, recovery coordination and compensating actions | Native effect admission remains subject to current scope, qualification, operation ledger and fencing |

Job chains and batches may organize context-local work; they do not replace the selected Temporal workflow authority. A queue message carries stable IDs, payload/schema version, tenant/scope, expected domain revision, actor/delegation reference and correlation context. It carries neither a captured HTTP request nor long-lived credentials. Reload resources through the owning tenant scope and apply the execution authority appropriate to the message's purpose. Laravel's queued-model restoration does not retain earlier relationship constraints; this project prefers explicit scalar identifiers over serialized model graphs for security-sensitive jobs. [Queued relationships](https://laravel.com/docs/13.x/queues#queued-relationships)

Distinguish an unexecuted command from a committed fact. A queued command, export disclosure or privileged effect requires current permission and its applicable admission conditions at execution or retrieval. Projection updates, audit retention and evidence custody for an already committed fact run under the receiving service's current scoped authority: validate producer/provenance, tenant, schema and the consumer's permitted purpose, while retaining the original actor for accountability. Later revocation of that actor does not erase the fact or silently prevent required custody and projection convergence. Processing the fact grants no new user authority; any new command, disclosure or native effect it initiates must pass its own current authorization checks.

The implementation records a policy per job class: owner, queue/driver, fair-share/rate limit, admission preconditions, retryable errors, maximum attempts/elapsed retry window, backoff/jitter, job timeout, external request timeouts, redelivery interval, lock expiry, failed-job retention, replay authority and observability. Split slow work from latency-sensitive work and bound concurrency so a large tenant cannot exhaust every worker or database connection.

Set external connect/read deadlines within the job's execution budget. The worker/job timeout must precede redelivery with a safety margin: database/Redis-style Laravel queues use `retry_after`, while SQS uses its visibility timeout. Process/container shutdown grants must allow the bounded drain strategy to complete. Verify these relationships under pauses, crashes and slow dependencies. [Laravel timeout ordering](https://laravel.com/docs/13.x/queues#job-expirations-and-timeouts), [SQS visibility](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-visibility-timeout.html)

Transient dependency failures receive bounded retries. Invalid schema, denied authority and permanently invalid references become actionable terminal/held records. Exhausted jobs enter the selected failed-job/dead-letter path with a redacted cause and alert. Operator replay requires a corrected cause, current authorization, compatible code/schema and the same business operation identity. Never bulk-retry unknown native outcomes or erase failures to clear a dashboard.

Use separate durable queues/retention from disposable cache data. Encryption of a job payload, if selected, does not remove tenant validation, queue ACLs or secret minimization requirements. Replay and restore tests must include deleted resources, revoked actors, stale revisions and an old job reaching a new worker.

## 6. Cache and distributed lock discipline

Cache keys include environment, owning service, schema/version namespace, tenant and relevant resource revision; include actor/grant scope when output differs by permission. For example, a synthetic key shape is `env:catalogue:v1:tenant-id:application-id:revision:projection`. Explicit shared-reference caches use a separate namespace and access policy. Cached output must not cross tenant or user visibility boundaries.

Define freshness, invalidation, maximum staleness and rebuild behavior per cache. The database/owner API remains authoritative. Grant, revocation, approval, qualification and fencing checks cannot rely on an unbounded stale cache. A dependency failure holds privileged effects when current authorization cannot be established. Prevent stampedes with bounded rebuild work and test cold-cache load.

Laravel atomic locks need a shared compatible store across participants. Specify owner, resource scope, expiry, release ownership and stale-owner behavior. `ShouldBeUnique`, scheduler locks and `WithoutOverlapping` are concurrency aids, not exactly-once delivery or native fencing. Expired locks cannot stop a partitioned process that still holds external credentials. [Laravel cache locks](https://laravel.com/docs/13.x/cache#atomic-locks)

Separate disposable caches, coordination locks, sessions and durable queue/state where their loss policies differ. Do not call a whole-store flush during ordinary deployment: Laravel cache flush ignores key prefixes. Prefer versioned cache namespaces or targeted invalidation and retain durable coordination state. Cache failover must not silently move competing lock users onto independent stores. [Cache removal](https://laravel.com/docs/13.x/cache#removing-items-from-the-cache)

## 7. Scheduling and long-lived process isolation

Assign every scheduled task an owner, UTC schedule, allowed delay, scope, idempotency key, overlap behavior, run budget, alert and missed-run recovery. Use one scheduler ownership mechanism per environment: a deliberate singleton or distributed scheduling with a shared supported cache and named `onOneServer`/`withoutOverlapping` behavior. Locks reduce duplicate starts; the task's durable idempotency still protects reruns. Do not enable an orchestrator schedule and in-container cron for the same task. [Laravel scheduler](https://laravel.com/docs/13.x/scheduling#running-tasks-on-one-server)

Schedulers dispatch bounded context work or an authorized lifecycle request; they cannot bypass native admission. Pruning jobs respect evidence holds, inbox/outbox replay horizons, support windows and backup retention. Sub-minute scheduler processes must be interrupted/replaced during deployment so they do not continue executing the previous release.

At every request/job boundary, establish verified tenant and actor context, then clear it in a guaranteed cleanup path. Reset per-operation logging fields, locale/timezone overrides, database connection/session settings, cached policy results and temporary credentials after success, failure, cancellation and retry. Do not put tenant-specific mutable state in singletons/static properties or retain request objects in long-lived services. A missing tenant fails closed; it never reuses the preceding job's tenant.

Queue workers are long-lived even without Octane. Test alternating tenants on the same process, including an exception between jobs. Octane is an optional performance decision after profiling; if selected, its retained application state requires additional concurrency, memory-growth and request-isolation qualification. [Laravel Octane lifecycle](https://laravel.com/docs/13.x/octane#dependency-injection-and-octane)

## 8. Required verification evidence

| Scenario | Evidence required for the affected implementation |
| --- | --- |
| Two tenants use the same local name/ID inputs | Permitted independent records; cross-tenant relationship, route, export and job access denied |
| Concurrent identical/conflicting commands | One durable operation for a repeat; conflicting body under the same idempotency key rejected |
| Process crashes after domain commit, after publish and before consumer acknowledgement | Required message eventually delivered; duplicate consumption produces one local transition |
| Event gap or malformed payload | Defined hold/terminal response and alert; no unauthorized state transition |
| Actor revoked after enqueue or domain commit | Pending commands and disclosures obey current authority; committed facts still reach permitted audit/evidence/projection processing under service authority without regranting user access |
| Large tenant query/export | Bounded payload, memory, query count/time and fair worker consumption against its recorded budget |
| Backfill interrupted while old/new services write | Resumable progress, valid constraints, compatibility and no unbounded table lock |
| Timeout, redelivery and lost remote response | Documented timeout ordering; stable identity; uncertain external outcome held for reconciliation |
| Cache/lock outage or stale entry | No tenant bleed, privilege extension, duplicate native writer or unsafe failover |
| Alternating tenant jobs and requests in one process | No retained tenant, actor, locale, database or logging context after success/failure |
| Upgrade with queued jobs and scheduled work | Supported old payloads processed safely; old workers drained/replaced; scheduler ownership stays singular |

Attach observations to the affected phase package and qualification campaign; a checklist or passing mock alone is not integration evidence. Operational configuration, probes and drain procedures are defined in the [deployment model](../operations/deployment-model.md), [installation](../operations/runbooks/install.md) and [upgrade](../operations/runbooks/upgrade.md) procedures.
