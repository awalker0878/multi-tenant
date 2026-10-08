# Developer workflow and code quality

Owner: engineering lead, with each service owner accountable for its implementation. Reviewed: 2026-10-04. Applies to P01.01–P01.04 and every subsequent change. These are project engineering rules; the framework documentation establishes supported mechanisms, while this product's service boundaries and risk determine their use.

Read the [context code structure](../architecture/context-code-structure.md), [code-control policy](code-control.md), [service specifications](../services/README.md), [Laravel conventions](laravel-conventions.md), [testing and CI standard](testing-and-ci.md) and [documentation guide](../documentation-guide.md) together. The existing commands in [CONTRIBUTING](../../CONTRIBUTING.md) validate documentation. Application commands below become usable only after P01 creates and verifies the respective scaffold and configuration.

## Repository ownership and independent builds

Keep the seven deployables independently buildable and owned. One repository makes coordinated changes easier; it does not permit importing another service's application classes or writing its database. The [machine-readable context inventory](../../architecture/context-map.yaml) identifies service/context source roots, layer policy, shared packages and worker ownership. Capability and published-contract semantics remain in their owning specifications; P01 connects implemented artifact identities. Source ownership and permitted dependency edges are checked, reviewed and versioned with the code.

| Boundary | Dependency/build ownership | Review responsibility |
| --- | --- | --- |
| `apps/console/` | Its Composer manifest/lock, frontend package manifest/lock, PHP/Node runtime constraints and image definition | Console owner; consuming API owners for contract changes |
| `services/governance/`, `services/catalogue/`, `services/assurance/` | One Composer manifest/lock and build/test configuration per service; capability code under `app/Domain/` and `app/Application/`, integrations under `app/Infrastructure/`, normal Laravel entrypoints | Owning service; security reviewer for authority, tenancy and evidence controls |
| `services/inventory/`, `services/planning/`, `services/lifecycle/` | One Python project manifest, reproducible locked dependency set and build/test configuration per service; owned package under `src/<service>/` | Owning service; lifecycle/SRE reviewers for execution and recovery changes |
| `workers/` execution packages | Declared owning context, separately buildable image and dependency inventory; no independent authorization policy | Owning service and site/SRE owner |
| `contracts/` and generated clients | Versioned producer-owned schemas; deterministic generator/tool version and declared consumers | Producer and affected consumers |
| Shared technical packages | Explicit owner, published/versioned contract or immutable build input, consumer list and compatibility tests | Package owner and impacted consumers |
| Deployment, workflows and policy configuration | Pinned tools and images, artifact trust, network/identity scope and rollout behavior | Platform/SRE; security for privileged changes |

P01 creates `.github/CODEOWNERS` and verifies the associated repository review/ruleset configuration, covering every boundary, contracts, dependencies, workflow files and the ownership file itself. Follow the [code-control review policy](code-control.md): critical changes require independent role review, and multiple CODEOWNERS entries alone do not enforce approval by every listed owner. Map accountable roles to actual authorized accounts; confirm which ruleset features the repository supports before claiming enforcement. The change author remains responsible for following up with affected owners.

Shared packages may contain observability helpers, contract clients and narrow technical primitives. They must not become a shared tenant model, Eloquent aggregate library or cross-service business layer. Keep the allowed dependency graph acyclic; changes to shared packages trigger all transitive consumers' checks. An independently built service cannot depend on an uncommitted sibling directory or developer-local symlink.

## Working within a bounded context

Start a feature in its owning service and capability. For Laravel, follow [ADR-024](../decisions/adr-024-pragmatic-laravel-domain-convention.md): `App\Domain\<Capability>` contains business behavior, including Eloquent models; `App\Application\<Capability>\Actions` contains use cases with public `handle()`; `App\Infrastructure` contains external adapters. Keep normal Laravel directories for controllers, commands, jobs, listeners, policies, providers, migrations and factories. Python retains `src/<service>/{domain,application,infrastructure,interfaces}` and its existing framework-independent core.

