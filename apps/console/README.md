# Console foundation

The Console is the browser entrypoint for Enterprise Workload Mobility and Secure Hosting. It will compose tenant-scoped provisioning, migration, approval and recovery journeys through the owning service APIs. It owns presentation and server-side browser sessions; Governance and the other contexts retain their authorization decisions and business records. See the [Console specification](../../docs/services/console.md) and [frontend standard](../../docs/engineering/frontend.md).

This P01 increment provides an independently packaged Laravel/Inertia application and a compiled Vue/TypeScript/Tailwind interface. The public foundation page describes the intended product and makes its development state clear. Sign-in, tenant selection, service calls and workload operations are not implemented. There are no sample users, privileged identities, copied business aggregates or enabled mutation endpoints.

## Routes

| Request | Behavior |
| --- | --- |
| `GET /` | Inertia `Foundation` page. Explicit props are `productName` and `implementationState`; the adapter also supplies its standard error props. No actor, tenant, secret or service record is shared. |
| `GET /health/live` | `200`, `{service: console, status: alive, scope: process}`. Does not query a dependency or start a session. |
| `GET /health/ready` | `503`, `{service: console, status: not_ready, scope: service, reason: foundation_only}` with `Retry-After: 10`. A caller or environment switch cannot enable readiness. |

Web responses are private and non-cacheable and set `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY` and a same-origin referrer policy. Process probes are non-cacheable. The server-session cookie defaults to Secure, HttpOnly and SameSite=Lax. The file session driver is a local foundation choice; it does not establish a multi-replica session architecture. Debug and Inertia devtools are disabled. No fixed CSRF meta tag, browser token store or self-registration flow is added.

## Install and verify

Run these commands in this directory with the accepted PHP 8.5.11, Composer 2.10.3 and Node 24.19.0 family:

```sh
composer validate --strict --no-check-all
composer install --no-interaction --no-progress --prefer-dist
composer check-platform-reqs
npm ci --ignore-scripts --no-audit --no-fund
npm run typecheck
npm run test:boundaries
npm run build
composer test:format
composer test:types
composer test:architecture
composer test:canaries
composer test
```

The initial Composer lock is the P00 resolver seed until the first service-specific CI resolution is captured. It is intentionally not represented as a resolved Console lock: `composer validate --strict --no-check-all` detects the manifest mismatch before that capture. Initial resolution and subsequent locked replay are separate, explicit modes of the P01 runner. The npm manifest and lock are private to this application, and the clean local installation, strict Vue-aware type check, boundary check and production build have passed. See the [implementation record](../../docs/implementation/p01-console-foundation.md) for exact evidence and remaining checks.

For local development, copy `.env.example` to `.env`, generate an application key with `php artisan key:generate`, build the frontend, and run `php artisan serve --host=127.0.0.1 --port=8000`. The example disables Secure cookies only for loopback HTTP. A hosted deployment must use HTTPS, a protected generated key and Secure cookies. Do not commit `.env` or a generated key. PHP's development server is not the production ingress design.

The browser suite uses a separately running application and production-built assets:

```sh
npm run browser:install
npm run browser:test
```

`CONSOLE_BASE_URL` can select another local test address. The browser test checks real hydration, title, foundation disclosure, viewport overflow and JavaScript errors. It does not establish accessibility conformance or authenticated workflow behavior.

## Structure and controls

The service owns its `App\` namespace, Composer autoload root, npm dependencies, PHP configuration and compiled assets. PHP HTTP entrypoints and providers follow ordinary Laravel placement. Add Console-owned `Domain/<Capability>`, `Application/<Capability>/Actions` and Infrastructure adapters only when implementing actual behavior under [ADR-024](../../docs/decisions/adr-024-pragmatic-laravel-domain-convention.md). No development package from the convention's author is installed.

The browser bootstrap is in `resources/js/app/`; route pages are in `resources/js/pages/`. Future feature source belongs in `contexts/<context>/features/<capability>/`, exposed through a reviewed context `index.ts`. Journeys/pages compose those public interfaces. Shared technical/UI code cannot import upward into application presentation. The TypeScript AST check covers static imports/exports, type imports, literal dynamic imports and the one reviewed page glob. Unregistered packages/aliases, computed imports, sibling-service paths, context-private imports, cross-context feature coupling, upward shared imports and additional globs fail the check. SFC scripts are inspected and external script sources rejected. Bundle/type checks remain separate from this source policy; it is not a runtime sandbox or full proof against arbitrary JavaScript execution.

The regular PHP test command runs actual HTTP and architecture tests. CSRF controls use a test-only mutation route and explicitly disable Laravel's testing-environment bypass, checking both a rejected missing token and an accepted session token. This proves the configured middleware branch, not a completed business mutation or real-browser privilege transition. The separate private Deptrac canaries verify four permitted convention dependencies and nine intended rule rejections and restore the original source. They do not invent implemented Domain/Application behavior.

Remaining P01/P02 work includes service images and deployment controls, federation/delegation, authenticated session lifecycle, service readiness checks, proxy trust/CSP, shared session availability, tenant/context transitions, actual browser support, accessibility assessment and authorized workflows. Readiness stays closed while these dependencies are absent.
