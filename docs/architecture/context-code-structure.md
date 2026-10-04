# Context and microservice code structure

Owner: Architecture and engineering leads, with each context owner. Reviewed: 2026-10-04. Applies to P00.02, P01.01/P01.03/P01.04 and all feature packages.

The product is organized by bounded context, then by dependency layer and capability. Each business context owns its model, use cases, persistence, public contracts and release impact. A microservice is the deployable boundary around that ownership. A capability is a cohesive area inside its context; adding a capability does not automatically add another microservice.

This is the required project structure following the user's direction for a context-oriented enterprise codebase. It supersedes the earlier suggestion to organize business behavior primarily under `app/Actions`, `app/Models` and optional domain folders. Laravel allows custom autoloaded organization; it does not prescribe this architecture. The framework host remains conventional while business code follows explicit context boundaries. The [target architecture](target-architecture.md) owns system responsibilities; [code control](../engineering/code-control.md) owns enforceable change and dependency controls.

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

## 3. PHP context layout

The canonical business-code root is `services/<service>/src/Contexts/<StudlyContext>/`. Each context contains `Domain/`, `Application/`, `Infrastructure/` and `Interfaces/`; capabilities are organized inside those layers. Catalogue `Domain/Applications/` and `Application/Applications/Commands/` belong to the same context.

| Layer | Contents | Boundary rule |
| --- | --- | --- |
| `Domain/` | Aggregates, entities, immutable values, domain events, invariant policies and typed domain failures | Pure PHP; no Laravel, ORM, request/session, transport, container or provider SDK dependency |
| `Application/` | Named commands/queries, handlers, application DTOs, authorization orchestration, transaction and external dependency ports | Coordinates the context's domain and ports; no Eloquent, framework facade, transport or concrete adapter |
| `Infrastructure/` | Eloquent records/mappers, repository/query implementations, transaction adapter, outbox/inbox storage, HTTP clients, secret and clock adapters | Implements inward-facing ports; translates external representations into owned values |
| `Interfaces/` | HTTP controllers/requests/resources, inbound event consumers, Artisan commands and local job entry adapters | Establishes trusted input, invokes application use cases, maps output; no direct persistence or native mutation |

Retain `artisan`, `bootstrap/`, `config/`, `routes/`, `public/`, `database/`, `storage/`, `tests/` and the service's Composer files at the Laravel host root. `app/` is a host/composition shell restricted to registered providers and host middleware; framework exception configuration belongs in the host bootstrap. Business controllers, policies, use cases, entities and persistence models live in their registered context. Adjust Artisan defaults or move and namespace generated output before merge.

For `services/catalogue/composer.json`, the owning mappings are:

```json
{
  "autoload": {
    "psr-4": {
      "App\\": "app/",
      "Product\\Contexts\\Catalogue\\": "src/Contexts/Catalogue/"
    }
  },
  "autoload-dev": {
    "psr-4": {
      "Tests\\": "tests/"
    }
  }
}
```

