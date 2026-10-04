# Laravel enterprise practices research and documentation assessment

Reviewed: 2026-10-04. Owner: Engineering lead. Baseline examined: `greenfield/enterprise-microservices-plan` at `717925b0dae05c32248e5a15a27d4dbf337d5179`, containing 121 Markdown documents and the documentation tooling/register. This review concerns the proposed implementation and documentation, not a running codebase audit.

## Assessment

The existing documents cover service ownership, immutable plans, tenant authority, native-effect uncertainty, qualification, recovery and release scope in depth. They did not yet give developers a consistent Laravel implementation standard, sufficiently specific frontend rules or a complete framework-to-test mapping. The scale concern is therefore consistency across independently deployed PHP/Python contexts and teams, rather than a need to add more services or prescribe a large custom framework.

The review adds [engineering standards](../engineering/README.md) and [24 mapped controls](../engineering/coverage.md), then integrates them into existing architecture, service, phase, campaign, deployment and contribution documents. Source-backed framework facts are distinguished from project choices. The existing seven-service architecture, language ownership and evidence-based completion model remain authoritative.

## How the supplied article is used

The [Strapi article](https://strapi.io/blog/laravel-best-practices) is a useful topic checklist: formatting, input handling, authorization, caching, query efficiency, tests, migrations and dependency maintenance. Its examples require adaptation to this product. It is a secondary source, so implementation rules below are grounded in primary documentation and explicit project design decisions.

| Advice requiring interpretation | Project treatment and primary basis |
| --- | --- |
| Put business logic in large models | Place business transitions on capability-owned Eloquent models where they belong; coordinate authorization and persistence in Application Actions. Avoid giant models and mandatory parallel persistence mappings. The user-selected [Laravel convention](../engineering/laravel-conventions.md) governs placement within each service. |
| Validation examples allow every caller | Validation, authenticated tenant context, field permissions and resource authorization are separate checks. Follow Laravel validation/authorization and the [security standard](../engineering/security-and-tenancy.md). |
| Administrator authorization bypass | Tenant and privileged support access remain explicitly scoped, time-bound and audited. No universal bypass; preserve the existing governance model. |
| URL forcing as HTTPS enforcement | Enforce transport at approved ingress, restrict trusted proxies/hosts and test cookie/redirect behavior. Correct generated URLs alone do not block plaintext traffic. |
| Older CSRF middleware examples | Follow the selected Laravel 13 request-forgery mechanism and real browser/session tests; do not transplant older middleware assumptions. |
| Generic query caching | Partition by tenant and authorized view, handle invalidation, and exclude stale authority decisions. See [data and messaging](../engineering/data-and-messaging.md). |
| Every migration has a simple reverse operation | Use expand/contract and controlled backfills. Rollback safety depends on data changes and running readers/workers; a `down` method is not a recovery guarantee. |
| Public CDN, CMS and backup packages | Add only for a demonstrated requirement and approved custody/network boundary. None is a required dependency merely because it appears in a general guide. |
| Minimal example CI | Extend to dependency-aware service checks, static analysis, real transaction tests, browser/security checks and artifact trust. |

## Primary-source findings that change implementation detail

1. **Framework support is a versioned constraint.** Laravel 13 lists PHP 8.3–8.5 and security support through March 17, 2028. That establishes candidate compatibility, not proof that all chosen packages, extensions and base images work together. ADR-003 still requires an exact bill of materials and compatibility spike. [Laravel release policy](https://laravel.com/framework/docs/13.x/releases).
2. **Formatting and interoperability are distinct.** PSR-4 defines autoloading. PHP-FIG's PER Coding Style evolves style guidance. This project selects one pinned Pint `laravel` preset and does not describe that choice as complete PER conformance. [PSR-4](https://www.php-fig.org/psr/psr-4/), [PER](https://www.php-fig.org/per/coding-style/), [Pint](https://laravel.com/framework/docs/13.x/pint).
3. **Framework conveniences do not replace durability.** After-commit dispatch controls transaction timing; durable cross-service event delivery still needs the existing outbox/inbox design. Queue uniqueness or overlap locks do not prove exactly-once external effects. Driver-specific timeouts, redelivery and lost acknowledgements need tests. [Laravel queues](https://laravel.com/framework/docs/13.x/queues), [data standard](../engineering/data-and-messaging.md).
4. **Long-lived workers change the isolation risk.** Request/job-scoped container bindings are available, but mutable singleton/static state and manually managed loops can still leak tenant context. Treat alternating tenants and failed jobs as an explicit test obligation. [Container lifecycles](https://laravel.com/framework/docs/13.x/container), [Octane](https://laravel.com/framework/docs/13.x/octane).
5. **Frontend correctness needs its own verification.** Inertia props and browser history are data surfaces; generated TypeScript is not runtime authorization. A production asset build does not replace type checking, browser coverage or accessibility review. [Frontend standard and primary sources](../engineering/frontend.md).
6. **Framework defaults are not enterprise acceptance criteria.** Application boot health, test fakes, successful migrations and a written runbook each prove a limited fact. Readiness, migration completion, restore correctness and safe authority need independent observations. [Deployment](https://laravel.com/framework/docs/13.x/deployment), [testing](https://laravel.com/framework/docs/13.x/testing), [migrations](https://laravel.com/framework/docs/13.x/migrations).

## Standards and scope

| Authority | Use in this repository | Claim boundary |
| --- | --- | --- |
| Official Laravel 13 documentation | Supported APIs and framework lifecycle; concrete HTTP, persistence, queue and deployment rules | API availability is not a successful deployment |
| PHP-FIG PSR-4 and PER Coding Style | Namespace/autoload interoperability and current coding-style reference | The selected Pint preset is stated explicitly |
| OWASP ASVS and relevant cheat sheets | Versioned application-security verification and implementation guidance | Threat review selects applicability; no blanket certification or authorization-to-operate claim |
| Official Inertia, Vue, TypeScript, Tailwind and Vite documentation | Framework-compatible frontend and build/browser constraints | Exact packages and managed browsers require P00/P01 proof |
| W3C WCAG 2.2 | AA engineering target for operator journeys | Actual conformance requires scoped testing and review |
| NIST SSDF and SLSA | Secure development and provenance control references | Select applicable practices; do not claim maturity or a SLSA level from documentation alone |

The detailed engineering pages cite the primary pages used for each topic. These are living upstream references, not immutable dependency pins. Revisit them on major upgrades; preserve source/lock/image identities in real compatibility and release records. A newer draft standard or article update does not automatically change the accepted delivery baseline.

## Coverage conclusion and follow-through

The user subsequently selected the [pragmatic Laravel DDD article](https://dev.to/maiobarbero/pragmatic-domain-driven-design-in-laravel-with-laravel-boost-3bcm) and its [author-maintained package](https://github.com/maiobarbero/laravel-boost-ddd). [ADR-024](../decisions/adr-024-pragmatic-laravel-domain-convention.md) replaces ADR-023's framework-independent PHP proposal. The [context code structure](../architecture/context-code-structure.md) now applies that convention inside independent Laravel services, retaining the [code-control policy](../engineering/code-control.md), service-private data and machine-readable ownership map. Capability folders are not automatically bounded contexts. This is an explicit project choice; it is not a claim that Laravel mandates this structure.

The documentation now defines a coherent enterprise Laravel baseline with owners, implementation packages and specific verification obligations for architecture, security, frontend, persistence, messaging, quality and operations. This is documentary coverage: the corresponding runtime controls and tests must still be built and demonstrated.

Before scaffolding, P00 must resolve compatible tooling, identity/session choices, approved deployment dependencies and operating/security applicability. P01 then implements the common engineering foundation. P02/P03 must prove it against real tenant and catalogue behavior. The [coverage map](../engineering/coverage.md) supplies the review route through later scale, security, recovery and pilot gates.

Do not infer completed security, code quality, accessibility or performance from this assessment. Future reviews should inspect actual code and evidence against the same mapped controls, record concrete failures, and update the affected canonical document rather than adding disconnected advice.

## Preferred convention review

Reviewed on 2026-10-04 against the author's repository README, core guidance and architecture-test stub. The selected convention is binding through ADR-024. The user explicitly requests only the convention, so the repository is a reference source; no Laravel Boost DDD or Boost installation is included in this plan.

Project-owned architecture tests must be included in the normal Laravel test suite. The reference stub helps identify rules to cover, but does not replace positive and negative fixtures for this repository's service ownership, Composer boundaries and registered source roots. Version compatibility for the project's formatter, analyzer and test tools remains part of P00/P01.

Project additions cover tenant and actor isolation across entrypoints, durable outbox/inbox recovery, independently built services, protected source ownership and native qualification. The [coverage map](../engineering/coverage.md) retains all 24 controls and their phase/gate obligations. An architecture-test pass covers only its assertions; skipped namespaces and dynamic lookups require explicit accounting.
