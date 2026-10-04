# P00.03 compatibility execution report

Executed: 2026-10-04. Package: P00.03. Criterion: G00.03. Accountable review roles: engineering and SRE leads. This is an actual bounded spike report, not owner acceptance of ADR-003 or a completed G00 review.

The requested frontend stack built successfully and passed independent Vue/TypeScript checking after replacing an incompatible TypeScript 7 candidate with TypeScript 6.0.3. Python dependencies resolved, installed into a new isolated environment and passed the synthetic library probe. PHP, Composer and Docker were unavailable in the local runner. A subsequent isolated GitHub Actions run resolved the PHP candidate and passed the probe again after a clean lock reinstall. The subsequent [Python tooling experiment](p00-python-tooling-results.md) passed fresh locked installation, lint/format, strict typing, four behavior tests, three Import Linter contracts, seven expected boundary rejections and strict dependency advisory lookup. [Laravel HTTP and PHP quality integration](p00-integration-results.md) and [Chromium browser execution](p00-browser-results.md) subsequently passed all 26 commands in run `37226789018`, including 20 PHP tests/200 assertions and 14 negative controls. They have separate source-bound records and retain their initial failures. Production image checks and operating-owner decisions remain unresolved, so P00.03 is incomplete.

## Scope and artifact identity

[The spike](../../spikes/compatibility/README.md) is deliberately outside product source roots. Its dependencies and examples do not add features to the seven services or change the accepted context/capability convention. No historical branch source was copied into the probe. No Laravel Boost or DDD package was installed.

Each [command record](../../spikes/compatibility/results/11-environment.json) contains the exact command, working directory, UTC timestamps, stdout/stderr, command exit status and SHA-256 values of source/manifests/locks present when it ran. [The final artifact inventory](../../spikes/compatibility/results/final-artifacts.json) records final input and generated-asset sizes and hashes. The commit containing these files supplies the immutable repository identity; the delivery evidence entry binds that commit separately. Installed dependencies and generated bundles are excluded from source control.

| Input | Observed version or identity | Interpretation |
| --- | --- | --- |
| Local host | Linux 6.18.44, x86-64, glibc 2.39 | Existing execution environment; no production OS image selected |
| Node / npm | 24.19.0 / 11.9.0 | Actual frontend execution runtimes |
| Inertia client and Vite plugin | 3.8.0 / 3.8.0 | Resolved in npm lock |
| Vue / Vue Vite plugin | 3.5.43 / 6.0.9 | Resolved in npm lock |
| Vite / Laravel Vite plugin | 8.3.2 / 3.2.0 | Resolved and exercised in asset build |
| Tailwind / Tailwind Vite plugin | 4.3.3 / 4.3.3 | Resolved and exercised in CSS output |
| TypeScript / vue-tsc | 6.0.3 / 3.3.12 | Successful strict typecheck tuple; TypeScript 7.0.2 rejected below |
| Node type declarations | 24.19.1 | Resolved in npm lock; distinct from installed Node runtime patch |
| Python / uv | 3.12.14 / 0.12.19 | Actual isolated Python execution runtimes |
| Pydantic / HTTPX | 2.13.5 / 0.28.1 | Resolved in uv lock and exercised by probe |
| PHP / Composer | 8.5.11 / 2.10.3 in GitHub Actions | Actual remote probe runtimes; unavailable locally |
| Laravel / Inertia Laravel adapter | 13.34.0 / 3.5.1 | Resolved and replayed Composer lock; library/transaction smoke passed |
| Docker | Unavailable locally | Production image execution remains open |
| PHP lock | SHA-256 `ef1985e1756631f170f2ab2b8e0fb8e3cd0c34111ad54b87f99e3afa53b24c22` | Retrieved from successful Actions run; installed versions/references identical after clean reinstall |

