# Laravel service and code conventions

Owner: Engineering and Laravel service leads. Applies to console, governance, catalogue and assurance. Reviewed: 2026-10-04. Related delivery: P00.02/P00.03, P01.01/P01.03/P01.04 and all later Laravel feature packages.

Laravel supplies the application framework; the [target architecture](../architecture/target-architecture.md) defines which service owns each decision. These are project conventions for the planned implementation. They do not change the Laravel/Python split or the dispositions of ADR-003/004/005.

## 1. Preserve ordinary Laravel applications

Each Laravel deployable has its own `composer.json`, committed lockfile, `artisan`, `bootstrap/`, `config/`, `routes/`, `app/`, `database/`, `tests/` and image definition. The console additionally owns its frontend manifest, lockfile and build configuration. Use conventional framework discovery and generators where practical. Laravel permits application-specific organization; a large repository does not require replacing the framework's structure with a custom kernel. See [directory structure](https://laravel.com/framework/docs/13.x/structure).

| Location within a service | Responsibility | Keep out |
| --- | --- | --- |
| `app/Http/Controllers/`, `Requests/`, `Resources/` | HTTP adaptation, declared validation, authorization invocation and explicit serialization | Long workflows, native credentials, cross-service SQL |
| `app/Actions/<Capability>/` | One named application use case, its transaction boundary and domain coordination | Transport response formatting and hidden external side effects |
| `app/Queries/<Capability>/` | Bounded, tenant-scoped read composition | Mutation, authorization bypass and unbounded relationship expansion |
| `app/Models/` | Owned persistence mapping, relationships, casts and local query scopes | Estate-wide workflows or models owned by another service |
| `app/Domain/<Capability>/` | Reusable invariants, typed values and state transitions when complexity warrants separation | Framework request/session state and provider SDK calls |
| `app/Policies/` | Resource/action decisions using authenticated scope | A global administrator shortcut around tenant or separation-of-duties checks |
| `app/Integrations/<Dependency>/` | Typed contract clients and bounded transport/error mapping | Direct platform mutation outside lifecycle's authorized worker path |
| `app/Jobs/`, `Listeners/`, `Console/` | Background, event and CLI entry adapters into the same use cases | A second implementation of business permissions or orchestration |
| `app/Providers/` | Explicit binding and framework boot configuration | Database changes or remote calls during application bootstrap |

Create these additional capability folders when the first relevant implementation needs them. Do not generate empty layers, a repository interface for every table, or a separate deployable for every capability. A simple read can use a scoped query directly; extract a query object when composition or reuse justifies it. A multi-entity revision or approval operation merits a named action with a visible transaction.

## 2. Keep decisions in one place

Controllers translate input and output. Form Requests enforce the HTTP input shape and invoke the declared authorization policy; their successful validation is not authority to access every referenced object. Convert allowed fields to typed application input and add authenticated tenant/actor context separately. Jobs and commands call the same use case with independently established authority.

Local rules may live on a cohesive model or domain object. Put cross-aggregate coordination in a named action, not in a growing model, generic `Service` class or model observer. Keep native provisioning, migration, fencing and compensation in lifecycle/Temporal and site workers. Model events must not invisibly start a native operation or an external side effect before a transaction commits.

A catalogue revision use case, for example, checks current caller scope, recognizes a previously accepted command, verifies the expected parent revision, validates domain associations, and commits the new revision, command receipt and outbox event together. Its HTTP adapter returns the contracted receipt; a CLI adapter cannot skip those rules. The exact order and status codes remain owned by the [contract conventions](../contracts/README.md).

The project deliberately avoids prescribing either maximum-size models or fully framework-independent persistence for every feature. Extract pure domain code where state transitions and invariants benefit from fast independent tests; use Eloquent normally for service-owned persistence. The criterion is explicit ownership and testable behavior.

## 3. Dependency direction and shared code

- No service imports another service's `app/` classes, migrations, models or runtime configuration. The console reads business data through APIs and owns only its sessions/preferences and authorized presentation state.
- Application actions depend on owned domain code and narrow integration contracts. HTTP/queue/CLI adapters depend on actions; domain value objects do not depend on controllers or request globals.
- Share schema-generated clients, interoperable scalar formats and small technical helpers only when there is a real consumer need. Shared libraries have owners, explicit versions and compatibility checks. A common business model package would recreate joint data ownership and requires a boundary redesign.
- Use interfaces for external dependencies or meaningful interchangeable behavior. Do not wrap every framework method simply to avoid using Laravel. Constructor injection makes use-case dependencies inspectable; ordinary framework facades remain acceptable at framework adapters and in focused integration code.
- Review library changes against every transitive consumer. Service-only deployment remains possible when its public contracts are compatible.