`Product\Contexts\Catalogue\Domain\Applications\Application` maps to `src/Contexts/Catalogue/Domain/Applications/Application.php`. Governance and Assurance declare only their own equivalent context namespace. A broad `Product\Contexts\` mapping to multiple service directories would defeat the boundary and is prohibited. Explicit test-factory mappings remain service-local and development-only.

## 4. Allowed dependency matrix

This matrix governs first-party imports. Runtime API calls are a separate, reviewed contract dependency. The same layer directions apply to Python using lowercase package names.

| Importing area | May depend on | Forbidden dependencies |
| --- | --- | --- |
| Domain | Its own Domain and language primitives used without external effects | Application, Infrastructure, Interfaces, host code, framework/ORM, shared packages, generated transport clients, another context |
| Application | Its own Application and Domain; locally defined ports and typed values | Infrastructure, Interfaces, host code, framework/ORM, shared packages, concrete client/SDK, another context |
| Infrastructure | Its own Infrastructure, Application ports/DTOs and Domain; selected framework/ORM/transport libraries; approved schema-generated clients | Interfaces, another context's internal code, shared business models |
| Interfaces | Its own Interfaces, Application input/output and use-case types, required Domain values; inbound framework/protocol libraries | Infrastructure implementations, ORM queries, provider writes, another context's internal code |
| Host/composition | Its own context's layers for bindings/registration; framework bootstrap and selected infrastructure constructors | Business decisions, cross-context in-process calls, tenant authority acquired during bootstrap |
| Contract/technical package | Its declared schema generation/runtime or approved technical dependencies | Any service source, business aggregate or database table ownership |
| Tests | Code under test and scoped test fixtures; contract clients for integration tests | Production dependency on tests; production imports justified only because a test needs them |

Within a context, capability dependencies are also reviewed. `Domain/Applications` may reference an owned immutable value from `Domain/SecurityDomains`; it cannot load that capability's database row. Cross-aggregate coordination lives in an application use case. Capability dependency cycles and a generic shared domain folder that gradually owns every rule require refactoring, even when the layer checker passes.

The initial core policy permits no external shared package in Domain/Application. A later framework-free primitive library requires an explicit scoped policy change, consumer review and analyzer fixtures before use; an `allowed_packages` entry for a service does not open its core layers. Standard-library membership is not proof of purity: filesystem, process, network, database and nondeterministic clock access must remain behind application ports/adapters. The initial AST check is not an effect-system analyzer.

Reflection, global container lookups, dynamic imports and string-built class names cannot bypass these rules. Domain/Application classes receive typed dependencies; they never call `app()`, resolve `DB`, inspect request globals or select an infrastructure implementation. Static checks are supplemented by review, container wiring tests and behavior tests; import checks cannot prove runtime data ownership.

### Deliberate composition exceptions

The host service provider knows both an application port and its infrastructure implementation to bind them. It may also register interface routes, commands, policies, Eloquent morph mappings and event dispatch wiring. This narrowly scoped composition exception does not permit business rules in `app/`. Context code does not import `App\`.

An Eloquent mapper may reconstruct a Domain aggregate from validated stored state, and a repository may map it back to owned records; this is the intended Infrastructure-to-Domain direction. Rehydration does not re-emit creation events or repeat accepted transitions. Eloquent factories and integration tests may construct ORM records. Neither exception permits a Domain entity to extend an Eloquent model. Model observers are infrastructure hooks and cannot replace an application use case or trigger unrecorded external effects.

## 5. Catalogue implementation reference

These paths define where the first complete Catalogue slice belongs; they do not claim these classes already exist. Add classes needed by the slice, maintaining the four enforced boundaries without filling every capability with empty abstractions.

| Path below `services/catalogue/` | Responsibility |
| --- | --- |
| `src/Contexts/Catalogue/Domain/Applications/Application.php` | Application aggregate and its accepted state changes |
| `src/Contexts/Catalogue/Domain/Applications/ApplicationId.php` | Typed stable identity without transport or ORM behavior |
| `src/Contexts/Catalogue/Domain/IntentRevisions/IntentRevision.php` | Immutable requested intent and version/digest semantics |
| `src/Contexts/Catalogue/Domain/IntentRevisions/DependencyGraph.php` | Workload references and execution-dependency cycle rules |
| `src/Contexts/Catalogue/Domain/IntentRevisions/IntentRevisionCreated.php` | Internal domain fact, subsequently mapped to a public event schema |
| `src/Contexts/Catalogue/Application/Applications/Commands/CreateIntentRevision.php` | Typed command with permitted fields and authenticated actor scope |
| `src/Contexts/Catalogue/Application/Applications/Commands/CreateIntentRevisionHandler.php` | Authority, idempotency, revision concurrency and local transaction coordination |
| `src/Contexts/Catalogue/Application/Applications/Queries/GetApplication.php` | Authorized, bounded read use case |
| `src/Contexts/Catalogue/Application/Applications/DTOs/ApplicationView.php` | Explicit read result independent of Eloquent and HTTP resources |
| `src/Contexts/Catalogue/Application/Ports/ApplicationRepository.php` | Load/save at the aggregate's tenant and version boundary |
| `src/Contexts/Catalogue/Application/Ports/ApplicationReader.php` | Bounded projections without full aggregate reconstruction for lists |
| `src/Contexts/Catalogue/Application/Ports/Authorization.php` | Current actor/action/resource authorization contract |
| `src/Contexts/Catalogue/Application/Ports/Transaction.php` | Local unit of work without exposing a database connection |
| `src/Contexts/Catalogue/Application/Ports/CommandReceipts.php` | Durable retry binding, receipt lookup and collision detection |
| `src/Contexts/Catalogue/Application/Ports/Outbox.php` | Persist event intent in the same owned transaction |
| `src/Contexts/Catalogue/Infrastructure/Persistence/Eloquent/Models/ApplicationRecord.php` | Catalogue-owned Eloquent persistence record |
| `src/Contexts/Catalogue/Infrastructure/Persistence/Eloquent/Models/IntentRevisionRecord.php` | Append-only revision mapping and owned relationships |
| `src/Contexts/Catalogue/Infrastructure/Persistence/Eloquent/Mappers/ApplicationMapper.php` | Explicit domain/record mapping including tenant and version |
| `src/Contexts/Catalogue/Infrastructure/Persistence/Eloquent/EloquentApplicationRepository.php` | Aggregate persistence and conditional concurrency checks |
| `src/Contexts/Catalogue/Infrastructure/Persistence/Eloquent/EloquentApplicationReader.php` | Tenant-bound projections, select fields and query budgets |
| `src/Contexts/Catalogue/Infrastructure/Persistence/LaravelTransaction.php` | Implements the local transaction port |
| `src/Contexts/Catalogue/Infrastructure/Authorization/GovernanceAuthorization.php` | Maps Governance contract decisions into Catalogue application types |
| `src/Contexts/Catalogue/Infrastructure/Messaging/OutboxEventMapper.php` | Converts local facts into a pinned event schema |
| `src/Contexts/Catalogue/Interfaces/Http/Controllers/CreateIntentRevisionController.php` | Invokes the use case and maps its accepted/conflict result |
| `src/Contexts/Catalogue/Interfaces/Http/Requests/CreateIntentRevisionRequest.php` | HTTP input shape/bounds and early authority checks |
| `src/Contexts/Catalogue/Interfaces/Http/Resources/IntentRevisionResource.php` | Explicit contracted response from application output |
| `src/Contexts/Catalogue/Interfaces/Console/CreateIntentRevisionCommand.php` | CLI adapter into the same use case under verified command authority |
| `app/Providers/CatalogueServiceProvider.php` | Port bindings and route/policy/command registration |
| `database/migrations/` | Owned schema changes; no foreign-service table joins or writes |
| `tests/Unit/Contexts/Catalogue/Domain/` | Pure invariant tests without booting Laravel |
| `tests/Unit/Contexts/Catalogue/Application/` | Use-case tests with explicit port fakes |
| `tests/Integration/Contexts/Catalogue/Infrastructure/` | Real mapping, uniqueness, transaction and outbox behavior |
| `tests/Feature/Contexts/Catalogue/Interfaces/` | HTTP/CLI/message authentication, validation and result mapping |

A repository represents an aggregate consistency boundary, not every table. Revision records may be persisted through a cohesive aggregate operation without generic CRUD repositories for every child row. The exact transaction shape follows ADR-013. Query adapters may use efficient SQL/Eloquent inside Infrastructure and return application DTOs while preserving authorization, tenant filters and response bounds.

### End-to-end revision command

1. The HTTP adapter authenticates the caller and establishes trusted tenant/actor context separately from the payload. Its Form Request validates shape and field bounds; client-supplied tenant, role or privilege claims never establish authority.
2. The controller constructs `CreateIntentRevision` and invokes its handler. CLI or queue adapters enter the same application boundary with independently verified actor/delegation context.
3. The handler checks current authority through `Authorization`, validates command scope and resolves immutable reference inputs through ports. Remote calls are outside the local transaction; unavailable or stale required decisions fail closed under the action's freshness policy.
4. Inside `Transaction`, the handler checks durable idempotency, rejects the same key with changed payload, and loads the tenant-bound aggregate at its expected revision. A prior receipt is returned only after the current caller is authorized to see it.
5. Domain methods enforce associations, workload identity, immutable revision rules and dependency-graph invariants. The handler coordinates owned aggregates and any local authority/version tokens. No Domain method contacts Governance, a database or a native provider.
6. Repositories persist the revision and conditional current-revision change. Receipt and outbox adapters persist the exact result and event intent on the same owned connection/transaction. Concurrent conflicts produce a stable failure rather than overwriting another revision.
7. After commit, the interface maps the typed result to the contracted receipt/resource. A queue hint may wake publication; the durable outbox owns recovery if the process dies after commit.
8. The publisher emits the pinned event. Planning receives it through its own interface, deduplicates with local effects, and resolves authorized Catalogue contracts for full intent. It never imports Catalogue classes or treats an event as current execution authority.

Local atomicity does not create an atomic transaction with Governance. Each operation defines decision freshness and race handling. Exact-plan approval and native-effect admission retain the stricter Governance/Lifecycle rechecks; creating a Catalogue revision cannot authorize provider writes.

## 6. Authorization at three boundaries

| Boundary | Owns | Must not substitute for |
| --- | --- | --- |
| Interface request/policy | Authentication adaptation, shape, early denial and safe presentation | Application authority required by alternate entrypoints |
| Application authorization port/use case | Current action/resource/delegation checks and external authority orchestration | A hidden UI control or cached event |
| Domain invariant/policy | Valid product state independent of transport, such as immutable intent | Identity-provider validation, database lookup or remote authorization |

Laravel policies and Form Requests are interface adapters when they deal with framework users/requests. They delegate to the application permission contract and do not query persistence independently. Resource resolution uses a tenant-bound application query/port. Avoid implicit Eloquent route binding that loads a business record before its owning authorization boundary. Explicit binding requires equivalent query/permission review and negative tests.

Authentication/session records required by Laravel live in the appropriate infrastructure adapter; actor context passed inward is framework-free. A policy can consume a framework authentication interface and application resource reference without importing an Infrastructure model. Global administrator hooks cannot skip tenant scope or separation of duties.

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

## 8. Console composition exception

Console uses `apps/console/src/Contexts/Console/` with Application, Infrastructure and Interfaces boundaries. Add Domain only for genuine console-owned invariants such as presentation-preference rules; do not manufacture business entities to imitate Catalogue. Session/authentication persistence remains an infrastructure concern.

Console Application composes task views through client ports. Infrastructure implements them against generated contracts; `Interfaces/Http/` owns Inertia controllers, presenters and request adapters. Host providers bind the ports. Vue features live under `resources/js/contexts/<context>/features/<capability>/` and expose only reviewed `contexts/<context>/index.ts` entrypoints; pages and journeys compose those entrypoints. See [frontend conventions](../engineering/frontend.md) for private/shared import rules. Console never owns a second application aggregate, approves a plan, acquires native credentials or queries business-service tables.

Page composition has bounded fan-out/timeouts and explicit partial/unavailable states. Mutations call the owning service with current delegation and preserve its receipt/idempotency semantics. A convenience facade cannot turn a browser session into universal service authority.

## 9. Code control and acceptance

Ownership, required review, path rules, package dependencies, schema compatibility and affected-build selection belong to [code control](../engineering/code-control.md). The [context inventory](../../architecture/context-map.yaml) must agree with this map. Boundary changes update the inventory, dependency rules, contracts, owner review and tests together.

P01 demonstrates an allowed Catalogue command path and deliberately rejected cases: Eloquent in Domain, Infrastructure in Application, a controller querying an ORM model, another service namespace, business code under the host, an undeclared Python service import and an unapproved shared package. Documentation checks alone prove none of those language/runtime properties.

Feature review follows the changed capability and aggregate through input, authority, transaction, output/event, consumer impact, tests and operations. Attach proof to the existing [engineering coverage](../engineering/coverage.md) packages and gates; do not create another completion ledger in source folders.

## Sources and architectural judgment

- [Laravel directory structure](https://laravel.com/framework/docs/13.x/structure): application-specific organization is permitted when classes are autoloadable.
- [Laravel service container](https://laravel.com/framework/docs/13.x/container) and [service providers](https://laravel.com/framework/docs/13.x/providers): injection and registration mechanisms for the composition root.
- [PHP-FIG PSR-4](https://www.php-fig.org/psr/psr-4/): namespace/path and case correspondence.
- [Bounded Context](https://martinfowler.com/bliki/BoundedContext.html): separate models and explicit context relationships.

The four-layer policy, exact layout and restrictions are project architecture decisions for this product's ownership and code-control needs. They are not mandatory Laravel framework conventions or evidence that implementation has passed qualification.
