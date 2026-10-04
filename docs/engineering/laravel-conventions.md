# Laravel context and code conventions

Owner: Engineering and Laravel context leads. Applies to Governance, Catalogue, Assurance and the Console composition boundary. Reviewed: 2026-10-04. Related delivery: P00.02/P00.03, P01.01/P01.03/P01.04 and all later Laravel feature packages.

Business code is organized by bounded context, dependency layer and capability. The [context code structure](../architecture/context-code-structure.md) is the canonical layout and allowed-dependency matrix; [code control](code-control.md) defines ownership and enforcement. Laravel supplies the framework host and adapters. A framework-wide `app/Models` or `app/Actions` grouping is no longer the business architecture for this project.

This stricter separation follows the user's requested enterprise context model. It is a project rule, not a claim that Laravel requires domain-driven design. It preserves the seven principal deployables and the existing PHP/Python split.

## 1. Separate the framework host from context code

Each Laravel deployable owns its `composer.json`, committed lockfile, `artisan`, `bootstrap/`, `config/`, `routes/`, `public/`, `database/`, `storage/`, `tests/` and image definition. Console additionally owns its frontend manifest, lockfile and build configuration. Conventional host paths remain available for deployment, configuration caching and framework lifecycle operations.

| Source destination | Required content |
| --- | --- |
| `services/<service>/src/Contexts/<Context>/Domain/` | Framework-free aggregates, invariants, domain values/events |
| `services/<service>/src/Contexts/<Context>/Application/` | Use cases, typed input/output, local transaction and dependency ports |
| `services/<service>/src/Contexts/<Context>/Infrastructure/` | Eloquent records/mappers, repositories, queries, transport and storage implementations |
| `services/<service>/src/Contexts/<Context>/Interfaces/` | HTTP, message, CLI and local-job adapters into the same use cases |
| `app/Providers/` and narrowly defined host glue | Binding, route/policy/command registration and framework initialization |
| `database/` | Context-owned migrations, development seeds and configured factories |
| `tests/` | Context/layer tests plus local contract and runtime integration checks |

