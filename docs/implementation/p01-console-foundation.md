# P01 Console foundation

Owner role: Console maintainer. Phase/work package: P01 / P01.01. Date: 2026-10-04. Status: implementation present; PHP service lock resolution and hosted runtime verification pending at initial publication. This increment does not complete G01.

## Implemented boundary

`apps/console/` is an independent Laravel browser application following accepted ADR-003, ADR-005, ADR-019 and ADR-024. It has a private Composer manifest/autoload root and npm manifest/lock, explicit Laravel bootstrap/configuration, Inertia middleware, Vue page resolution, strict TypeScript, Tailwind/Vite compilation, HTTP and architecture suites, and a real-browser foundation test. No Boost or convention-author package is installed. The seven-deployable design and independent business ownership are unchanged.

The public `/` entrypoint renders the product name and an honest foundation-state explanation through the `Foundation` page. Only `productName` and `implementationState` are explicitly supplied. There is no authentication simulation, local privileged actor, tenant data, dashboard metric or workload operation. `/health/live` reports process liveness; `/health/ready` remains `503 foundation_only` and cannot be enabled by an environment flag or client-supplied value. Health endpoints do not start browser sessions.

The server session uses a named Console cookie with Secure-by-default, HttpOnly and SameSite=Lax flags. Web responses are private/no-store with framing, MIME-sniffing and referrer headers. The HTTP test suite exercises initial HTML, Inertia JSON, explicit page disclosure, cookie attributes, route absence, health behavior and request-forgery middleware. The CSRF negative/positive tests register a test-only route and deliberately exit Laravel's `testing` environment to exercise real token verification; no product mutation route is created for the test.

## Dependencies and measured local checks

| Input/check | State at initial publication |
| --- | --- |
| PHP framework | Manifest selects PHP `~8.5.0`, Laravel `13.34.0`, Inertia Laravel `3.5.1` and measured P00 quality-tool versions. Required PostgreSQL extension is declared; no database connection or product persistence is configured. |
| Composer lock | P00 lock used as an explicitly identified resolver seed. Requires service-specific resolution, capture and subsequent locked replay; it is not yet proof of Console installation. |
| Browser dependencies | Private npm lock retains Inertia Vue/Vite `3.8.0`, Vue `3.5.43`, TypeScript `6.0.3`, Tailwind `4.3.3`, Vite `8.3.2`, Vue plugin `6.0.9`, Laravel Vite plugin `3.2.0`, Vue TSC `3.3.12`, Node types `24.19.1`, Playwright `1.63.0`. |
| Local installation | Node `24.19.0`, npm `11.9.0`; `npm ci --ignore-scripts --no-audit --no-fund` passed with 77 installed packages. No advisory assessment is claimed by this command. |
| Local source/build | `npm run typecheck`, `npm run test:boundaries` and `npm run build` passed. Boundary check inspected three implemented source files and ten allowed/forbidden import fixtures. Vite transformed 565 modules and produced a main bundle, lazy Foundation page chunk and stylesheet. |
| PHP / browser execution | Not available in the local executor at initial publication. Hosted exact-runtime installation, formatting, type analysis, PHP tests, Deptrac, canaries and actual browser hydration must be recorded from their real executions. |

The existing P00 PHP/browser measurements support the accepted dependency choice, but are not reused as a pass for these new application files. The Composer manifest has changed and must be resolved in its own application directory. An independent Console lock and actual execution evidence are required before claiming service verification.

## Code controls

The service-local Deptrac policy admits Laravel-native Domain models and Application DB/Gate orchestration while rejecting forbidden layer, transport and sibling-service dependencies. Thirteen temporary parser controls distinguish four permitted dependencies from nine exact intended failures and remove their injected source. Regular tests also require actual implementation classes, private autoload roots, strict types and final classes. There are no empty Domain/Application suites represented as implemented business coverage.

The frontend checker parses TypeScript module references and Vue SFC scripts. It disallows unregistered aliases/packages, sibling source escape, cross-context private imports, cross-context feature coupling, upward shared imports, computed imports and uncontrolled globs. Ten controls include both allowed local/public-interface imports and intended policy failures. The single bootstrap page glob is explicit. These checks are source constraints; dynamic execution, runtime response validation and all future authorization behavior still require their own controls. TypeScript compilation does not prove runtime input validity.

## Outstanding scope

The [Console specification](../services/console.md), [frontend standard](../engineering/frontend.md) and [P01 plan](phases/p01.md) remain authoritative for unfinished work. The current file session driver is for this local scaffold, not a measured highly available session design. No service container, proxy/CSP configuration, remote-service delegation, authentication provider, tenant switch, protected command, native operation, accessibility conformance or operating acceptance is claimed.

Record hosted failures as well as passing service-specific resolution/replay artifacts, retain their exact source/lock and runtime bindings, and update this record when results are available. Keep actual readiness closed until real dependencies and their checks are implemented. Subsequent deployment/qualification results must remain separate from this public foundation page.
