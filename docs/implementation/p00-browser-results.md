# P00.03 browser transport probe

Recorded: 2026-10-04. Package: P00.03. Criterion: G00.03. Review roles: frontend, PHP and SRE leads.

The disposable Laravel/Inertia application passed its actual Chromium flow in [run 37226789018](https://github.com/awalker0878/multi-tenant/actions/runs/37226789018), alongside the complete PHP suite and clean build checks. One test executed with no failures, retries or skips. It verified server props, validation and successful redirects, Inertia JSON, no document reload and no JavaScript errors. The earlier response-matcher failure and its trace-based correction remain documented below. This is a synthetic compatibility result, not G00 acceptance.

## Implemented scope

The [Vue fixture](../../spikes/compatibility/frontend/resources/js/Pages/Compatibility.vue) receives server props and submits one synthetic name through Inertia's form helper. The [browser test](../../spikes/compatibility/frontend/tests/browser/compatibility.spec.ts) checks initial HTML hydration, a server validation error, a successful redirect with a notice, and the absence of a full page reload or JavaScript exceptions. Both form submissions must return an actual Inertia JSON response. A successful asset build alone cannot satisfy this check.

| Fixture interface | Contract |
| --- | --- |
| `GET /compatibility` | Inertia component `Compatibility`; `sampleCount: 0`, `notice: null` or the flashed success string; shared validation errors |
| `POST /compatibility/validate` | Laravel validation: name required, string, length 3–40; standard session/CSRF middleware |
| Invalid input | Redirect back; the rendered form exposes the server error and marks the input invalid |
| Valid input | Redirect to the fixture page; notice `Compatibility request accepted` |

These public routes exercise transport only. They do not store a product object, implement authentication, authorize tenant changes, or contact a platform. Protected tenant/policy behavior belongs to the separate PHP integration checks. No fixture becomes a product service through this spike.

## Dependency and browser identities

| Input | Resolved value | Evidence |
| --- | --- | --- |
| Node / npm locally | 24.19.0 / 11.9.0 | Existing runtime baseline; Node repeated in the browser registry inventory |
| Node / npm in the first browser CI run | 24.19.0 / 11.17.0 | Runtime inventory from run 37226133015; different bundled npm patch, same declared 11.x engine family |
| Playwright test / runner / core | 1.63.0 / 1.63.0 / 1.63.0 | [npm lock](../../spikes/compatibility/frontend/package-lock.json) |
| Bundled execution engine | Chromium Headless Shell 153.0.8010.12; Playwright revision 1243 | [Installed package browser registry](../../spikes/compatibility/results/browser/06-browser-registry.json); actual Chromium version 153.0.8010.12 captured in the failed run's browser attachment |
| Frontend tuple | Inertia 3.8.0, Vue 3.5.43, Vite 8.3.2, Tailwind 4.3.3 | [Installed package inventory](../../spikes/compatibility/results/browser/05-package-inventory.json) |
| Independent type checker | TypeScript 6.0.3; vue-tsc 3.3.12 | Same proven tuple retained; type checking includes the browser configuration and test |

The Playwright dependency is exact-pinned; its browser revision comes from the locked package. The test attaches the actual launched engine name and version to its result. The default project uses the bundled headless shell, not installed managed Chrome or Edge. The browser package and its system dependencies must be installed separately from `npm ci`. Playwright's [browser documentation](https://playwright.dev/docs/browsers) explains the version coupling and shell install option; its [configuration reference](https://playwright.dev/docs/test-configuration) defines the selected bounded execution controls.

## Actual local outcomes

Each immutable record captures arguments, UTC times, exit status, output and frontend source/lock hashes. Dependency directories, generated assets and test caches are not repository inputs. npm continues to emit the inherited `http-proxy` configuration warning described in the earlier report.

| Command | Outcome | Record |
| --- | --- | --- |
| `npm ci --ignore-scripts --no-audit --no-fund` | PASS | [Clean installation](../../spikes/compatibility/results/browser/01-clean-install.json) |
| `npm run typecheck` | PASS | [Strict type check](../../spikes/compatibility/results/browser/02-typecheck.json) |
| `npm run build` | PASS | [Production asset build](../../spikes/compatibility/results/browser/03-build.json) |
| `npm exec -- playwright test --list` | PASS; one Chromium test discovered; none executed | [Discovery](../../spikes/compatibility/results/browser/04-test-discovery.json) |
| `npm ls --depth=0 --json` | PASS | [Installed package inventory](../../spikes/compatibility/results/browser/05-package-inventory.json) |
| Node inspection of installed Playwright browser registry | PASS; expected browser identity read; browser not launched | [Registry inventory](../../spikes/compatibility/results/browser/06-browser-registry.json) |

## First remote execution and correction

[Run 37226133015](https://github.com/awalker0878/multi-tenant/actions/runs/37226133015), source commit `74b486c9fdd62d2b4574b060c6158ad1c998e4d0`, launched Chromium 153.0.8010.12 and built/served the real Laravel fixture. Its browser test timed out waiting for the validation response. The [retained result](../../spikes/compatibility/results/integration-37226133015/browser.json) records the failure. The [trace diagnostic](../../spikes/compatibility/results/browser/07-redirect-diagnostic.json) retains selected actual network entries with the original trace archive and network-member hashes; session and CSRF values are omitted.

The trace shows initial HTML `GET /compatibility` returning 200, the empty-name Inertia POST returning 302, and the redirected GET returning 200 with JSON `props.errors.name` set to `The name field is required.` Both the request and response include `X-Inertia: true`; the rendered error is visible in the failure snapshot. This is not evidence of an Inertia protocol change or broken server-side validation. The test's synchronous `request.headers()` predicate did not match the redirected request. The corrected matcher reads the actual response header asynchronously, then asserts complete request headers with `allHeaders()`, JSON content and the rendered state. The one-document-navigation and JavaScript-error assertions remain required. At that failed revision, the valid submission and final no-reload checks were unproven; the successful runs below subsequently exercised them.

## Reproduction and remote evidence

From `spikes/compatibility/frontend`, use the locked Node/npm family, run the clean install, type check and build commands above, then `npm run browser:install`. The install command selects only the Chromium headless shell and its OS dependencies. Copy `public/build` into the sibling PHP fixture's `public/build` directory. From that PHP directory, set `APP_ENV=local`, `APP_URL=http://127.0.0.1:8000` and `APP_KEY` to a freshly generated Laravel application key, then run `php artisan serve --host=127.0.0.1 --port=8000`. The fixture bootstrap prepares writable session/cache/view/log directories. Its public form needs no database. Use Laravel's HTTP application for this check.

Run `P00_BASE_URL=http://127.0.0.1:8000 npm run browser:test`. `P00_BASE_URL` may select the actual loopback port. `PLAYWRIGHT_JSON_OUTPUT_FILE` selects a retained result path; otherwise the report is generated at `frontend/test-results/browser.json`. The [configuration](../../spikes/compatibility/frontend/playwright.config.ts) limits execution to one worker, no retries, 30 seconds per test and 90 seconds overall. Failures retain traces and screenshots in the ignored test-results directory; video is disabled. Raw JSON results and command logs must be captured before temporary CI artifacts expire. No passing trace or generated bundle needs to enter source control.

Remote evidence must bind the tested commit, lock and source hashes, runtime inventory, server startup, asset copy, browser installation and test result. Record an unsuccessful run as a failure before rerunning a correction. Only a successful real browser run can change the browser execution status above.

## Limits and remaining decisions

This single synthetic flow does not establish the managed-browser support matrix, accessibility conformance, production SSO/session behavior, CSP policy, SSR, reverse-proxy behavior, PostgreSQL compatibility, concurrency safety, native platform execution or a restricted-network installation path. Firefox, WebKit, managed Chrome/Edge and assistive technologies remain untested. The endpoint owners still need to supply the supported fleet and policies; later product journeys require their own tests. G00.03 and ADR-003 remain subject to their other integration, tooling, runtime and owner-decision evidence.

## First successful browser execution

[Run 37226550687](https://github.com/awalker0878/multi-tenant/actions/runs/37226550687) at source `41d6bd28928eda76f2a82c0f5d539c2040a0c179` passed the corrected browser test without retries or skips. Its [JSON result](../../spikes/compatibility/results/integration-37226550687/browser.json) and [command output](../../spikes/compatibility/results/integration-37226550687/browser.log) record the actual Chromium execution against the Laravel server in `APP_ENV=local`. The full experiment still failed its independent Pest check; browser success does not conceal that outcome or satisfy product authentication, managed-fleet or G00 acceptance.

The later **complete green run 37226789018**, source `fb03c98478ba0d533d330174f34dc50227de8a18`, also passed this browser flow. Its [JSON result](../../spikes/compatibility/results/integration-37226789018/browser.json) binds the engine attachment and executed test; [the integration report](p00-integration-results.md) records the full PHP/browser result and verified input hashes. The actual engine was Chromium 153.0.8010.12, with Playwright 1.63.0, Node 24.19.0 and npm 11.17.0 on the remote runner.
