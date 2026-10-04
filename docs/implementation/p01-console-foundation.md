# P01 Console foundation

Owner role: Console maintainer. Phase/work package: P01 / P01.01. Date: 2026-10-04. Status: private lock replay, PHP/frontend quality and hosted Chromium foundation checks passed; image packaging and corrective verification are recorded separately. This increment does not complete G01.

## Implemented boundary

`apps/console/` is an independent Laravel browser application following accepted ADR-003, ADR-005, ADR-019 and ADR-024. It has a private Composer manifest/autoload root and npm manifest/lock, explicit Laravel bootstrap/configuration, Inertia middleware, Vue page resolution, strict TypeScript, Tailwind/Vite compilation, HTTP and architecture suites, and a real-browser foundation test. No Boost or convention-author package is installed. The seven-deployable design and independent business ownership are unchanged.

The public `/` entrypoint renders the product name and an honest foundation-state explanation through the `Foundation` page. Only `productName` and `implementationState` are explicitly supplied. There is no authentication simulation, local privileged actor, tenant data, dashboard metric or workload operation. `/health/live` reports process liveness; `/health/ready` remains `503 foundation_only` and cannot be enabled by an environment flag or client-supplied value. Health endpoints do not start browser sessions.

The server session uses a named Console cookie with Secure-by-default, HttpOnly and SameSite=Lax flags. Web responses are private/no-store with framing, MIME-sniffing and referrer headers. The HTTP test suite exercises initial HTML, Inertia JSON, explicit page disclosure, cookie attributes, route absence, health behavior and request-forgery middleware. The CSRF negative/positive tests register a test-only route and deliberately exit Laravel's `testing` environment to exercise real token verification; no product mutation route is created for the test.

## Dependencies and measured checks

| Input/check | Observed state and evidence |
| --- | --- |
| PHP framework | Manifest selects PHP `~8.5.0`, Laravel `13.34.0`, Inertia Laravel `3.5.1` and measured P00 quality-tool versions. Required PostgreSQL extension is declared; no database connection or product persistence is configured. |
| Composer lock | Private resolved lock replayed unchanged in run 37239193553; SHA256 `926d7cd6f70cea71f705e6233ee2c2a219f5824c5a08faeece99068d3f7fd913`. Both installs produced equal package versions/references. |
| Browser dependencies | Private npm lock retains Inertia Vue/Vite `3.8.0`, Vue `3.5.43`, TypeScript `6.0.3`, Tailwind `4.3.3`, Vite `8.3.2`, Vue plugin `6.0.9`, Laravel Vite plugin `3.2.0`, Vue TSC `3.3.12`, Node types `24.19.1`, Playwright `1.63.0`. |
| Local installation | Node `24.19.0`, npm `11.9.0`; `npm ci --ignore-scripts --no-audit --no-fund` passed with 77 installed packages. No advisory assessment is claimed by this command. |
| Local source/build | `npm run typecheck`, `npm run test:boundaries` and `npm run build` passed. Boundary check inspected three implemented source files and ten allowed/forbidden import fixtures. Vite transformed 565 modules and produced a main bundle, lazy Foundation page chunk and stylesheet. |
| PHP / browser execution | Hosted run 37239193553 passed 23 expected commands, 24 Pest tests / 86 assertions, formatting, type analysis, Deptrac/canaries, cached HTTP probes and one Chromium hydration test with no retries, skips or unexpected outcomes. |

The [package record](p01-laravel-foundations.md) binds the independent Console lock and actual source at `4142571874a53b351a9c6023313185fe718d0dac`; its [Console report](../../verification/p01/packages/run-37239193553/console/report.json) preserves the raw observations. The earlier Pest exception-handler binding failure remains in the failed-run record. P00 measurements do not substitute for these product-source results.

## Code controls

The service-local Deptrac policy admits Laravel-native Domain models and Application DB/Gate orchestration while rejecting forbidden layer, transport and sibling-service dependencies. Thirteen temporary parser controls distinguish four permitted dependencies from nine exact intended failures and remove their injected source. Regular tests also require actual implementation classes, private autoload roots, strict types and final classes. There are no empty Domain/Application suites represented as implemented business coverage.

The frontend checker parses TypeScript module references and Vue SFC scripts. It disallows unregistered aliases/packages, sibling source escape, cross-context private imports, cross-context feature coupling, upward shared imports, computed imports and uncontrolled globs. Ten controls include both allowed local/public-interface imports and intended policy failures. The single bootstrap page glob is explicit. These checks are source constraints; dynamic execution, runtime response validation and all future authorization behavior still require their own controls. TypeScript compilation does not prove runtime input validity.

## Outstanding scope

The [Console specification](../services/console.md), [frontend standard](../engineering/frontend.md) and [P01 plan](phases/p01.md) remain authoritative for unfinished work. The current file session driver is for this local scaffold, not a measured highly available session design. The [image record](p01-laravel-images.md) retains the initial missing-page packaging failure and the corrective image execution that includes the server-side Inertia page lookup inputs. This is separate from integrated ingress/proxy/CSP configuration, remote-service delegation, authentication, tenant switching, protected commands, native operations, accessibility conformance or operating acceptance.

Preserve the source/lock/runtime bindings of both failed and passing executions; later source or dependency changes require affected checks. Keep actual readiness closed until real dependencies and their checks are implemented. Subsequent deployment/qualification results must remain separate from this public foundation page.
