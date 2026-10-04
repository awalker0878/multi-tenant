# P00 Laravel HTTP and quality-tool integration

P00.03 now includes executable Laravel HTTP, PHP quality and Chromium integration probes under `spikes/compatibility/`. This document records the experiment separately from the earlier dependency-only result. The new Composer development dependencies require a separately measured lock; the initial CI run explicitly resolves them before clean-install replay. Execution is pending at this revision. No product service, production image, native adapter or G00 approval is established by adding these probes.

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

The first implementation commit deliberately uses `resolve` for its push run because the earlier lock lacks the new quality tools. Once the result is retrieved, the measured lock and evidence will be committed and push runs will use `install`. Earlier raw evidence remains unchanged. A failed command remains a failed attempt until its cause is fixed and a new source revision passes.

See the [delivery register](delivery-register.yaml) for authoritative work, verification and acceptance status. P00.03 remains in progress while this execution and the remaining runtime/owner decisions are incomplete.