The original frontend, Python and PHP locks are preserved at [the original evidence revision](https://github.com/awalker0878/multi-tenant/tree/9a214f6ea2f0bba02abb7959cbd2f3523efbba1c/spikes/compatibility). Current locks include subsequent tooling/browser experiments and are identified in their separate reports. Original command records retain their contemporaneous hashes; a link to the latest lock must not be interpreted as reproducing the earlier experiment.

## Commands and measured outcomes

Commands ran in the corresponding spike directory. The capture wrapper records full arguments, including bounded network timeout options, in the linked records.

| Check | Command | Actual outcome and evidence |
| --- | --- | --- |
| Initial frontend dependency resolution | `npm install --ignore-scripts --no-audit --no-fund` | PASS; [record 01](../../spikes/compatibility/results/01-frontend-resolve.json). Initial manifest and lock preserved separately. |
| Python dependency resolution | `uv lock --python 3.12` | PASS; [record 02](../../spikes/compatibility/results/02-python-lock.json). Index was `https://pypi.org/simple`. |
| PHP runtime discovery | `php --version` | UNAVAILABLE; [record 03](../../spikes/compatibility/results/03-php-runtime.json). No PHP command executed. |
| Composer discovery | `composer --version` | UNAVAILABLE; [record 04](../../spikes/compatibility/results/04-composer-runtime.json). No dependency resolution executed. |
| Initial strict Vue typecheck | `npm run typecheck` | FAIL with TypeScript 7.0.2; [record 05](../../spikes/compatibility/results/05-frontend-typecheck.json). |
| Initial production asset build | `npm run build` | PASS despite the failed typecheck; [record 06](../../spikes/compatibility/results/06-frontend-build.json). Demonstrates why both checks are required. |
| New isolated Python install | `uv sync --locked --python 3.12` | PASS; [record 07](../../spikes/compatibility/results/07-python-frozen-install.json). Created a new `.venv` from the lock. |
| Python library smoke | `uv run --frozen python smoke.py` | PASS; [record 08](../../spikes/compatibility/results/08-python-smoke.json). JSON round-trip, three invalid-input cases and local mock HTTP exchange. |
| Initial npm advisory check | `npm audit --json --audit-level=low` | PASS; [record 09](../../spikes/compatibility/results/09-frontend-audit.json). No advisory findings returned for that lock. |
| TypeScript candidate correction | `npm install --save-dev --save-exact typescript@6.0.3 --ignore-scripts --no-audit --no-fund` | PASS; [record 10](../../spikes/compatibility/results/10-typescript6-resolve.json). Required frontend major versions unchanged. |
| Runtime inventory | Python subprocess inventory | Captured exact versions and absent tools; [record 11](../../spikes/compatibility/results/11-environment.json). Inventory success is not stack compatibility. |
| Intermediate typecheck | `npm run typecheck` | INVALID ATTEMPT: [record 12](../../spikes/compatibility/results/12-typescript6-typecheck.json) failed because a concurrently started clean install removed files. Retained as an execution error, not a TypeScript 6 incompatibility claim. |
| Clean frontend lock installation | `npm ci --ignore-scripts --no-audit --no-fund` | PASS; [record 13](../../spikes/compatibility/results/13-frontend-clean-install.json). Replaced the dependency directory from the exact lock. |
| Strict Vue typecheck after install finished | `npm run typecheck` | PASS; [record 14](../../spikes/compatibility/results/14-clean-frontend-typecheck.json). Strict mode; dependency declaration checking remains enabled. |
| Production asset build from clean installation | `npm run build` | PASS; [record 15](../../spikes/compatibility/results/15-clean-frontend-build.json). Generated JS/CSS and Laravel Vite manifest. |
| Final npm advisory check | `npm audit --json --audit-level=low` | PASS; [record 16](../../spikes/compatibility/results/16-final-frontend-audit.json). No advisory findings returned for the final lock. This is not an OS/PHP/Python or comprehensive security audit. |
| Final direct dependency inventory | `npm ls --depth=0 --json` | PASS; [record 17](../../spikes/compatibility/results/17-resolved-frontend-versions.json). |
| Resolved production browser targets | Vite `resolveConfig` via Node | Captured actual JS/CSS targets; [record 18](../../spikes/compatibility/results/18-build-targets.json). Browser execution was not performed. |

All npm commands emitted an inherited `http-proxy` environment-configuration warning. It did not prevent resolution or build; the runner should remove that obsolete npm configuration before it becomes a future package-manager incompatibility.

## Compatibility findings

**TypeScript must be pinned to the proven tuple.** The installed `vue-tsc` 3.3.12 attempts to load `typescript/lib/tsc`, which TypeScript 7.0.2 does not export. The failure is `ERR_PACKAGE_PATH_NOT_EXPORTED`, before application type analysis. Preserve [the initial manifest](../../spikes/compatibility/results/initial-frontend-package.json) and [initial lock](../../spikes/compatibility/results/initial-frontend-package-lock.json) to reproduce it in a separate temporary directory. TypeScript 6.0.3 passes with the same Vue checker. Revisit this exact pair in a dependency-update spike before changing either member; do not skip type checking or add blanket declaration suppressions.

**Build targets and a supported browser fleet are different decisions.** The resolved Vite targets were Chrome/Edge 111, Firefox 114, Safari/iOS 16.4. Tailwind's documented core floor is Chrome 111, Safari 16.4 and Firefox 128 [S4]. Therefore Firefox 114 cannot become the combined-stack support floor merely because it appears in the bundler configuration. These are compatibility constraints; managed-browser inventory, current security support and actual browser/accessibility tests still determine the supported product matrix.

**The initial backend probe established a bounded baseline.** Laravel's published 13.x matrix includes PHP 8.3–8.5, and the Inertia Laravel 3.x manifest includes Laravel 13 [S1, S2]. Those upstream declarations alone did not establish that this project's complete tool/runtime set worked. The initial remote probe exercised synthetic Eloquent writes and rollback on SQLite plus Inertia class autoload. The later [integration report](p00-integration-results.md) now proves the bounded Laravel HTTP, quality-tool and browser checks. Production image and PostgreSQL concurrency qualification remain separate.

**The Python tuple is a measured probe, not the final service runtime decision.** The available Python 3.12 family is in security maintenance through October 2028 [S6]. Engineering/SRE must decide the service runtime family and patch/update ownership; any different family needs its own locked execution evidence. HTTPX and Pydantic are spike candidates, not an authorization to add them to every Python service.

## Work still required for G00.03

| Remaining work | Responsible role | Concrete completion evidence |
| --- | --- | --- |
| Adopt the demonstrated HTTP/tooling candidate | PHP/frontend leads | Review the passing isolated Laravel/Inertia, Pint/Larastan/Pest/Deptrac and Chromium results; carry the rules into service-specific P01 checks without treating synthetic fixtures as product implementation |
| Choose supported production runtime and image identities | SRE and engineering leads | Accepted ADR-003 scope, immutable image digests, extension list, runtime support/update owner and clean image build |
| Approve browser support and accessibility matrix | Product/frontend/endpoint owners | Actual managed browser facts, accepted floors, real browser checks and measured accessibility scope |
| Adopt the measured quality-tool candidates | Engineering leads | Accountable runtime/tool adoption and update ownership; map candidate rules to actual registered services, workers and packages and execute P01 gates. Locked synthetic Python tool compatibility is demonstrated. |
| Decide infrastructure, trust, custody and contract-generation choices | Owning NOW ADR reviewers | Accountable decisions and evidence links for P00.03; this spike does not select an identity provider, broker, database, orchestrator, secrets service or evidence store |
| Verify restricted-network dependency path | Platform/security leads | Approved mirror identities and freshness, controlled resolution/audit path and clean build using it; public npm/PyPI access here is insufficient |

The first PHP workflow at `ad43dbf565769a5e46761881b968af2003db7af6` was rejected before creating a job because runner paths were referenced at job-environment scope. Commit `06df7bfb15d83eb5a180e10c0d6c65970c5b0a54` moved them into the execution step; [run 37224453605](https://github.com/awalker0878/multi-tenant/actions/runs/37224453605) then passed all 12 probe commands. This was a workflow configuration correction, not a PHP dependency failure. The [source-bound report](../../spikes/compatibility/results/php-ci/report.json), [command results](../../spikes/compatibility/results/php-ci/probe.json), [retrieval digest record](../../spikes/compatibility/results/php-ci/retrieval.json) and [original Composer lock](https://github.com/awalker0878/multi-tenant/blob/9a214f6ea2f0bba02abb7959cbd2f3523efbba1c/spikes/compatibility/php/composer.lock) preserve the exact outcome independently of temporary Actions artifact retention. The ZIP digest matched the GitHub artifact digest; copied input files matched the reviewed source.

The original dependency-only sequence records runtime/extensions, resolves dependencies with plugins/scripts disabled, validates the manifest/lock, checks platform requirements, runs the synthetic probe, removes vendor files, installs from the unchanged lock, repeats validation/platform/probe checks and compares package versions/source references. The broad runner extension inventory is an observed test environment, not the selected production extension allowlist. The initial local unavailable-tool records and frontend failure remain preserved. The [canonical register](delivery-register.yaml), [G00 review](../qualification/gate-reviews/g00.md) and [ADR-003](../decisions/adr-003-runtime-and-dependency-baseline.md) determine delivery and decision status.

## Primary compatibility references

Reviewed 2026-10-04. Package locks and command records above are the authority for the actual tested tuple; upstream pages support only the stated compatibility/lifecycle constraints.

| Ref | Primary source | Use |
| --- | --- | --- |
| S1 | [Laravel 13 release support matrix](https://laravel.com/docs/13.x/releases) | PHP family compatibility and framework support policy |
| S2 | [Inertia Laravel 3.x Composer requirements](https://github.com/inertiajs/inertia-laravel/blob/3.x/composer.json) | Upstream declared Laravel/PHP requirements; branch source is not a resolved project lock |
| S3 | [Inertia 3 client setup](https://inertiajs.com/docs/v3/installation/client-side-setup) and [Vite getting started](https://vite.dev/guide/) | Vue/Inertia Vite configuration, Vite 8 compatibility and Node floor |
| S4 | [Tailwind compatibility](https://tailwindcss.com/docs/compatibility) | CSS browser floor |
| S5 | [Node release status](https://nodejs.org/en/about/previous-releases) and [PHP supported versions](https://www.php.net/supported-versions.php) | Runtime family support review; not a claim that the installed patch is the latest |
| S6 | [Python version status](https://devguide.python.org/versions/) | Python 3.12 security-maintenance horizon |