The [service container](https://laravel.com/framework/docs/13.x/container) provides injection and scoped bindings. Mutable tenant, actor, authorization, request and correlation context must never be process-global or a long-lived singleton. Establish it per request/job and clear it on completion and failure. Framework scoped bindings help; custom loops, static state and caches still require explicit isolation tests.

Follow the [provider lifecycle](https://laravel.com/framework/docs/13.x/providers): register bindings in `register`, then configure boot behavior in `boot` after providers are registered. Providers must be safe to load in HTTP, workers, CLI, tests and cache-building commands. Service startup must not acquire native authority as a side effect.

## 4. PHP naming, types and formatting

Use [PSR-4](https://www.php-fig.org/psr/psr-4/) namespace/path correspondence, including case-sensitive filenames. Keep capability and action names specific, such as `CreateIntentRevision`, rather than a catchall `Helper` or `Manager`. Names in public contracts follow the contract schema, not a formatter's naming preference.

First-party PHP uses declared parameter, return and property types, strict scalar typing where applicable, explicit nullability and bounded enums/value objects for meaningful states, units and identifiers. `declare(strict_types=1)` does not validate an HTTP body or make an untrusted integer/string a tenant identity. Validate at trust boundaries; do not pass loosely shaped arrays through a chain of actions. Use PHPDoc generics/shapes for Eloquent collections and framework types that native PHP cannot express. Avoid suppressions and unsafe casts used only to silence analysis.

Use one committed, pinned Pint policy with the `laravel` preset across the Laravel applications; generated/vendor code has separate generation ownership. [Pint](https://laravel.com/framework/docs/13.x/pint) supports multiple presets, so selecting this one does not establish conformance to every PHP-FIG style rule. [PER Coding Style](https://www.php-fig.org/per/coding-style/) is the current evolving style reference; PSR-2 is not the target. The [developer workflow](developer-workflow.md) owns tool versions and exceptions, while [testing and CI](testing-and-ci.md) owns enforcement.

Preserve rationale in comments for non-obvious invariants, trust assumptions and recovery boundaries. Avoid comments that restate the next line of code or automatic rules that discard useful design rationale. Prefer explicit named dependencies and states over reflection-based conventions developers cannot trace.

## 5. HTTP adapters and failure semantics

Serialize with explicit resource/DTO field lists; do not return an Eloquent model graph as an accidental public API. [Laravel API resources](https://laravel.com/framework/docs/13.x/eloquent-resources) provide a transformation boundary, but the versioned OpenAPI schema still owns fields, relationships, pagination and permissions. Loaded relationships are not necessarily authorized relationships. New Laravel JSON:API support is optional; do not silently change the existing problem/receipt contracts to another protocol.

Dependency clients have declared connect/total timeouts, permitted endpoints, payload/page limits, caller identity, cancellation behavior and bounded retry budgets. [Laravel's HTTP client](https://laravel.com/framework/docs/13.x/http-client) requires deliberate handling of unsuccessful responses; map failures explicitly and never treat a parsed body as success. Retry reads only when their contract permits it. Retry writes only with an accepted idempotency/reconciliation contract; a timeout does not prove the remote operation failed. Avoid multiplicative retries at proxy, client, queue and workflow layers.

Map expected domain conflicts and validation failures to stable contract codes. Unexpected exceptions produce a safe correlation reference and restricted diagnostics. Do not catch an exception, log it and return a success value or empty dataset. [Error configuration](https://laravel.com/framework/docs/13.x/errors) is centralized; debug traces, SQL and tokens never belong in public responses. Browser Inertia validation follows the distinct [frontend](frontend.md) protocol.

## 6. Review and delivery proof

P01 implements a representative action, query, policy, resource and integration adapter in the owning service, then exercises it through HTTP and the applicable background entry point. It must demonstrate forbidden-import detection, configured formatter/static analysis, typed contract handling, clean configuration caching and tenant-context isolation. Feature packages extend this pattern rather than copying a demonstration into every service.

Reviewers inspect permissions and transaction boundaries before naming/style details. Require the relevant evidence in [the coverage map](coverage.md), especially cross-tenant access, stale revisions, duplicates and dependency failure. Data and runtime rules are detailed in [data and messaging](data-and-messaging.md); security rules in [security and tenancy](security-and-tenancy.md).
