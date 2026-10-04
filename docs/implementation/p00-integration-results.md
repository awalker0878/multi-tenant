# P00 Laravel HTTP and quality-tool integration

P00.03 now has a successful source-bound execution of the isolated Laravel HTTP, PHP quality and Chromium integration probes. [Run 37226789018](https://github.com/awalker0878/multi-tenant/actions/runs/37226789018), source `fb03c98478ba0d533d330174f34dc50227de8a18`, passed all 26 recorded commands, including 20 Pest tests with 200 assertions and all 14 negative controls. Earlier failures and their corrections remain recorded below. This establishes the measured candidate's compatibility; it does not approve a product service, production image, native adapter or G00 gate.

## Scope and convention

The synthetic compatibility capability uses the service-local `App\\` namespace and normal Laravel bootstrap, providers, controllers, Form Requests, policies and resources. An Eloquent model owns its state-transition invariant. An Application Action exposes `handle`, authorizes through Gate and coordinates two writes within a transaction. This follows the selected pragmatic convention without installing Laravel Boost or the referenced DDD program.

Feature tests exercise full Laravel request handling, Inertia HTML/JSON responses and validation redirects. Authenticated test actors exercise scoped reads, foreign-tenant concealment, policy denial, direct Action authorization, malformed commands, successful transitions, stale/repeated transitions and rollback when the second write fails. These synthetic identities are test fixtures; no public login or real identity provider is implemented. SQLite rollback evidence does not prove production database locking or concurrency.

The public `/compatibility` page and its validation form allow an actual browser to exercise the built Vue/Inertia assets, session-backed validation errors, redirect notices and page continuity. The browser result is recorded separately in the [browser report](p00-browser-results.md).

## Tool checks

| Check | Required signal |
| --- | --- |
| Composer | Strict manifest validation, platform requirements, exact lock and installed-reference agreement after deleting `vendor` and reinstalling |
| Pint | Laravel style check without rewriting the source in the passing run |
| Larastan/PHPStan | Level 8 analysis of implemented application classes; no baseline or blanket ignored errors |
| Deptrac | Actual class/use dependencies; forbidden directions and uncovered dependencies fail |
| Pest architecture | Nonempty implemented namespaces, public non-static Action `handle`, permitted Eloquent domain model, private service-local autoloading |
| Negative controls | Temporary dependency, transport, type, formatting and Action-visibility faults must produce the expected failure and leave clean source restored |
| HTTP/model tests | Real requests and transactional behavior, including denied/invalid paths |
| Browser | Actual Chromium launch against PHP and built assets, with errors/reloads detected |
| Advisory checks | Current Composer and npm audit results for this experiment; not a comprehensive security assessment |

Generated clients belong behind the service's infrastructure adapters. Domain/Application cannot import sibling service implementations, HTTP delivery or Inertia. Framework persistence, Gate and Eloquent remain allowed under the selected Laravel convention. Python retains its separately enforced framework-free core; see the [Python tooling report](p00-python-tooling-results.md).

## Reproduction and evidence

The [workflow](../../.github/workflows/p00-php-compatibility.yml) uses pinned action revisions, PHP 8.5.11, Composer 2.10.3 and Node 24.19.0. The [orchestrator](../../spikes/compatibility/run-integration.py) copies inputs outside the checkout, uses bounded subprocesses, records each command, binds all spike inputs by SHA-256, and retains the lock and browser report even on failure. It permits only Composer's explicitly allowlisted Pest plugin; Composer scripts and npm dependency install scripts remain disabled. Normal reproduction uses `--dependency-mode install`; `resolve` is a distinct experimental dependency update.

The first implementation commit used `resolve` because the earlier lock lacked the new quality tools. [Run 37225914647](https://github.com/awalker0878/multi-tenant/actions/runs/37225914647), source `4b8a538ad7d605a5a4f3d0cc3a9e05641eaa9267`, resolved and clean-installed identical package versions/references, then failed Pint on `fully_qualified_strict_types` in two files. Its [report](../../spikes/compatibility/results/integration-37225914647/report.json) and actual command logs are retained. Explicit imports correct those issues without changing the rule. The measured dependency lock is now committed and push runs use `install`; full-suite success was still pending at that revision. Independent quality checks collect their own failures before the attempt is classified, so a style failure cannot silently count as another check passing. Earlier raw evidence remains unchanged. A failed command remains a failed attempt until its cause is fixed and a new source revision passes.

See the [delivery register](delivery-register.yaml) for authoritative work, verification and acceptance status. P00.03 remains in progress while the remaining runtime/owner and technical decisions are incomplete.

## Second attempt and corrections

[Run 37226133015](https://github.com/awalker0878/multi-tenant/actions/runs/37226133015), source `74b486c9fdd62d2b4574b060c6158ad1c998e4d0`, replayed the committed lock without changes. Pint passed 31 files. Deptrac and all 14 negative controls passed. Larastan correctly rejected an unnecessary nullable return type. Pest found a hardcoded origin assumption and missing test session continuity, and reported 11 warnings whose full diagnostics are enabled for the next run. The browser launched and received the actual validation error, but its response-matching assertion timed out; the [browser diagnostic](../../spikes/compatibility/results/browser/07-redirect-diagnostic.json) records the real exchanges without session values.

The [report](../../spikes/compatibility/results/integration-37226133015/report.json) and per-command logs retain these failures. Corrections narrow the middleware type, use the configured route origin, carry the real response session cookie between test requests and inspect browser response headers asynchronously. No boundary rule or validation assertion is disabled. Pest now fails on warnings, risky tests and an empty suite; command output includes full warning details. The browser server uses `APP_ENV=local`; PHPUnit selects its testing environment separately. Actual remote npm was 11.17.0, distinct from the earlier local 11.9.0 observation.

## Third attempt and runner configuration

[Run 37226550687](https://github.com/awalker0878/multi-tenant/actions/runs/37226550687), source `41d6bd28928eda76f2a82c0f5d539c2040a0c179`, passed Chromium's complete flow, Pint, Larastan, Deptrac, all negative controls, clean locks/builds and advisory checks. The overall attempt still **failed** Pest. Expanded diagnostics identified Dotenv reading the absent `.env` fixture. Seven POST tests returned 419 because the runner had also imposed the browser's `APP_ENV=local` on the test command, preventing its intended test environment. These are isolated harness failures; they do not establish application authorization failures or a passing PHP suite. The [raw report](../../spikes/compatibility/results/integration-37226550687/report.json) and [browser result](../../spikes/compatibility/results/integration-37226550687/browser.json) retain the distinction.

The correction supplies a comment-only `.env` inside the temporary PHP copy, keeps test execution in `APP_ENV=testing`, and applies `APP_ENV=local` only to the actual HTTP server process. It neither supplies credentials nor relaxes warnings or CSRF middleware. The successful complete replay below subsequently verified the HTTP/session assertions.

## Successful complete replay

The fourth attempt, [run 37226789018](https://github.com/awalker0878/multi-tenant/actions/runs/37226789018), passed from the committed lock without resolving new dependencies. The [source-bound report](../../spikes/compatibility/results/integration-37226789018/report.json), [retrieval verification](../../spikes/compatibility/results/integration-37226789018/retrieval.json) and command logs preserve the result beyond temporary CI artifact retention. The downloaded ZIP matched GitHub's SHA-256 digest; all 52 source input hashes matched the inspected files.

| Measured component or check | Result |
| --- | --- |
| Runtime | PHP 8.5.11; Composer 2.10.3; Node 24.19.0; npm 11.17.0; GitHub-hosted Ubuntu 24.04 x64 |
| Framework/adapter | Laravel 13.34.0; Inertia Laravel 3.5.1 |
| Quality tools | Pint 1.32.1; Larastan 3.12.2; PHPStan 2.2.16; Deptrac 4.7.2; Pest 4.7.8; Pest Laravel plugin 4.1.0 |
| Dependency replay | Strict validation and platform checks passed; deleting `vendor` and reinstalling preserved lock, package versions and source references |
| Pint / Larastan / Deptrac | 31 formatted PHP files; level 8 application analysis; allowed dependency graph passed with uncovered dependencies fatal |
| Pest | 20 tests passed, 200 assertions; warnings/risky/empty suite are fatal. Includes 14 behavior tests and 6 architecture tests |
| Negative controls | 11 forbidden dependency directions, incorrect return type, format fault/repair and private Action `handle` rejected for their intended reason; source restored |
| Frontend/browser | Clean npm install, strict Vue typecheck, Vite build and one real Chromium flow passed without retry/skip |
| Advisory lookup | Composer and npm returned no known advisories for the tested locks; time-specific package checks only |

The Composer lock SHA-256 is `2f4291ae8d40bf77cb83e5c558cf3eab22405214402f979051e6881d5f996d4f`. No assertion or architecture rule was weakened to obtain this result. Test and browser environment separation, fixture setup and response-header/session handling are part of the measured harness. The PHP tests prove SQLite rollback and synthetic tenant/policy behavior, not PostgreSQL row-lock semantics, concurrent writers, production SSO or full cross-service integration. Product source and native qualification remain unimplemented. Runtime image/mirror choices, managed-browser policy, remaining technical decisions and accountable adoption still keep P00.03/G00.03 open.

## Primary implementation references

The measured lock and command records establish compatibility. These primary sources explain the selected convention's framework/tool behavior: [Laravel authorization](https://laravel.com/docs/13.x/authorization), [Laravel providers](https://laravel.com/docs/13.x/providers), [Inertia server setup](https://inertiajs.com/docs/v3/installation/server-side-setup), [Pest configuration](https://pestphp.com/docs/configuring-tests), [Larastan](https://github.com/larastan/larastan), [Deptrac configuration](https://github.com/deptrac/deptrac/blob/4.x/docs/configuration.md) and [Pint](https://laravel.com/docs/13.x/pint). Current project ADR-024 remains authoritative for service/capability boundaries; upstream examples do not grant cross-service imports.
