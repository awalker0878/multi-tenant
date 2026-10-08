# P01 Laravel foundations and complete package replay

Date: 2026-10-04. Work packages: P01.01/P01.04. Evidence: EV-P01-007. These results verify independent package foundations; P01 and G01 remain in progress and unreviewed respectively.

## Executed source and dependency replay

[Package run 37239193553](https://github.com/awalker0878/multi-tenant/actions/runs/37239193553) passed all nine component jobs at source `4142571874a53b351a9c6023313185fe718d0dac`. The [retrieval index](../../verification/p01/packages/run-37239193553/retrieval.json) binds artifact identities and checksums; [source verification](../../verification/p01/packages/run-37239193553/source-verification.json) binds 226 unique input files to that immutable commit. This is the measured revision, not an assertion that every later edit was executed by this run.

Each component was copied into its own clean directory without sibling application source, installed dependencies or earlier verification output. PHP used the committed private Composer lock in explicit `replay` mode. Both installation passes preserved the lock and produced equal installed package versions/references. Python used its private lock, quality checks and independently installed wheel. All 158 recorded commands had their expected outcomes; 316 command-log hashes and 350 retained package-artifact hashes were checked. Browser and wheel envelopes preserve the corresponding binary report/build bytes.

| Component | Runtime checks observed | Report |
| --- | --- | --- |
| Governance | 15 commands; 14 Pest tests / 44 assertions; locked install, quality, boundary canaries and cached HTTP boot | [Governance](../../verification/p01/packages/run-37239193553/governance/report.json) |
| Catalogue | 15 commands; 14 Pest tests / 44 assertions; locked install, quality, boundary canaries and cached HTTP boot | [Catalogue](../../verification/p01/packages/run-37239193553/catalogue/report.json) |
| Assurance | 15 commands; 14 Pest tests / 44 assertions; locked install, quality, boundary canaries and cached HTTP boot | [Assurance](../../verification/p01/packages/run-37239193553/assurance/report.json) |
| Console | 23 commands; 24 Pest tests / 86 assertions; PHP/frontend quality, production asset build and one passing Chromium test, without retries, skips or unexpected results | [Console](../../verification/p01/packages/run-37239193553/console/report.json) |
| Planning | 18 commands; private locked installation, Ruff, mypy, tests, wheel and isolated installed diagnostics | [Planning](../../verification/p01/packages/run-37239193553/planning/report.json) |
| Inventory | 18 commands; private locked installation, Ruff, mypy, tests, wheel and isolated installed diagnostics | [Inventory](../../verification/p01/packages/run-37239193553/inventory/report.json) |
| Lifecycle | 18 commands; private locked installation, Ruff, mypy, tests, wheel and isolated installed diagnostics | [Lifecycle](../../verification/p01/packages/run-37239193553/lifecycle/report.json) |
| Inventory worker | 18 commands; private locked installation, Ruff, mypy, tests, wheel and isolated installed diagnostics | [Inventory worker](../../verification/p01/packages/run-37239193553/inventory-workers/report.json) |
| Lifecycle worker | 18 commands; private locked installation, Ruff, mypy, tests, wheel and isolated installed diagnostics | [Lifecycle worker](../../verification/p01/packages/run-37239193553/lifecycle-workers/report.json) |

The PHP checks used PHP 8.5.11 and Composer 2.10.3; Console used Node 24.19.0. Python checks used Python 3.12.14 and uv 0.12.19. The hosted environment was Ubuntu 24.04. The exact framework, direct/transitive dependency and interpreter inventories remain in each report and its retained logs.

| Private Composer lock | SHA256 |
| --- | --- |
| Governance | `e5ddd1d1218174f0be042650de80d9b4df67ce3c73749e761384890ff340a988` |
| Catalogue | `398e228c419850ce2061c606ca5f48211a57c3785d9d97e5763f8461c2be992a` |
| Assurance | `9dacdf289986884e8f016d602b608403ecc687f306cb273bc15c18537443ac96` |
| Console | `926d7cd6f70cea71f705e6233ee2c2a219f5824c5a08faeece99068d3f7fd913` |

The committed PHP locks are now private resolved locks. The earlier P00 resolver seeds are historical inputs and are no longer described as the current installation baseline. Ordinary package verification uses replay; later dependency changes require an explicit reviewed resolution followed by replay.

## Failures retained alongside the passing replay

[Initial package run 37238718424](https://github.com/awalker0878/multi-tenant/actions/runs/37238718424), source `af1bf00ad84831a84817975e2ffc124190e3bdcc`, resolved private locks but failed its overall outcome: Governance, Catalogue and Assurance failed Pint, and Console failed Pest with an unbound Laravel exception-handler contract. The source and test bootstrap corrections were measured by the successful replay above. The [initial retrieval index](../../verification/p01/packages/run-37238718424/retrieval.json) preserves those failures and five passing Python outcomes; they are not relabelled as a pass.

That initial upload omitted four `application-logs/.gitignore` marker files because the artifact uploader excluded hidden files. Its retrieval metadata records the exact omissions. Actual command/application logs, manifests, locks and relevant binary envelopes are retained. The replay workflow includes hidden files, and all replay artifact entries were present and hash-verified.

## Implemented behavior and remaining boundary

Governance, Catalogue and Assurance expose diagnostic HTTP liveness and deliberately unavailable readiness. Their private Composer/autoload roots, formatting, static analysis, actual HTTP/class tests and positive/negative Deptrac canaries passed. Domain aggregates, authorization, tenant persistence, database migrations and outbox/inbox behavior remain unimplemented. Canary fixtures measure parser/rule behavior; they do not stand in for product Domain or Application code.

Console additionally serves the public Inertia foundation page, explicit page props, production-built Vue assets and secure-by-default cookie/header configuration. The browser observation covers the existing foundation page only. Authenticated sessions, remote-service delegation, tenant journeys, accessibility conformance and multi-replica session operation remain future work. The [Console record](p01-console-foundation.md) and [Governance record](p01-governance-bootstrap.md) describe their checks in detail.

Python components remain one-shot process diagnostics, with no running collector, workflow consumer or native operation. For all components, liveness does not establish service readiness: Laravel readiness stays HTTP 503 and Python readiness exits unavailable. No dependency-readiness bypass was added.

The [image record](p01-laravel-images.md) separately binds the eight passing images, retained Console packaging failure and successful corrective Console image run. [Code-control observations](p01-code-control.md) distinguish tested CI feedback from actual protected admission. Neither package nor image results establish operated signing, deployment, inter-service contracts, identity/data isolation, recovery or G01 acceptance. Next implement the isolated P01.02 topology and P01.05 dependency boundaries, then retain actual installation and denial observations.
