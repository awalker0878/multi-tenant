# P00 runtime compatibility spike

This disposable probe supplies execution evidence for P00.03. It contains a Vue/Inertia asset entrypoint, a synthetic Python validation/HTTP-library check and a PHP Eloquent/Inertia probe. It implements no application feature, public service contract or deployment. Do not import it from a product service. Laravel Boost and the author's DDD package are not dependencies; the project adopts only the documented convention.

Read the [execution report](../../docs/implementation/p00-compatibility-results.md) before interpreting results. Frontend and Python locks were resolved and exercised locally on 2026-10-04. PHP and Composer were unavailable locally; the later isolated Actions run resolved and replayed the PHP lock successfully. The initial TypeScript 7 failure remains recorded alongside the successful TypeScript 6 tuple.

## Contents and evidence

| Path | Purpose |
| --- | --- |
| `frontend/` | Exact npm lock, strict Vue type checking, Inertia 3/Vue 3/Tailwind 4/Vite 8 build probe |
| `python/` | uv lock, Python 3.12 family probe, synthetic positive/invalid-input/HTTP transport checks |
| `php/` | Candidate PHP 8.5/Laravel 13/Inertia 3 Composer requirements; SQLite transaction and autoload probe |
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

The clean installation deliberately disables dependency lifecycle scripts. The selected native build packages worked with their distributed platform binaries. Treat a different architecture or missing optional binary as a new compatibility result; do not silently enable all install scripts. No browser, Laravel HTTP server or SSR server is started by these checks.

In `python/`:

```sh
uv sync --locked --python 3.12
uv run --frozen python smoke.py
```

Use an isolated environment without production credentials. The Python probe sends no external request: HTTPX uses an in-memory `MockTransport`. It verifies installed libraries and strict synthetic input handling, not a service contract or real network integration. The lock covers Python 3.12 only; another production Python family requires its own resolution and tests.

In `php/`, with PHP 8.5, Composer and the required extensions supplied:

```sh
composer install --no-interaction --prefer-dist --no-plugins --no-scripts
composer validate --strict
composer check-platform-reqs
php smoke.php
composer audit --locked
```

The first command installs the committed lock without running plugins or scripts. Record the exact PHP/Composer/extension identities and rerun the probe in a fresh directory. A dependency update must be captured as a separate experiment. A successful resolver is insufficient on its own. SQLite is a disposable test dependency; it does not select the production database. The probe tests a local Eloquent commit and rollback and Inertia adapter autoloading, not a complete Laravel request lifecycle. PHP quality tools and framework HTTP integration remain separate follow-up checks.

## Capture another attempt

From this directory, use a new result name. Options precede the result name; the command follows `--`:

```sh
python record.py --cwd frontend --timeout 180 rerun-frontend-typecheck -- npm run typecheck
```

The recorder refuses to replace an existing result. It records only command arguments, source/lock digests and command output, not environment variables. Supply no credentials in arguments or output. Every execution record identifies its contemporaneous inputs; later documentation changes do not invalidate the measured code/lock hashes. The authoritative package and gate states remain in the [delivery register](../../docs/implementation/delivery-register.yaml).

## PHP execution evidence

[Actions run 37224453605](https://github.com/awalker0878/multi-tenant/actions/runs/37224453605) passed at source commit `06df7bfb15d83eb5a180e10c0d6c65970c5b0a54`: PHP 8.5.11, Composer 2.10.3, Laravel 13.34.0 and Inertia Laravel 3.5.1. The resolved [Composer lock](php/composer.lock) and [source-bound report](results/php-ci/report.json) preserve the run. Use `composer install --no-interaction --prefer-dist --no-plugins --no-scripts`, then validation/platform checks and `php smoke.php` to replay this lock on a compatible PHP runner. Dependency updates are a new experiment, not a reproduction command. This probe does not prove full Laravel/Inertia HTTP behavior or a production image.