Use `Product\Contexts\Governance\`, `Product\Contexts\Catalogue\` and `Product\Contexts\Assurance\` mapped only inside their owning applications. Console uses `apps/console/src/Contexts/Console/` and `Product\Contexts\Console\`; it has no business-service entities. Its domain layer is optional when no genuine console-owned invariant requires one.

Capabilities belong inside layers: `Domain/Applications/`, `Application/Applications/Commands/` and `Interfaces/Http/Controllers/`. Do not create a context, Composer package or service for every controller, aggregate or capability. Do not move business classes under `App\` to accommodate a generator default. Configure discovery explicitly or relocate and namespace generated files before merging them.

## 2. Enforce dependency direction

Domain depends only on owned Domain code and effect-free language primitives. Application depends on its own Domain/Application types and locally defined ports. Shared packages are excluded from these core layers in the initial policy. Infrastructure implements the ports. Interfaces calls application use cases and maps input/output. Host providers wire implementations. Context code does not import host `App\` classes.

Domain and Application must not import `Illuminate`, Eloquent, framework facades, request/session state, generated HTTP clients, provider SDKs or Infrastructure/Interfaces classes. Neither layer locates dependencies through the global container. Constructors expose collaborators; return types expose meaningful results or failures.

No service imports another service's internal namespaces, migration classes, ORM records or configuration. Contracts and generated clients are the integration boundary. Shared packages cannot carry mutable business entities or permission decisions. A new package requires an owner, consumers, dependency rules and release/compatibility impact before adoption.

Use the architecture dependency matrix and executable checks in code control. File paths alone are insufficient: imports, Composer autoload/package dependencies, generated sources and runtime wiring must agree with ownership. Within a context, review capability dependencies and cycles as well as layer direction.

## 3. Separate Domain models from Eloquent records

Domain aggregates encode accepted state transitions and invariants in pure PHP. Eloquent models live under `Infrastructure/Persistence/Eloquent/Models/` and map the context's tables, relationships, casts and query scopes. Mappers reconstruct valid domain state and persist allowed transitions. A domain entity never extends `Model` or returns a query builder.

Use a repository port at a meaningful aggregate consistency boundary where persistence is required. Avoid generic repository interfaces for every table and pass-through service chains. Read use cases use an application reader port implemented by bounded SQL/Eloquent projections; lists need not hydrate full aggregates. Both read and write adapters enforce tenant scope, concurrency requirements and explicit output shape.

Changes involving multiple owned records define their local consistency boundary in the application handler. Domain logic rejects invalid values and transitions; database constraints enforce storage uniqueness and referential integrity. Neither replaces the other. Cross-context references are IDs/versions/digests, not cross-database Eloquent relationships.

Preserve aggregate/mapping tests during schema evolution. Database-backed tests exercise races, stale revisions, tenant constraints and transaction failure using the selected production database engine. A fake repository cannot prove those properties. See [data and messaging](data-and-messaging.md).

## 4. Give use cases authority and transaction control

Controllers, Form Requests, queue entrypoints and Artisan commands are adapters. They translate permitted fields and establish verified actor/tenant/delegation context before invoking the same use case. A successful Form Request or Laravel policy is an early check; it does not authorize every nested reference or replace application authorization.

The application authorization port checks the current action/resource permission. Its infrastructure implementation calls Governance or the approved authority mechanism. Domain policies enforce product invariants independently of identity infrastructure. Domain code never fetches a token, inspects a session or resolves a remote grant.

A Catalogue revision handler coordinates current authority, durable idempotency, expected parent revision, domain associations and atomic revision/receipt/outbox persistence. The [worked command path](../architecture/context-code-structure.md#end-to-end-revision-command) defines the sequence. Transaction ports expose a local unit of work, not raw database connections; Infrastructure implements it on the owning connection.

Remote authorization/reference reads have declared freshness semantics and occur outside the database transaction. A retryable transaction closure contains repeatable local work only: no HTTP calls, mail sends, queue publication or native mutation. Stronger admission guarantees use the defined approval/reservation/fencing protocol, not a database transaction spanning services.

Idempotency includes tenant, principal/action scope and canonical request identity. The same key with changed intent is a conflict. Retrieving a prior receipt still requires permission to disclose it. Unknown external outcomes require reconciliation by the effect owner; database rollback cannot undo a provider write.

Native provisioning, migration, fencing and compensation belong to Lifecycle/Temporal and its owned workers. Laravel observers, controllers and local jobs cannot create an alternate native execution path. Internal domain events express local facts; outbox mapping produces the public event contract.

## 5. Register adapters explicitly

Host providers bind application ports to infrastructure implementations. Use `register` for bindings and `boot` for framework registration after providers are available. Providers load safely during HTTP, workers, CLI, tests and cache construction. They do not read business state, start migrations, call remote services or acquire native credentials during bootstrap. See the official [provider lifecycle](https://laravel.com/framework/docs/13.x/providers).

Custom context paths need deliberate registration of routes, commands, policy mappings, listeners and factories. Test actual boot/discovery behavior rather than assuming defaults find classes outside `app/`. Keep routes declarative and delegate to interface controllers. Interface policies use application authorization/resource references instead of directly querying Eloquent records.

Framework abstractions belong at adapters. Facades may be used inside focused Infrastructure or Interfaces code where allowed by their responsibilities; they are prohibited in Domain/Application. Laravel's [container](https://laravel.com/framework/docs/13.x/container) supplies constructor injection and scoped bindings. A provider may depend on both port and implementation; application handlers may not.

Tenant, actor, authority, request and correlation context is established for each request/job and cleared after success or failure. It is not static or a process-lifetime singleton. Scoped bindings help with framework-managed lifecycles; custom loops and library caches still require reset and alternating-tenant tests.

## 6. Types, names and formatting

Follow [PSR-4](https://www.php-fig.org/psr/psr-4/) namespace/path correspondence and case-sensitive filenames. Use specific names such as `CreateIntentRevisionHandler`, `GovernanceAuthorization` and `ApplicationReader`. Avoid catchall `Helper`, `Manager` and `BaseService` classes that obscure ownership. Public field/event names follow the schema.

First-party PHP declares parameter, return and property types, strict scalar typing where applicable, explicit nullability, and bounded enums/value objects for states, units and identifiers. `declare(strict_types=1)` does not validate a payload or authenticate a tenant; boundary validation remains explicit. Application DTOs contain permitted values/references, never `Request`, Eloquent models, query builders or anonymous arrays passed through a use-case chain.

PHPDoc generics/shapes describe collections or types that native PHP cannot express, primarily at adapters. Avoid unsafe casts, broad ignored-error patterns and static-analysis baselines added to accept new violations. Narrow exceptions follow code-control review and expiry rules.

Use one pinned, committed Pint policy with the `laravel` preset across Laravel services, including context source paths. [Pint](https://laravel.com/framework/docs/13.x/pint) offers multiple presets; this choice does not claim exact conformance to every PHP-FIG rule. [PER Coding Style](https://www.php-fig.org/per/coding-style/) is the current style reference; PSR-2 is not the target. [Developer workflow](developer-workflow.md) owns versions; [testing and CI](testing-and-ci.md) owns enforcement.

Comments preserve non-obvious invariant, trust and recovery reasoning. Avoid comments that restate code and magic conventions that hide control flow. Developers must be able to trace input through use case, ports, aggregate rules, transaction and output contract.

## 7. Keep public contracts independent of domain classes

Canonical schemas remain in `contracts/openapi/<service>.yaml`, `contracts/asyncapi/<service>.yaml` and `contracts/schemas/`, with fixtures under `contracts/fixtures/<service>/`, as defined by the [contract catalogue](../contracts/README.md). Generated clients and transport DTOs are schema artifacts. Infrastructure translates them into the consuming context's types. Publishing a PHP class does not establish a cross-language contract.

Interface resources serialize explicit application-result fields rather than an Eloquent graph. [Laravel API resources](https://laravel.com/framework/docs/13.x/eloquent-resources) supply transformation; versioned schemas own fields, relationships, pagination and permission semantics. Loaded data is not automatically authorized data. JSON:API does not silently replace the established problem/receipt protocol.

Infrastructure HTTP clients declare endpoints, identity, payload/page bounds, timeouts and retry budgets. Handle unsuccessful responses and map them to application failures: Laravel's [HTTP client](https://laravel.com/framework/docs/13.x/http-client) does not make a parsed response proof of success. Retry writes only under an idempotency/reconciliation contract. Coordinate retry budgets across proxy, client, queue and workflow layers.

Map expected domain/application failures to stable interface errors. Unexpected exceptions return a safe correlation reference with restricted diagnostics; never log failure then return success or an empty authorized dataset. Browser Inertia errors follow the [frontend](frontend.md) protocol. Event consumers validate schemas and source/scope, deduplicate durably and invoke use cases rather than mutating ORM records in listeners.

## 8. Prove the boundaries before feature expansion

P01 delivers a representative context path with port bindings, registration, typed command/query results, Eloquent mapping, current authority handling and durable outbox. P02/P03 extend it into real Governance/Catalogue behavior. Do not copy demonstration scaffolding into every capability without a use case.

Architecture proof includes rejected forbidden imports and unowned paths, case-correct autoloading, contract compatibility, cached bootstrap and tenant-context isolation. Runtime proof includes real transaction/idempotency races and alternate-entrypoint permission checks. Language-level enforcement examines dependencies beyond simple path/text validation.

Review ownership, authority, aggregate/transaction boundaries and contract impact before style details. Attach observed proof to the [coverage map](coverage.md) packages and gates. Data, security, frontend and deployment guidance continues to apply within this structure; a layered directory alone cannot establish correctness.
