# Laravel capability and code conventions

Owner: Engineering and Laravel context leads. Applies to Governance, Catalogue, Assurance and the Console composition boundary. Reviewed: 2026-10-04. Related delivery: P00.02/P00.03, P01.01/P01.03/P01.04 and later Laravel feature packages.

Use the selected pragmatic Laravel DDD convention: capability models and business behavior in `app/Domain`, use-case Actions in `app/Application`, external adapters in `app/Infrastructure`, and normal Laravel entrypoints. The [context code structure](../architecture/context-code-structure.md) owns the complete layout and dependency matrix; [code control](code-control.md) owns enforcement. [ADR-024](../decisions/adr-024-pragmatic-laravel-domain-convention.md) records the direction.

Each Laravel application remains a separate artifact and data owner. A Catalogue capability can collaborate directly with another Catalogue capability. Governance, Planning or Lifecycle can be reached only through their published contracts. PHP code structure does not change the seven principal deployables or the Python/native-effect responsibilities.

## 1. Organize capabilities inside a normal Laravel application

Each service owns its Composer manifest/lock, bootstrap, routes, configuration, migrations, tests and image. Console also owns its frontend dependencies and assets. Every Laravel artifact maps its own `App\` namespace to its own `app/` directory; Composer and build inputs must never expose a sibling service.

| Code | Destination relative to the owning service |
| --- | --- |
| Catalogue application entity | `app/Domain/Applications/Models/Application.php` |
| Revision invariants, values and failures | `app/Domain/IntentRevisions/` |
| Revision creation use case | `app/Application/IntentRevisions/Actions/CreateIntentRevision.php` |
| Meaningful structured revision input | `app/Application/IntentRevisions/Data/CreateIntentRevisionData.php` |
| Consumer's external capability requirement | `app/Application/IntentRevisions/Contracts/` or the Domain capability's `Contracts/` when Domain owns that need |
| Remote authority/event adapters | `app/Infrastructure/` |
| HTTP transport | `app/Http/Controllers/`, `app/Http/Requests/`, `app/Http/Resources/` |
| CLI, queue and event delivery | `app/Console/Commands/`, `app/Jobs/`, `app/Listeners/` |
| Authorization and registration | `app/Policies/`, `app/Providers/` |
| Schema and test construction | `database/migrations/`, `database/factories/`, `database/seeders/` |

Add only the classes a use case needs. Product models belong to their capability. During greenfield scaffolding, a service-owned authentication model belongs in the relevant identity capability with explicit authentication, factory and policy mappings. Do not manufacture a context or package for every capability.

## 2. Preserve responsibility boundaries

Domain cannot import Application, Infrastructure or delivery code. Application cannot import Infrastructure or delivery code. Those constraints include indirect access through container lookups, custom facades and string-built class names. Inject the contract owned by the consumer when an external integration is needed; bind its implementation in a service provider.

Eloquent models and relations are permitted in Domain. Application may load/save those models, use Laravel database transactions, and authorize the explicit actor with gates/policies. Framework usage follows responsibility: `DB` and `Gate` do not turn an Action into an adapter. HTTP requests/responses, provider SDKs and HTTP clients still belong outside Domain/Application.

Capabilities in one context may collaborate directly. Cross-aggregate changes needing atomicity are coordinated by the outer Action. An Action may invoke another complete Action where that is useful, preserving actor authorization and the outer transaction; do not split every line into a separate use case.

Shared generated clients and the registered technical integration packages are adapter dependencies under the current project policy. They do not allow Domain/Application to import transport clients or bypass a consumer-owned external contract. Framework dependencies are evaluated separately from those shared monorepo packages.

No service may import another service's classes, migrations, models or configuration. Cross-context references carry identifiers, versions, tenant scope and digests as required by the contract. Eloquent relationships must not traverse another service's database.

## 3. Put business behavior on the appropriate model or value

Catalogue Eloquent entities own valid state transitions and associations. A revision method rejects invalid workload references, immutable-state changes and inconsistent domain associations with meaningful domain failures. The Action coordinates loading and saving; the model does not return an HTTP response or authorize a browser session.

Use a value object where it provides useful validation or behavior, such as a dependency graph or bounded resource quantity. Use a domain service when a cohesive business rule has no appropriate entity/value owner. Do not add inheritance hierarchies, event collectors, DTOs or factories for domain construction without a concrete need. Normal Eloquent test factories remain appropriate.

Direct Eloquent is the persistence default. A repository or specialized persistence contract needs a documented reason beyond wrapping `find`, `save` or a query builder. There is no required separate persistence record, mapper or reader port for every model. Database constraints and domain behavior complement each other: constraints enforce storage integrity while domain methods explain accepted business transitions.

Tests must match actual behavior. Pure values and state transitions can be tested without a database when their implementation allows it. Eloquent relationships, casts, scopes, constraints, transactions and concurrency require framework/database tests, using the production engine for engine-dependent guarantees. Moving an Eloquent model into Domain does not make its database behavior a pure unit test.

## 4. Make Actions own meaningful use cases

An Action has a verb-oriented name such as `CreateIntentRevision`, normally is `final`, and exposes public `handle()`. Use meaningful parameter and return types. A scalar identifier can remain a scalar; an immutable `*Data` object is useful for structured revision input with several related fields. A Form Request never becomes an Action argument. Returning an owned model is acceptable when the caller presents only authorized fields.

Entrypoints authenticate the caller, validate transport shape and establish trusted tenant/actor/delegation context. The Action independently authorizes that explicit actor against the scoped resource using Laravel's policy/gate mechanism. Nested references require scope and permission checks too. A successful Form Request or previous web request is insufficient authority for a queue retry or CLI call.

Use `DB::transaction` when multiple local writes must succeed together. The Catalogue revision transaction includes the immutable revision, conditional current pointer, durable receipt and outbox intent. [The worked revision flow](../architecture/context-code-structure.md#end-to-end-revision-command) defines where current remote authority checks and local version checks occur. A trivial read does not need a transaction wrapper merely to fit a template.

Retryable transaction closures contain repeatable local work. Remote authorization/reference calls, message publication, mail and native effects remain outside them. Authority decisions have explicit scope, binding and freshness semantics; local rollback cannot undo a remote action or guarantee atomicity with Governance. Idempotency binds tenant, actor/action scope and canonical request identity; reusing a key with changed intent is a conflict. Disclosing an existing receipt still requires current permission.

Domain events describe local facts; Application coordinates when reactions may run. Use after-commit event/listener behavior where appropriate so rolled-back work cannot trigger follow-up effects. Durable cross-service publication additionally requires the outbox/inbox protocol: an after-commit callback alone cannot survive every process crash. The durable record and business writes share the owning transaction and connection.

Native provisioning, migration, fencing, reconciliation and compensation remain Lifecycle/Temporal responsibilities. An Action, observer, listener or Laravel job cannot introduce an alternate provider mutation path.

## 5. Use Laravel policies, providers and entrypoints normally

Keep policies in `app/Policies`. Map them to capability models in a provider; Domain models must not import their policy class. Policies answer actor/resource permission; model behavior answers whether a business transition is valid. Policy evaluation must use verified tenant/authority context and preserve separation of duties.

Providers bind consumer contracts in `register` and perform framework registrations in `boot` when the lifecycle requires it. Bootstrap must work for HTTP, queue workers, CLI, tests and cache construction without remote business calls, migrations or native credentials. Validate factory/model associations, relationships, route binding and policy discovery whenever a model moves.

A simple authorized, tenant-scoped read can remain in its controller with bounded Eloquent querying and an explicit Resource. Promote it to an Action when it becomes a coordinated business use case. Jobs and listeners invoke Actions for meaningful operations; small technical reactions can remain local. Prefer events for asynchronous follow-up from an Action, while preserving the durable delivery requirements of the use case.

Establish actor, tenant, authority and correlation context for every request/job and clear it on success and failure. Do not keep it in static state or a process-lifetime singleton. Scoped bindings help with framework lifecycles; custom loops and caches still need reset behavior and alternating-tenant tests.

## 6. Types, names and formatting

Follow [PSR-4](https://www.php-fig.org/psr/psr-4/) namespace/path correspondence and case-sensitive filenames. Action names omit an `Action` suffix; meaningful structured input classes in `Data/` use the `Data` suffix. Avoid generic `Helper`, `Manager` and `BaseService` classes that hide responsibility. Public field and event names follow their schemas.

First-party PHP declares parameter, return and property types, explicit nullability and strict scalar typing where applicable. Use enums and value objects for bounded states, units or identifiers when they clarify behavior. `declare(strict_types=1)` does not validate a request or authenticate a tenant. Structured Action input contains permitted business values/references and excludes HTTP request objects.

Use PHPDoc generics/shapes when native PHP cannot express a collection or result type. Avoid unsafe casts and broad ignored-error baselines for new code. Narrow analyzer exceptions need the owner, reason, scope and expiry required by code control.

Use one pinned Pint policy with the `laravel` preset across the PHP services. It formats all applicable application and test paths. [PER Coding Style](https://www.php-fig.org/per/coding-style/) is the current style reference; the Pint preset is not a claim of exact conformance to every PHP-FIG recommendation. [Developer workflow](developer-workflow.md) owns resolved versions; [testing and CI](testing-and-ci.md) owns gates.

Comments explain invariant, trust and recovery decisions that code alone does not make clear. A reviewer should be able to trace the actor and input through policy, Action, model behavior, transaction and public result.

## 7. Keep public contracts independent of PHP implementation

Canonical schemas remain in `contracts/openapi/<service>.yaml`, `contracts/asyncapi/<service>.yaml` and `contracts/schemas/`, with fixtures under `contracts/fixtures/<service>/`. Infrastructure clients translate published representations into consumer-owned inputs/results. Eloquent classes and Laravel events are not cross-language contracts.

HTTP Resources expose explicit authorized fields, relationships and pagination, including when their input is an Eloquent model. Loaded relationships are not automatically authorized. Preserve the established problem/receipt protocol and Inertia behavior described in [frontend conventions](frontend.md).

Infrastructure HTTP clients declare endpoint identity, payload/page bounds, timeouts and retry budgets. Map unsuccessful responses into meaningful failures; parsed JSON is not proof of success. Retry writes only under an idempotency/reconciliation contract and account for retries in proxies, queues and workflows too.

Map expected business failures to stable transport outcomes. Unexpected failures produce a safe correlation reference and restricted diagnostics, without returning success or an apparently empty authorized dataset. Consumers validate source, scope and schema, deduplicate durably, and invoke the appropriate Action rather than embedding a second mutation workflow in a listener.

## 8. Verify the convention and the behavior

P01 supplies a synthetic foundation slice using capability Eloquent models, a registered policy, an Action with public `handle()`, normal Laravel entrypoints, meaningful external contracts and a durable outbox. Real Catalogue revision behavior is delivered in P03. It proves legitimate framework dependencies are accepted and forbidden upward or cross-service dependencies fail. P02/P03 expand that foundation into real Governance/Catalogue behavior.

Implement project-owned architecture tests for dependency direction, public Action `handle()` methods and the relevant naming rules, alongside service ownership and tenancy checks. Include the Architecture suite in normal CI. Skipped checks for absent namespaces are recorded as gaps; they do not prove the implemented-service gate. The article and package repository supply reference material for the convention; no Boost or Laravel Boost DDD installation is planned.

Run direct Action tests as well as transport tests. Cover denied authority, invalid state, tenant leakage, concurrency conflicts, rollback and event timing. Architecture tests check structural properties; they do not prove those outcomes. After-commit tests must actually exercise a commit rather than remain inside a test transaction that never commits.

Record observed results through the [coverage map](coverage.md) and existing delivery gates. Review capability ownership, authority, local atomicity and cross-service contract effects before style details. Documented conventions do not establish passed product qualification.

## Source basis

The user-selected [article](https://dev.to/maiobarbero/pragmatic-domain-driven-design-in-laravel-with-laravel-boost-3bcm), [package](https://github.com/maiobarbero/laravel-boost-ddd), [core guidance](https://github.com/maiobarbero/laravel-boost-ddd/blob/main/resources/boost/guidelines/core.blade.php) and [connected example](https://github.com/maiobarbero/laravel-boost-ddd/blob/main/resources/boost/skills/creating-action/references/order-cancellation.md) inform the PHP convention. The service isolation, authority protocol and durable event guarantees above adapt that convention to this product. Laravel's [container](https://laravel.com/framework/docs/13.x/container), [providers](https://laravel.com/framework/docs/13.x/providers), [resources](https://laravel.com/framework/docs/13.x/eloquent-resources) and [HTTP client](https://laravel.com/framework/docs/13.x/http-client) document the underlying framework mechanisms.
