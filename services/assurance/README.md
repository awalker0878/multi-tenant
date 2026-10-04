# Assurance service foundation

Assurance owns attributable evidence metadata, artifact custody, qualification decisions and conditional support publication. Its detailed responsibility, invariants and delivery cases are in the [service specification](../../docs/services/assurance.md).

This P01 increment establishes a service-private Laravel application boundary and diagnostic HTTP endpoints. The evidence upload or verification, object storage, custody controls, qualification decisions, authorization, database migrations, outbox delivery and public business endpoints are not implemented. A passing foundation check does not establish those product capabilities or operational acceptance. P06.04 implements the business behavior.

## Service ownership

This application owns `composer.json`, its service-private `composer.lock`, its `App\` namespace and all files beneath this directory. It does not load sibling application source or a shared business model. Business capabilities will use `app/Domain/<Capability>/` and `app/Application/<Capability>/Actions/` when implemented; Actions expose `handle()`. Eloquent is permitted in the owning Domain, and application Actions may use Laravel authorization and local transactions under [ADR-024](../../docs/decisions/adr-024-pragmatic-laravel-domain-convention.md). External adapters belong in `app/Infrastructure/`; HTTP entrypoints remain in `app/Http/`. No synthetic business model exists in this foundation.

## Diagnostic endpoints

| Request | Result | Meaning |
| --- | --- | --- |
| `GET /health/live` | HTTP 200, `status: alive`, `scope: process` | The Laravel request reached this process. |
| `GET /health/ready` | HTTP 503, `status: not_ready`, `reason: foundation_only` | Required application dependencies and their checks are not implemented. |

Both endpoints return JSON with `Cache-Control: no-store`; readiness also returns `Retry-After: 10`. They do not start browser sessions, accept tenant identity or check database connectivity. Health writes are rejected, unknown routes return JSON and business endpoints are absent. There is no configuration flag that changes this foundation into a ready service. These routes are diagnostic probes, not a public business API or authorization contract.

## Install and check

The candidate uses PHP 8.5 with the measured Laravel 13.34.0 and exact development tool versions. A private PostgreSQL driver is declared for the intended persistence boundary, but no connection or credentials are configured and no database is created. Runtime deployment must supply its own environment, application key and writable cache/storage paths.

The service-private Composer lock is retained. Run from this directory with the pinned runtime:

```sh
composer install --no-interaction --prefer-dist --no-progress
composer validate --strict --no-check-all
composer test:format
composer test:types
composer test:architecture
composer test
composer test:canaries
```

The test environment key in `phpunit.xml` is a synthetic test value. It is not installed application configuration. Package discovery runs on the local application's dependencies. The Composer manifest has no path repository, sibling autoload mapping, shared business package or dependency on the compatibility spike.

The ordinary tests exercise actual HTTP responses, absent routes, write rejection, private autoload resolution and implemented class conventions. Deptrac enforces the selected layer rules. Temporary positive and negative canaries exercise analyzer behavior without adding fake business code to the deployed application. Their results establish configured source controls only; tenancy, actor authorization, transaction durability, network/data isolation and implemented domain invariants require their own later behavior tests.

## Current verification scope

The [package record](../../docs/implementation/p01-laravel-foundations.md) binds the successful private-lock replay, PHP quality, 14 Pest tests / 44 assertions and cached HTTP probes in run 37239193553. The [image record](../../docs/implementation/p01-laravel-images.md) separately binds the independently built image and restricted process diagnostics. These are foundation measurements, not acceptance of the future product behavior. Dependency readiness remains unavailable until its real probes and required dependencies are implemented; process liveness cannot promote this state.