A capability groups behavior within a bounded context. Capabilities with the same owner may collaborate directly; do not manufacture a service or repository boundary between them. A Laravel Action authorizes through the registered policy, invokes model behavior and coordinates persistence/transactions. A small authorized read can remain in a controller. Add Data objects, repositories or domain services when the use case demonstrates a need. A remote service/provider integration uses a versioned contract behind an owned interface and Infrastructure adapter. The console composes APIs; sharing a familiar `App\` prefix never permits importing backend source.

Before creating another context or shared package, update the inventory and explain its data owner, public interface, permitted dependencies, review owner and independent build/release impact. Do not copy domain entities, share Eloquent models or create a catchall shared business package to avoid contract work. The source dependency graph is acyclic; documented event conversations do not imply mutual source imports.

## Dependency and runtime discipline

[ADR-003](../decisions/adr-003-runtime-and-dependency-baseline.md) owns exact runtime/tool selections. Each service records PHP/Python version, required extensions, OS/base image, package manager and development-tool compatibility. Select the frontend package manager and Python locking tool once during P01 and commit their versions and frozen-install behavior; do not maintain competing lock formats for the same application.

For Laravel applications, commit `composer.json` and `composer.lock`; installation in CI and release builds consumes the lock. Resolve an intentional dependency update in a dedicated change, inspect the complete lock diff and rerun affected checks. Composer distinguishes installation from a lock from dependency resolution; its validation command checks manifest/lock consistency [S3].

The project policy additionally requires:

1. Install build tools from owned locks rather than global latest versions. Pin image digests and workflow action revisions. Lock development dependencies as well as runtime dependencies because they execute during builds and tests.
2. Review package ownership, maintenance, license, supported runtimes, transitive dependencies, security advisories and required privileges before adoption. Minimize packages where the framework already solves the need. An abandoned package requires an explicit replacement plan or reviewed exception.
3. Review Composer scripts and allow only the required Composer plugins by name. Do not broadly enable plugins or run dependency installation with production credentials. New install/build scripts are executable supply-chain changes [S4].
4. Validate the actual production image's PHP/extensions using `composer check-platform-reqs --no-dev`. A configured resolver platform is not evidence that the built image has those capabilities. Do not make `--ignore-platform-reqs` part of the supported build path [S3].
5. Audit every application lock and the built OS/container content. An unavailable advisory feed or scanner error is reported as an incomplete check. Restricted environments use a governed advisory/artifact mirror and record its freshness; a failed fetch must not be reported as no vulnerabilities.
6. Keep Composer authentication, registry tokens, environment secrets and credentials outside Git and images. Commit documented environment names and synthetic values only. Use the [configuration/BOM rules](../operations/configuration-and-bom.md) for artifact and configuration identities.

## PHP namespaces, formatting and types

Use Composer PSR-4 autoloading, matching namespace/path case exactly. Check generated autoload metadata on Linux so case-insensitive developer filesystems do not conceal mismatches [S1]. Business names follow the [domain model](../product/domain-model.md); each Laravel service maps its own `App\` namespace to its own `app/` directory. Namespace equality across services is normal and grants no source-sharing permission. Keep bootstrap/configuration and ordinary Laravel entrypoints in their standard paths. Autoloading must not include another service or an unclassified shared business directory.

Use **Laravel Pint with the `laravel` preset** as the single formatter policy for first-party PHP. P01 commits the Pint configuration and compatible tool version in each applicable lock; any common configuration must be a reproducible build input. CI uses check mode, and deliberate formatter upgrades are isolated from behavior changes. Do not run conflicting PHP formatters or mix presets by contributor preference [S2].

PHP-FIG's current PER Coding Style 3.1 expands and replaces PSR-12. It is the reference for reviewing modern PHP style, but this project chooses Laravel's preset and does not claim full PER conformance. If a published library later needs strict PER conformance, record its distinct package policy and verify the pinned tool's exact rules before claiming it [S1, S2].

First-party application PHP uses parameter, return and property types; document collection element types and array shapes where native types cannot express them. Validate external contract data and narrow `mixed` values before use. Use a Data object when structured input improves the contract; scalar inputs and ordinary local model operations do not require wrappers. New source files use `declare(strict_types=1)` where compatible with the reviewed conventions; this is a project choice, not a statement that Laravel requires it. Strict typing does not validate HTTP input or replace authorization.

P01 configures PHPStan with a Laravel-compatible Larastan release, records an explicit rule level, and demonstrates analysis of application code and tests. Select the strongest level supported by the scaffold and correct type annotations; a lower starting level requires the engineering lead's rationale and a tracked increase target. Larastan may boot the application to understand framework types, so analysis must receive only isolated configuration and must not contact privileged environments [S5].

New first-party code starts without a suppression baseline. Prefer accurate generics, boundary validation and narrow dependency stubs over weakening types. A tool upgrade may require a time-bounded baseline for a demonstrated tooling limitation; record the affected rule/files, issue, owner and expiry. Keep unmatched-ignore reporting enabled, fail unreviewed baseline growth, and remove resolved entries. Do not blanket-ignore an application directory or regenerate a baseline simply to turn CI green. PHPStan supports incremental levels and baselines; these restrictions are this project's policy for a new codebase [S6].

Dependency analysis is a separate required check. P01 pins Deptrac for each Laravel application's dependency graph, Pest architecture checks for its adopted convention, Import Linter for Python package rules and the selected ESLint boundary configuration for the console; supplemental PHPStan/reflection rules cover explicit gaps. Prove those configurations with legal and violating fixtures, including aliases and unknown source roots. The current architecture validator is a limited structural check; passing it does not establish full application analysis. See [code control](code-control.md).

Python services apply the same typed-boundary and exception principles using the formatter, linter and static checker selected in ADR-003. The console enables TypeScript strict checking and uses one pinned formatting/lint configuration. Generated clients are regenerated reproducibly and checked for drift; hand edits do not become the source of truth.

## A normal implementation change

1. Identify the user outcome, owning context/capability, requirement IDs, package and affected contracts. Update the inventory when ownership, source roots or dependencies change. Confirm the prerequisite decisions and accepted support scope.
2. Describe the behavior and failure boundary before implementation. Name authorization, tenancy, concurrency, retry and recovery cases relevant to this change; do not mechanically add unrelated tests.
3. Implement a coherent slice with its contract, migrations, meaningful tests and documentation. Keep dependency resolution and broad formatting changes separately reviewable when possible.
4. Run the owning service's boundary/quality/behavior checks and every affected consumer check. Compute impact from both the base and proposed inventory so deleted edges do not hide consumers. Review the [change-to-check matrix](testing-and-ci.md) for cross-service and full-suite triggers. Do not suppress a failing test by replacing the behavior under test with a fake.
5. Record verification actually performed: revision, environment, command/job, result and limits. Attach immutable authorized evidence references when the work meets a qualification criterion.
6. Obtain the owning review and required independent security/contract/operations review against the current revision. Merge only after the required aggregate check passes, material blocking findings are resolved and applicable exceptions are valid. Publish branch changes through the GitHub connector in this work environment; protected-branch admission follows the verified repository policy.

The pull-request description explains the problem and resulting behavior, then lists requirement/package/ADR IDs, compatibility and migration impact, checks performed, qualification impact and remaining dependencies. Include rollback constraints when data or native effects change. Update the service specification and runbook in the same change when they describe changed behavior.

## Local verification after the scaffold exists

The following is the intended baseline for **one Laravel service directory**, after P01 creates its manifest, lock, application and analyzer/test configuration. These commands are not available in the current documentation-only tree. Pin their tool versions and demonstrate them in P01 before copying them into onboarding instructions:

```sh
composer validate --strict
composer install --no-interaction --prefer-dist
composer audit --locked
composer dump-autoload --optimize --strict-psr
./vendor/bin/pint --test
./vendor/bin/phpstan analyse --no-progress
./vendor/bin/pest tests/Architecture
php artisan test
```

The supported manifest supplies the metadata needed for strict validation. The install command can execute approved scripts/plugins; it is used only in a prepared isolated development/CI environment. `php artisan test` does not by itself prove real queue, identity, browser or cross-service integration: those jobs have their own fixtures and entrypoints under the [testing standard](testing-and-ci.md).

P01 adds the pinned language-boundary commands and publishes equivalent verified commands for Python checks, frontend typecheck/build/component tests, contract generation, real-dependency integration and browser tests. Do not infer an architecture pass from `phpstan` or `artisan test` unless the required boundary configuration actually ran and its result is reported. Document required service startup, isolated credentials, data reset and cleanup before describing any one-command workflow. A developer must be able to reproduce a failing check from a clean checkout with no access to production.

## Exceptions and maintenance

An exception records its rule, exact scope, rationale, risk, compensating control, accountable owner, reviewer, expiry and removal work item. Material security or support claims cannot be waived by a formatter/static-analysis exception. An expired exception fails the affected gate; a renewed exception needs fresh review. Keep the record beside the owning service's engineering configuration or in an ADR for cross-cutting decisions, and link it from the change.

Revisit tool compatibility on dependency upgrades and before a framework support deadline; pin a tested tuple instead of silently adopting the latest major. Keep review ownership, dependency/contract consumer maps, setup instructions and required checks current as services are added. A runtime or topology change updates ADR-003 and the relevant decision before widening the supported tuple.

## Primary references

Reviewed 2026-10-04. These references support the mechanisms and standards above; the repository-specific ownership, gating and exception rules are project decisions.

| Ref | Source | Use here |
| --- | --- | --- |
| S1 | [PHP-FIG PSR-4](https://www.php-fig.org/psr/psr-4/) and [PER Coding Style 3.1](https://www.php-fig.org/per/coding-style/) | Autoload interoperability; modern style reference |
| S2 | [Laravel 13 Pint](https://laravel.com/docs/13.x/pint) | Configurable preset and non-mutating style check |
| S3 | [Composer basic usage](https://getcomposer.org/doc/01-basic-usage.md) and [CLI commands](https://getcomposer.org/doc/03-cli.md) | Locks, validate, audit, autoload and platform verification |
| S4 | [Composer configuration](https://getcomposer.org/doc/06-config.md) | Plugin allow-list and dependency security configuration |
| S5 | [Larastan maintained repository](https://github.com/larastan/larastan) | Framework-aware analysis and compatibility prerequisites |
| S6 | [PHPStan levels](https://phpstan.org/user-guide/rule-levels) and [baseline](https://phpstan.org/user-guide/baseline) | Explicit analysis level and controlled suppression handling |
