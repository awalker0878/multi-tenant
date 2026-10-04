# Context and microservice code structure

Owner: Architecture and engineering leads, with each context owner. Reviewed: 2026-10-04. Applies to P00.02, P01.01/P01.03/P01.04 and all feature packages.

The product keeps six business bounded contexts and a Console composition boundary, each with its own service artifact, data ownership and public contracts. Inside each Laravel service, the user-selected [pragmatic Laravel DDD convention](https://dev.to/maiobarbero/pragmatic-domain-driven-design-in-laravel-with-laravel-boost-3bcm) organizes capabilities under `app/Domain` and `app/Application`, integrations under `app/Infrastructure`, and entrypoints in Laravel's normal directories. Eloquent remains part of the implementation. A capability is an area of behavior inside a context; creating one does not create a microservice.

This replaces the earlier PHP `src/Contexts` layout and framework-free core requirement. [ADR-024](../decisions/adr-024-pragmatic-laravel-domain-convention.md) records this direction. The [target architecture](target-architecture.md) defines service responsibilities; [code control](../engineering/code-control.md) defines ownership and enforcement. Python services retain their existing language-specific structure.

## 1. Contexts, capabilities and deployables

| Context or composition boundary | Principal deployable | Capability groups inside the boundary | Authoritative records and decisions |
| --- | --- | --- | --- |
| Console composition | `apps/console/`; Laravel/Inertia/Vue | Sessions, navigation, application views, review workspaces, operation views, evidence views | Browser sessions, presentation preferences and authorized page composition only |
| Governance | `services/governance/`; Laravel/PHP | Tenancy, membership, delegation, authorization, approvals, revocation | Tenant authority, grants, exact-plan approvals and separation-of-duties decisions |
| Catalogue | `services/catalogue/`; Laravel/PHP | Applications, deployments, intent revisions, workload definitions, domain associations | Requested application intent, immutable revisions, tenant-owned logical definitions |
| Inventory | `services/inventory/`; Python | Endpoint registration, discovery, normalization, observations, freshness | Registered targets and sourced observations of native state |
| Planning | `services/planning/`; Python | Requirements, capabilities, profiles, assessments, placement, plans | Explained eligibility and immutable proposals bound to exact inputs |
| Lifecycle | `services/lifecycle/`; Python/Temporal | Admission, jobs, workflows, operation ledger, fencing, reconciliation, managed bindings | Authority to perform admitted native effects and their actual outcomes |
| Assurance | `services/assurance/`; Laravel/PHP | Evidence custody, campaigns, qualification, acceptance, support publication | Attributable artifacts and scoped, independently reviewed support claims |

These names identify the initial ownership map; aggregate details remain in the [service specifications](../services/README.md) and [domain model](../product/domain-model.md). Catalogue `Application` means requested product intent, while Lifecycle may use an `ApplicationReference` to bind an operation. They do not share an `Application` entity class. A reference carries the required tenant, identifier, version and digest, not another service's persistence model.

Discovery pools belong to Inventory; privileged infrastructure, guest, shared-service and data-movement pools belong to Lifecycle. Laravel queue and verification processes use their owning service artifact, including Assurance verification; they do not introduce another site-worker source root. Process scaling, site placement or a separate worker image does not transfer aggregate ownership. Inventory observations and Lifecycle managed bindings remain distinct even when they describe the same native resource.

## 2. Repository and artifact boundaries

| Repository area | Required ownership and isolation |
| --- | --- |
| `apps/console/` | Independent Composer/frontend locks and image; frontend assets and server composition belong here |
| `services/<service>/` | Independent dependency lock, runtime bootstrap, tests, configuration, database migration ownership and image |
| `workers/inventory/`, `workers/lifecycle/` | Registered context-owned worker roots, with named pool roles, activity contracts and release compatibility |
| `contracts/openapi/<service>.yaml`, `contracts/asyncapi/<service>.yaml`, `contracts/schemas/`, `contracts/fixtures/<service>/` | Canonical versioned API/event schemas and fixtures owned by the producing context; retain the [contract catalogue](../contracts/README.md) paths |
| `packages/` | Explicitly approved generated clients or narrow technical libraries, each with an owner and consumer graph |
| `deploy/` | Process roles, policy, configuration interfaces and deployment manifests with deployment-owner review |
| `tests/` | Cross-service contract, integration and qualification suites; local tests remain with the owning service |
| `docs/` | Product meaning, decisions, engineering rules and delivery/qualification records |

Only the owning application's sources and declared package dependencies enter its build. Docker build access to the monorepo does not authorize importing neighboring service code. PHP Composer autoload mappings and Python package configuration expose only the registered local context; path dependencies on another service are forbidden. Generated clients consume published schemas and never include the producer's Domain, Application, Eloquent models or migrations.

An API, event publisher, consumer and local queue worker can be separate process roles of one service artifact. The principal deployment count therefore remains seven. New context extraction requires distinct ownership, data, contract and release responsibilities, plus an ADR and changes to the ownership/control registry. A large folder or another container is insufficient justification.

## 3. Laravel capability layout

All four Laravel applications use their own local `App\` namespace. The enclosing service directory identifies the bounded context; duplicating the service name inside every PHP namespace adds no ownership guarantee. The paths below are relative to `services/catalogue/`, with the same convention in Governance, Assurance and `apps/console/`.

| Location | Catalogue responsibility | Dependency constraint |
| --- | --- | --- |
| `app/Domain/Applications/Models/` | Owned application records, relationships and valid state transitions | May use Eloquent; no Application, Infrastructure or delivery dependencies |
| `app/Domain/IntentRevisions/` | Revision models, dependency-graph values, invariant failures and local facts | Can collaborate with other Catalogue capabilities |
| `app/Application/IntentRevisions/Actions/` | Revision use cases, actor authorization, concurrency, persistence and transaction coordination | May use Domain, Eloquent, `DB`, `Gate` and consumer-owned contracts |
| `app/Application/IntentRevisions/Data/` | Structured revision input when its fields justify a named value | Optional; transport-independent, with a `Data` suffix |
| `app/Application/IntentRevisions/Contracts/` | Capabilities required from remote authority or reliable event delivery | Add only for a real dependency boundary |
| `app/Infrastructure/` | Governance clients, event publication, specialized persistence and other external adapters | Implements contracts required by its consumer |
| `app/Http/Controllers/`, `Requests/`, `Resources/` | HTTP authentication integration, validation, invocation and response presentation | Meaningful mutations invoke Actions; scoped simple reads can use Eloquent |
| `app/Console/Commands/`, `app/Jobs/`, `app/Listeners/` | CLI, queue and event entrypoints | Establish trusted scope and invoke the same Actions |
| `app/Policies/`, `app/Providers/` | Laravel authorization policies and registration/bindings | Policies authorize actors; providers bind implementations and register models/policies |
| `database/migrations/`, `database/factories/`, `database/seeders/` | Catalogue schema, test factories and controlled development data | No foreign-service tables or shared database authority |
| `tests/Architecture/`, `tests/Unit/`, `tests/Feature/` | Dependency rules, pure invariants and framework/database behavior | Tests cover the owning service and its published contracts |

Create only the directories and classes a feature needs. Capability names follow the product language in the service specification. `Models`, `Events`, `Exceptions`, `ValueObjects` or `Contracts` subdirectories are useful when they clarify actual code; they are not a checklist of empty folders. Product models belong to their relevant capability. During scaffolding, place any service-owned authentication model in the appropriate identity capability and configure its framework references explicitly.

Retain normal Laravel bootstrapping, configuration, routes, storage, public assets and Composer files. The runtime autoload mapping is service-local:

```json
{
  "autoload": {
    "psr-4": {
      "App\\": "app/"
    }
  },
  "autoload-dev": {
    "psr-4": {
      "Tests\\": "tests/",
      "Database\\Factories\\": "database/factories/",
      "Database\\Seeders\\": "database/seeders/"
    }
  }
}
```

Thus `App\Domain\Applications\Models\Application` resolves only to Catalogue's `app/Domain/Applications/Models/Application.php` in the Catalogue artifact. Governance can independently use `App\Domain` without sharing that code. Composer mappings, dependency manifests and build inputs must prevent either application from loading the other's `app/` tree. A broad monorepo autoloader is forbidden.

## 4. Dependency rules within Laravel services

| Importing area | Allowed responsibilities | Forbidden dependencies or behavior |
| --- | --- | --- |
| Domain | Owned business models, invariants, values and facts; Eloquent; collaboration across local capabilities; a consumer-owned contract when justified | Application, Infrastructure, HTTP/CLI/job/listener/policy/provider classes, transport objects, HTTP clients and vendor SDKs |
| Application | Domain behavior, explicit actor authorization through Laravel gates/policies, local Eloquent persistence, transactions and event coordination | Concrete Infrastructure adapters, delivery classes, `Request`/`Response`, another service's private code |
| Infrastructure | External integrations, technical persistence and implementations of Domain/Application contracts | Taking ownership of another context's business rules or bypassing its public API |
| Laravel entrypoints | Authenticate or verify delegated authority, validate inputs, invoke Actions, present outcomes; bounded authorized reads | Business mutation workflows copied into controllers/jobs/listeners; native provider mutation |
| Policies | Evaluate actor/resource permission with verified scope and the approved authority mechanism | Domain model references back to policy classes; universal administrator bypass of tenant or separation-of-duties rules |
| Providers | Bind consumer contracts to adapters; register policies, events and framework hooks | Business decisions, remote calls or acquisition of native credentials during bootstrap |
| Shared packages | Reviewed schema clients or narrow technical utilities with explicit consumers | Service classes, mutable business aggregates, permission decisions or cross-service persistence models |

Framework dependencies are evaluated by responsibility. Using `Model` in Domain or `DB` and `Gate` in Application is expected. Calling a provider SDK from an Action, returning an HTTP response from a model, or resolving an Infrastructure class through `app()` still violates the boundary. String bindings and custom facades must not conceal those dependencies. The currently registered shared transport clients and technical integration packages remain adapter dependencies; this project rule does not exclude Laravel itself from Domain/Application.

Capabilities inside a service can use each other's models and behavior directly. Catalogue Applications and IntentRevisions do not need HTTP calls or repository interfaces between them. An Action coordinates local writes that must succeed together; its model methods enforce the relevant state and value rules. Review cycles and unclear rule ownership when collaboration grows, without treating every capability as a bounded context.

Eloquent querying and saving are the default persistence approach. A repository is warranted by an actual persistence problem, such as a specialized store or replacement seam; its contract belongs to the consumer. Do not require record-to-aggregate mappers, generic CRUD repositories, transaction ports, query wrappers or Data objects for scalar identifiers. Public API resources still select explicitly authorized fields, even when an Action returns an owned Eloquent model.

## 5. Catalogue implementation reference

The first Catalogue slice creates an immutable intent revision with a current-revision pointer, durable receipt and publication intent. These are planned destinations for the slice, not a claim that application code exists.

| Path below `services/catalogue/` | Responsibility |
| --- | --- |
| `app/Domain/Applications/Models/Application.php` | Eloquent application entity; accepted lifecycle and revision association rules |
| `app/Domain/IntentRevisions/Models/IntentRevision.php` | Owned immutable revision data and relationships |
| `app/Domain/IntentRevisions/ValueObjects/DependencyGraph.php` | Workload reference validation and cycle rejection |
| `app/Domain/IntentRevisions/Exceptions/RevisionConflict.php` | Meaningful business failure independent of HTTP |
| `app/Domain/IntentRevisions/Events/IntentRevisionCreated.php` | Local revision fact; not itself the public event schema |
| `app/Application/IntentRevisions/Actions/CreateIntentRevision.php` | Public `handle()` coordinates actor/scope, idempotency, concurrency and local writes |
| `app/Application/IntentRevisions/Data/CreateIntentRevisionData.php` | Validated structured workload input and expected revision; useful because this command has several related fields |
| `app/Application/IntentRevisions/Contracts/GovernanceAuthority.php` | Required remote authorization/reference information with scope and freshness |
| `app/Application/IntentRevisions/Contracts/RevisionPublication.php` | Stage a contracted event durably with the revision transaction |
| `app/Infrastructure/Governance/GovernanceAuthorityClient.php` | Bound, authenticated Governance contract client |
| `app/Infrastructure/Messaging/OutboxRevisionPublication.php` | Event mapping and atomic publication-intent persistence on Catalogue's connection |
| `app/Http/Controllers/CreateIntentRevisionController.php` | Invoke the Action and map its result/failure to the API protocol |
| `app/Http/Requests/CreateIntentRevisionRequest.php` | Input shape, permitted fields and bounds |
| `app/Http/Resources/IntentRevisionResource.php` | Explicit schema fields and authorized relationships |
| `app/Policies/ApplicationPolicy.php` | Actor permission for Catalogue application operations |
| `app/Providers/AppServiceProvider.php` | Contract bindings and explicit policy/factory/model registration where needed |
| `database/migrations/` | Revision uniqueness, tenant references, receipts and outbox storage |
| `database/factories/` | Factories mapped to capability models for tests |
| `tests/Feature/IntentRevisions/` | Direct Action and entrypoint tests with the production database engine where behavior depends on it |

The two contracts above exist because remote authority and durable external publication are real boundaries. They do not justify an interface for every table or Laravel facility. The outbox implementation must participate in the same owned connection and transaction; an adapter that uses another connection cannot satisfy the atomicity requirement. The exact transaction semantics follow ADR-013 and [data and messaging](../engineering/data-and-messaging.md).

### End-to-end revision command

1. The HTTP entrypoint authenticates the caller and obtains trusted tenant/actor context separately from the payload. Its Form Request validates shape and bounds. A user-supplied tenant or privilege field cannot establish authority.
2. The controller passes the explicit actor, trusted scope and meaningful input to `CreateIntentRevision::handle()`. CLI and queue entrypoints invoke that same Action using independently verified authority.
3. The Action loads the tenant-scoped application, obtains any required current Governance decision through its contract, and authorizes the operation through `Gate::forUser($actor)` and the registered policy. Define freshness and resource/version binding before starting local writes. Required remote reads occur outside retryable database transaction closures.
4. Inside `DB::transaction`, the Action checks the durable idempotency key and canonical request identity, locks or conditionally updates the scoped records, and verifies that the authorized target/reference versions still match. A receipt is disclosed only to a currently authorized caller. Changed payloads or stale revisions produce a conflict.
5. Owned Eloquent model behavior and value objects enforce associations, workload identity, revision immutability and graph rules. The Action saves the allowed state changes and coordinates the revision, current pointer and receipt writes.
6. The Action stages publication through `RevisionPublication` in that same transaction. No remote message send or provider mutation occurs in the closure. Any transaction retry repeats only local, repeatable work.
7. After commit, the controller returns the contracted resource/receipt. An after-commit event can wake publication, but the outbox supplies recovery if the process stops before that wake-up or delivery. Laravel after-commit timing alone is not durable cross-service delivery.
8. Planning consumes the published event through its own authenticated contract boundary, deduplicates with its own effects, and resolves the authorized intent contract. It never imports Catalogue models or treats the event as execution authority.

A local transaction cannot make a Governance decision and Catalogue commit globally atomic. Each action documents acceptable decision freshness, revocation races and conflict handling. Exact-plan approval and native-effect admission retain the stronger Governance/Lifecycle protocol; a new Catalogue revision does not authorize a provider write.

## 6. Authorization, entrypoints and simple reads

Policies remain in `app/Policies`; providers register mappings to capability models. Models do not import their policies. Authentication establishes who is calling; the Action checks what that explicit actor may do to the scoped resource. Model methods check whether the transition itself is valid, regardless of entrypoint. Jobs and listeners cannot rely on a previous browser check.

A simple application list or detail controller may query its owned Eloquent models directly when it authorizes the read, scopes every lookup to the trusted tenant and permitted resource, bounds pagination/eager loading and emits an explicit Resource. Add an Action when the read acquires meaningful business behavior, multi-step coordination or another reusable use case. Do not create an Action and reader interface solely to return one record.

Factories stay in `database/factories`. Capability model moves require policy registration, factory/model mappings, route binding and relationships to be checked together. Event/listener/queue registration follows Laravel conventions; meaningful listener and job work invokes Actions. Sensitive mutations remain explicit and auditable rather than hidden in model observers.

## 7. Python services and site workers

Python contexts use `services/<service>/src/<service>/{domain,application,infrastructure,interfaces}/`. Domain and Application do not import web frameworks, ORM sessions, platform SDKs or Temporal APIs. Typed ports describe persistence, authority, dispatch and observations. Infrastructure implements them; HTTP/message/CLI interfaces adapt trusted input and invoke use cases.

| Lifecycle destination | Responsibility |
| --- | --- |
| `src/lifecycle/domain/operations/` | Operation identity, admissible transitions, fencing requirements and outcome vocabulary |
| `src/lifecycle/application/admission/` | Current authority, exact-plan and qualification checks; durable admitted-job command |
| `src/lifecycle/application/ports/` | Ledger, transaction, authority, workflow dispatch and native observation contracts |
| `src/lifecycle/infrastructure/persistence/` | Owned journal, reservations, transaction and outbox adapters |
| `src/lifecycle/infrastructure/temporal/` | Deterministic workflows, history/version compatibility and dispatch adapter |
| `src/lifecycle/interfaces/http/` | API authentication, validation and application entrypoints |
| `workers/lifecycle/` | Named execution-pool entrypoints, bounded provider adapters and runtime configuration |

Temporal workflow code is an infrastructure adapter with explicit orchestration and determinism constraints. It coordinates application-defined operations through activities; workflow code does not make database/provider calls. An activity establishes current scoped authority and invokes its owning execution use case. Provider adapters perform effects under Lifecycle's ledger/fencing protocol. An ordinary queue retry cannot replace fencing, reconciliation or cutover semantics.

Remote workers report through authenticated context contracts and have no independent database authority over Lifecycle or Inventory. Reused same-context code is an explicit immutable/versioned package or build input, with its compatible context artifact recorded. Import rules may permit the owning context's code in that artifact; they never permit runtime sibling-directory imports, cross-context reuse or extra data authority. Layer direction still applies: entry interfaces call Application; Infrastructure adapters implement ports; composition wires both without Interfaces/Infrastructure mutual imports. Native SDKs belong only in registered provider adapter areas. Import contracts and build checks cover both service and worker roots.

## 8. Console composition

Console applies the same PHP convention within `apps/console/app/`. Its Application capabilities compose authorized task views through consumer-owned client contracts; `app/Infrastructure/` implements those contracts. Inertia controllers, requests and Resources/presentation mapping belong in `app/Http/`. Domain is used only when Console owns a real invariant, such as presentation-preference behavior; it does not duplicate Catalogue application entities.

Vue capabilities live under `resources/js/contexts/<context>/features/<capability>/` and expose reviewed `contexts/<context>/index.ts` entrypoints. Pages and journeys compose those entrypoints. The [frontend conventions](../engineering/frontend.md) define private/shared import rules. Console cannot query business-service tables, approve a plan independently or acquire native credentials.

Page composition has bounded fan-out/timeouts and explicit partial/unavailable states. Mutations call the owning service with current delegation and preserve its receipt/idempotency semantics. A browser session never becomes universal service authority.

## 9. Code control and acceptance

Ownership, required review, path rules, dependency manifests, schema compatibility and affected builds belong to [code control](../engineering/code-control.md). The [context inventory](../../architecture/context-map.yaml) records each service, its local source root and allowed packages. Cross-service isolation comes from that ownership, autoload/build containment and runtime contracts; repeated `App\` prefixes are valid in separate artifacts.

P01 demonstrates both accepted and rejected cases. Accepted cases include an Eloquent Domain model, an Action using `DB`/`Gate`, a scoped simple controller read, and two independent Laravel services with local `App\` mappings. Rejected cases include Domain importing an Action, Application importing an Infrastructure implementation or controller, undeclared service/package dependencies, and autoloading another service's source. The Python rules remain separately tested.

Project-owned PHP architecture tests enforce the selected dependency and Action conventions in P01. Run them in the normal test suite, supplement service/package/build checks, and report skipped namespaces explicitly. The article and its package repository are references for the convention; adopting that convention requires no Boost or Laravel Boost DDD installation. Static checks cannot establish authorization, transaction races, rollback, durable delivery or native qualification. Direct Action and entrypoint behavior tests must exercise those relevant outcomes.

Feature review follows the changed capability from input and authority through model behavior, persistence, event contract, consumer impact and operations. Attach observed proof to the [engineering coverage](../engineering/coverage.md) packages and gates; do not create another completion ledger inside source folders.

## Sources and project decisions

- [The user-selected convention](https://dev.to/maiobarbero/pragmatic-domain-driven-design-in-laravel-with-laravel-boost-3bcm), [author package](https://github.com/maiobarbero/laravel-boost-ddd) and [core guidance](https://github.com/maiobarbero/laravel-boost-ddd/blob/main/resources/boost/guidelines/core.blade.php) define the Laravel approach adopted here.
- [Laravel directory structure](https://laravel.com/framework/docs/13.x/structure), [container](https://laravel.com/framework/docs/13.x/container) and [providers](https://laravel.com/framework/docs/13.x/providers) document framework mechanisms.
- [PHP-FIG PSR-4](https://www.php-fig.org/psr/psr-4/) governs namespace/path correspondence.

The service map, worker ownership, tenant/authority protocol, durable outbox and delivery gates are project requirements. The selected Laravel convention does not claim to supply those distributed-system guarantees. This document defines the convention; application implementation remains subject to the delivery gates.
