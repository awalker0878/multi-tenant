# Governance foundation

Governance will own tenant membership, grants, authorization decisions, plan approval and revocation. This P01 increment implements the independent Laravel process, two diagnostic HTTP endpoints, a service-private dependency manifest and quality controls. The [service specification](../../docs/services/governance.md) describes the later business behavior; none of those authority operations is implemented here.

## Process endpoints

| Request | Result | Meaning |
| --- | --- | --- |
| `GET /health/live` | `200`, `status: alive`, `scope: process` | The Laravel HTTP process can answer this request. No dependency is queried. |
| `GET /health/ready` | `503`, `status: not_ready`, `scope: service`, `reason: foundation_only` | Governance is not ready to serve business traffic. This cannot be enabled with an environment switch or request input. |

Both endpoints return `service: governance` and `Cache-Control: no-store`; readiness also returns `Retry-After: 10`. No session is created and no actor, tenant, grant, dependency address, version or credential is returned. These are unauthenticated process probes, not authorization APIs. Unsupported methods return `405`; unimplemented paths return safe JSON `404` responses. Governance also owns the versioned identity, tenancy, approval, delegation and bounded support APIs; none performs native infrastructure effects.

## Local commands

Use the accepted PHP 8.5.11 and Composer 2.10.3 development baseline. Commands run in this directory:

```sh
composer validate --strict --no-check-all
composer install --no-interaction --no-progress --prefer-dist
composer check-platform-reqs
composer test:format
composer test:types
composer test:architecture
composer test:canaries
composer test
php artisan config:cache
php artisan route:cache
php artisan serve --host=127.0.0.1 --port=8000
```

The committed lock is the private Governance lock. [Package run 37239193553](../../docs/implementation/p01-laravel-foundations.md) passed clean locked replay, installed version/reference equality, PHP quality, 14 Pest tests / 44 assertions and cached HTTP probes. Ordinary checks use replay and reject a missing or changed lock. See the [Governance record](../../docs/implementation/p01-governance-bootstrap.md) for measured source and limits.

`--no-check-all` disables Composer's exact/loose constraint advisory for the deliberately pinned direct dependencies; strict manifest and lock validation remain enabled.

The runtime requires PHP extensions declared by the manifest and its dependency lock, including PDO PostgreSQL. Quality tools additionally require their locked platform requirements; use `composer check-platform-reqs` on the actual installation. There is no SQLite fixture, Node build, Inertia package, frontend, identity provider, broker or native endpoint dependency. PostgreSQL configuration has no default host, database, username or password and defaults to `verify-full` TLS; no database is opened by this foundation.

Copy `.env.example` to `.env` for local use and set an application key locally if adding behavior that needs encryption; never commit keys. Debug responses are disabled even if an environment variable requests them. Only controlled runtime paths under `bootstrap/cache` and `storage` should be writable. The tracked directory markers supply these paths; HTTP bootstrap does not create missing directories or change permissions. The built-in server is a development command, not the production image or ingress design.

## Ownership and checks

The service owns `App\` and `Tests\` autoload roots, its framework configuration, routes, manifest and lock. It never loads sibling service source. Normal Laravel HTTP/Providers directories contain the implemented source. Add `Domain/<Capability>`, `Application/<Capability>/Actions` and `Infrastructure` only when implementing the owning behavior under [ADR-024](../../docs/decisions/adr-024-pragmatic-laravel-domain-convention.md); no sample domain, permissive administrator or synthetic business API is installed.

The normal test command includes HTTP and Architecture suites. Deptrac analyzes the actual service and rejects uncovered first-party dependencies; its separate canary command creates temporary parser fixtures, confirms four allowed Laravel/convention dependencies and nine forbidden dependencies, then removes them. A canary must produce its exact intended rule diagnostic, not merely any nonzero process status. These fixtures establish analyzer behavior, not implemented Domain/Application layers or real tenant isolation. The retained P00 convention examples remain reference experiments.

The [image record](../../docs/implementation/p01-laravel-images.md) separately verifies the independently built Governance container and restricted diagnostic process. Database role isolation, federation, delegation, audit/outbox, grant/approval behavior, business readiness and operating acceptance remain P01/P02 work.


## Bounded support access

[Policy version 1](../../docs/implementation/p02-support-access.md) and the
[owner contract](../../contracts/openapi/governance-support-v1.json) define explicit
membership/grant diagnostics for a named executor. A current tenant administrator
and separately appointed security approver approve the exact request; every use
rechecks current authority and commits an immutable audit. This is an API workflow,
not a new Console screen. Existing tenant grants cannot carry support permissions.

Apply numbered migrations before deploying the new code. Existing ordinary sessions
remain usable; support operations require reauthentication to retain their verified
signer. No OIDC environment settings were introduced. Follow the
[support operations runbook](../../docs/operations/runbooks/support-access.md)
for current role assignment, containment, expiry, audit delivery and review.
