# P00 runtime compatibility spike

This disposable probe supplies execution evidence for P00.03. It contains a Vue/Inertia browser entrypoint, synthetic Python behavior and tooling checks, and a Laravel HTTP/Eloquent probe with quality controls. It implements no application feature, public service contract or deployment. Do not import it from a product service. Laravel Boost and the author's DDD package are not dependencies; the project adopts only the documented convention.

Read the [execution report](../../docs/implementation/p00-compatibility-results.md) before interpreting results. Frontend and Python locks were resolved and exercised locally on 2026-10-04. PHP and Composer were unavailable locally; the later isolated Actions run resolved and replayed the PHP lock successfully. The initial TypeScript 7 failure remains recorded alongside the successful TypeScript 6 tuple.

## Contents and evidence

| Path | Purpose |
| --- | --- |
| `frontend/` | Exact npm lock, strict Vue type checking, Inertia 3/Vue 3/Tailwind 4/Vite 8 build probe |
| `python/` | uv lock, Python 3.12 family probe, synthetic positive/invalid-input/HTTP transport checks |
| `php/` | Laravel HTTP fixtures, model/Action/policy behavior, PHP quality tools and negative controls |
| `run-integration.py` | Isolated PHP lock replay, quality/HTTP tests and real Chromium run with source-bound evidence |
| `record.py` | Executes one command without a shell and records output, exit status, timestamps and input SHA-256 values |
| `results/` | Original local execution records, rejected initial frontend tuple and final artifact hashes |

The repository's product-source validator treats this exact directory as non-product experimental support code. That classification does not grant services permission to import spike files and does not exempt another unregistered spike directory. Generated dependency directories and build output are ignored; locks and command records are committed. Build output is reproducible from the recorded inputs, with its measured digest inventory retained in [final-artifacts.json](results/final-artifacts.json).

## Reproduce the accepted local checks

Use Node 24.19.0, npm 11.9.0, Python 3.12.14 and uv 0.12.19 to match this attempt. They are measured spike inputs, not approved production images. Commands below are relative to the named directory and must be completed in order. Dependency resolution and verification must never run concurrently in the same dependency directory.

In `frontend/`:

```sh
npm ci --ignore-scripts --no-audit --no-fund
npm run typecheck
npm run build
npm audit --json --audit-level=low
```

The clean installation deliberately disables dependency lifecycle scripts. The selected native build packages worked with their distributed platform binaries. Treat a different architecture or missing optional binary as a new compatibility result; do not silently enable all install scripts. These four commands do not launch a browser or HTTP server. The separate integration orchestrator starts PHP and Chromium; SSR remains disabled.

In `python/`:

```sh
uv sync --locked --python 3.12
uv run --frozen python smoke.py
```

Use an isolated environment without production credentials. The Python probe sends no external request: HTTPX uses an in-memory `MockTransport`. It verifies installed libraries and strict synthetic input handling, not a service contract or real network integration. The lock covers Python 3.12 only; another production Python family requires its own resolution and tests.

## Laravel HTTP and browser experiment

The [integration report](../../docs/implementation/p00-integration-results.md) describes the newly implemented checks and their current execution status. The first remote run explicitly resolves the new PHP quality-tool dependencies, then deletes `vendor` and reinstalls that same lock. Until the measured lock is committed, the previous lock represents the earlier dependency-only experiment.

The committed workflow runs the orchestrator outside the checkout with PHP 8.5.11, Composer 2.10.3 and Node 24.19.0. Reproduce a measured lock with:

```sh
python3 spikes/compatibility/run-integration.py --workspace "$PWD" --output /tmp/p00-integration-replay --dependency-mode install
```

Choose a new output directory for each attempt. `--dependency-mode resolve` is an explicit new dependency experiment. Composer's Pest plugin is the only allowlisted plugin; scripts remain disabled. npm installs also disable dependency lifecycle scripts. The browser installer explicitly installs the locked Playwright Chromium build and Linux dependencies, so use a disposable runner.

The public validation form is synthetic. Authenticated tenant and mutation behavior is exercised by injected test actors, not a public login. SQLite is a disposable test dependency and does not select or qualify the production database. No native platform operation runs. The Python quality experiment has its own commands and evidence in the [Python tooling report](../../docs/implementation/p00-python-tooling-results.md).

## Capture another attempt

From this directory, use a new result name. Options precede the result name; the command follows `--`:

```sh
python record.py --cwd frontend --timeout 180 rerun-frontend-typecheck -- npm run typecheck
```

The recorder refuses to replace an existing result. It records only command arguments, source/lock digests and command output, not environment variables. Supply no credentials in arguments or output. Every execution record identifies its contemporaneous inputs; later documentation changes do not invalidate the measured code/lock hashes. The authoritative package and gate states remain in the [delivery register](../../docs/implementation/delivery-register.yaml).

## PHP execution evidence

[Actions run 37224453605](https://github.com/awalker0878/multi-tenant/actions/runs/37224453605) passed at source commit `06df7bfb15d83eb5a180e10c0d6c65970c5b0a54`: PHP 8.5.11, Composer 2.10.3, Laravel 13.34.0 and Inertia Laravel 3.5.1. The historical Composer lock at source commit `9a214f6ea2f0bba02abb7959cbd2f3523efbba1c` and [source-bound report](results/php-ci/report.json) preserve that earlier run. Check out that revision to replay its dependency-only inputs; current source adds separate integration and quality-tool dependencies. Dependency updates are a new experiment, not a reproduction command. This probe does not prove full Laravel/Inertia HTTP behavior or a production image.
