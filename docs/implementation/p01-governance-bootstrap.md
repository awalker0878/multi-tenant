# P01 Governance Laravel foundation

Date: 2026-10-04. Work package: P01.01. Related checkpoints: G01.01/G01.02; later Governance behavior belongs to P02. This record describes the first real service source and separates authored checks from executed evidence.

## Implemented scope

`services/governance/` is an independent API-only Laravel application with the private `product/governance` package and service-local `App\` namespace. Its `HealthController`, provider, bootstrap, JSON exception rendering, routes, configuration and entrypoints do not include compatibility spike business entities. It includes no Boost program, Inertia frontend, default user, privileged tenant or fallback authorization.

The process answers `/health/live` with `200` and process scope. `/health/ready` always returns `503` with `foundation_only` until real readiness dependencies and authority checks are implemented. Request fields, environment switches and bearer-looking input cannot turn this into an authority service. The endpoints do not access persistence or remote services. Business paths remain absent. Responses suppress exception diagnostics and do not establish browser sessions.

The configuration declares a future service-private PostgreSQL connection without default endpoint, database or credentials and with verified TLS as the default. No connection has been made and no schema, migration, database isolation or tenant guarantee is claimed. Application and cache runtime directories are explicitly present; bootstrap performs no remote calls, migration or directory permission changes.

## Dependency and quality scope

The manifest pins Laravel 13.34.0, Pint 1.32.1, Larastan 3.12.2, PHPStan 2.2.16, Deptrac 4.7.2, Pest 4.7.8, Pest Laravel 4.1.0 and Mockery 1.6.15 on the accepted PHP 8.5 development family. Transitive versions must come from Composer resolution and a captured private lock; they are not manually authored. The initial source commit carries the measured P00 lock unchanged solely as the explicit resolver seed. This seed is not a validated Governance lock and normal lock validation must fail until the service-specific output is retained.

| Check | Authored coverage | Execution status |
| --- | --- | --- |
| HTTP feature suite | Actual kernel liveness/readiness, no-cache/retry headers, denied probe writes, absent business endpoints, input cannot enable readiness, no session cookie, JSON errors | Awaiting hosted execution |
| Pest architecture | Private autoload, reflection confirms service-local source, actual class strict types/finality, no sibling/frontend transport imports | Awaiting hosted execution |
| Deptrac | Actual HTTP/provider graph; layer policy includes future Domain/Application and transport separation | Awaiting hosted execution |
| Deptrac controls | Four allowed framework/contract parser controls; nine exact forbidden dependency diagnostics; cleanup and restored baseline | Awaiting hosted execution |
| Pint / PHPStan | Entire formatted source tree; level 8 application analysis with no baseline suppression | Awaiting hosted execution |
| Cached HTTP boot | Configuration and route cache, real HTTP liveness/readiness from the built-in development server | Awaiting hosted execution |
| Independent lock replay | Clean installation and platform checks from the captured service-only lock | Awaiting initial resolution and retained lock |

PHP and Composer are unavailable in the local authoring environment. The source has not been reported as passing from local inspection; the P01 hosted workflow must produce the actual outputs before this table advances. Failed attempts remain evidence and receive a source correction plus a new run.

## Remaining work and limits

The positive/negative analyzer fixtures are temporary synthetic classes. Domain, Application and Infrastructure product behavior is absent; there are no skipped suites claiming that those layers are implemented. This source cannot close the complete pragmatic convention foundation, durable outbox or tenant-isolation criteria by itself.

P01 still needs independently verified service images and inventories, actual runtime/process isolation, the complete context/build matrix, deployment and repository controls and the implemented foundation behavior specified by G01. P02 supplies actual identity, tenancy, current authorization, approval and revocation. Retained P00 experiments do not substitute for those service executions. Full native campaigns remain later qualification work and are not prerequisites for independently checking this process foundation.

The [service README](../../services/governance/README.md) gives commands and diagnostics. The [P01 phase](phases/p01.md) and [delivery register](delivery-register.yaml) own overall status; this record does not declare a gate passed.
