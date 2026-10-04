# Engineering standards

Owner: Engineering lead, with service, security, quality and SRE owners. Reviewed: 2026-10-04.

These standards turn the product architecture into implementation and review rules for the seven principal applications and their worker pools. They apply to new work on this branch. Application enforcement and verification are delivered through the mapped work packages; the repository currently contains design documentation, not a verified Laravel application.

## Choose the right guide

| Guide | Owns |
| --- | --- |
| [Laravel conventions](laravel-conventions.md) | Capability-based Domain/Application code, Eloquent behavior, Actions, normal Laravel entrypoints and external adapters |
| [Context code structure](../architecture/context-code-structure.md) | Service ownership, pragmatic Laravel layout, Python layers and private/public code boundaries |
| [Code controls](code-control.md) | Machine-readable ownership, dependency rules, protected changes, review policy and CI enforcement |
| [Data and messaging](data-and-messaging.md) | Eloquent, tenant persistence, transactions, outbox/inbox, queues, caches and schema evolution |
| [Security and tenancy](security-and-tenancy.md) | Authentication, authorization, tenant context, browser protection and hostile input |
| [Frontend](frontend.md) | Inertia/Vue architecture, safe props, forms, accessible journeys and browser compatibility |
| [Testing and CI](testing-and-ci.md) | Test layers, fault coverage, contract compatibility and automated delivery checks |
| [Developer workflow](developer-workflow.md) | Reproducible setup, dependency changes, ownership and change review |
| [Coverage and delivery mapping](coverage.md) | Each engineering control's owner, work package, gate and required proof |
| [Research assessment](../reference/laravel-practices-review.md) | Sources, assessment of the supplied article and the reasons for these additions |

Deployment procedures remain in [operations](../operations/README.md); API/event semantics remain in [contracts](../contracts/README.md). Do not maintain competing framework instructions in every service document. Service specifications explain their particular models, permissions, dependencies and exceptions to these common rules.

[ADR-024](../decisions/adr-024-pragmatic-laravel-domain-convention.md) selects the Laravel convention. Domain code can use Eloquent while remaining independent of Application and Infrastructure. Application Actions orchestrate use cases through `handle()`; direct Eloquent access and same-context collaboration are normal. Add repositories, DTOs and contracts when they clarify a concrete dependency or behavior. Service-private data, tenant authorization and versioned integration contracts remain mandatory.

## Apply the standards to a change

1. Identify the owning service, package and applicable controls in the coverage map. Confirm current ADR decisions and exact dependency locks.
2. Implement the smallest coherent use case within that service, including its authorization, persistence and failure behavior. Keep provider-specific effects in the authorized worker path.
3. Supply the positive, denied, concurrent and interrupted checks relevant to the change. Review generated clients, migrations, UI behavior and operating impact together.
4. Record actual evidence in the existing delivery register. A formatter result, design review or generated scaffold cannot establish tenant isolation, native support or release readiness.

Rules described here as required are project engineering policy. Laravel features are the mechanisms used to implement them. Suggested class grouping, performance budgets and runtime choices are not claims that Laravel mandates one enterprise architecture. Exact tool versions, security applicability and operating targets close through their existing P00/P01 decisions.

## Exceptions and maintenance

An exception records the affected control, service and release, reason, risk, compensating check, accountable reviewer, expiry/revisit trigger and corrective package. Use the owning design record; use an ADR when a boundary, trust model or material dependency changes. Do not silently add a second formatter policy, bypass type checks, share an Eloquent model across services or suppress a failed security test.

Service owners maintain local conformance. Engineering owns shared conventions; security owns security applicability; quality owns the verification map; SRE owns runtime procedures. Recheck the sources during framework/toolchain upgrades and update affected standards, work packages, tests and runbooks in the same change. [CONTRIBUTING](../../CONTRIBUTING.md) defines the review and documentation commands.
