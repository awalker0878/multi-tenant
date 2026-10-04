# P01 Governance Laravel foundation

Date: 2026-10-04. Work package: P01.01. Related checkpoints: G01.01/G01.02; later Governance behavior belongs to P02. This record describes the first real service source and separates authored checks from executed evidence.

## Implemented scope

`services/governance/` is an independent API-only Laravel application with the private `product/governance` package and service-local `App\` namespace. Its `HealthController`, provider, bootstrap, JSON exception rendering, routes, configuration and entrypoints do not include compatibility spike business entities. It includes no Boost program, Inertia frontend, default user, privileged tenant or fallback authorization.

The process answers `/health/live` with `200` and process scope. `/health/ready` always returns `503` with `foundation_only` until real readiness dependencies and authority checks are implemented. Request fields, environment switches and bearer-looking input cannot turn this into an authority service. The endpoints do not access persistence or remote services. Business paths remain absent. Responses suppress exception diagnostics and do not establish browser sessions.

The configuration declares a future service-private PostgreSQL connection without default endpoint, database or credentials and with verified TLS as the default. No connection has been made and no schema, migration, database isolation or tenant guarantee is claimed. Application and cache runtime directories are explicitly present; bootstrap performs no remote calls, migration or directory permission changes.

## Dependency and quality scope

The manifest pins Laravel 13.34.0, Pint 1.32.1, Larastan 3.12.2, PHPStan 2.2.16, Deptrac 4.7.2, Pest 4.7.8, Pest Laravel 4.1.0 and Mockery 1.6.15 on the accepted PHP 8.5 development family. Transitive versions must come from Composer resolution and a captured private lock; they are not manually authored. The initial source commit used the measured P00 lock as an explicit resolver seed. The current private Governance lock was resolved and retained, then replayed unchanged in [package run 37239193553](p01-laravel-foundations.md) at source `4142571874a53b351a9c6023313185fe718d0dac`. Its SHA256 is `e5ddd1d1218174f0be042650de80d9b4df67ce3c73749e761384890ff340a988`.

| Check | Authored coverage | Execution status |
| --- | --- | --- |
| HTTP feature suite | Actual kernel liveness/readiness, no-cache/retry headers, denied probe writes, absent business endpoints, input cannot enable readiness, no session cookie, JSON errors | Passed in the retained private-package replay |
| Pest architecture | Private autoload, reflection confirms service-local source, actual class strict types/finality, no sibling/frontend transport imports | Passed in the retained private-package replay |
| Deptrac | Actual HTTP/provider graph; layer policy includes future Domain/Application and transport separation | Passed in the retained private-package replay |
| Deptrac controls | Four allowed framework/contract parser controls; nine exact forbidden dependency diagnostics; cleanup and restored baseline | Passed in the retained private-package replay |
| Pint / PHPStan | Entire formatted source tree; level 8 application analysis with no baseline suppression | Passed in the retained private-package replay |
| Cached HTTP boot | Configuration and route cache, real HTTP liveness/readiness from the built-in development server | Passed in the retained private-package replay |
| Independent lock replay | Clean installation and platform checks from the captured service-only lock | Passed; lock unchanged and installed versions/references equal |

PHP and Composer were unavailable in the local authoring environment, so these results come from the hosted execution, not local source inspection. The [Governance report](../../verification/p01/packages/run-37239193553/governance/report.json) records 15 successful expected command outcomes and 14 Pest tests / 44 assertions on PHP 8.5.11 and Composer 2.10.3. Cached loopback HTTP returned liveness 200 and readiness 503 with the required bodies and headers. The earlier Pint failure remains in the [package history](p01-laravel-foundations.md).

## Remaining work and limits

The positive/negative analyzer fixtures are temporary synthetic classes. Domain, Application and Infrastructure product behavior is absent; there are no skipped suites claiming that those layers are implemented. This source cannot close the complete pragmatic convention foundation, durable outbox or tenant-isolation criteria by itself.

The [image record](p01-laravel-images.md) supplies a separate independently built Governance image and restricted process measurements. P01 still needs deployed service/dependency behavior, independent service deployment, repository admission controls and the remaining foundation behavior specified by G01. P02 supplies actual identity, tenancy, current authorization, approval and revocation. Retained P00 experiments do not substitute for those service executions. Full native campaigns remain later qualification work and are not prerequisites for independently checking this process foundation.

The [service README](../../services/governance/README.md) gives commands and diagnostics. The [P01 phase](phases/p01.md) and [delivery register](delivery-register.yaml) own overall status; this record does not declare a gate passed.
