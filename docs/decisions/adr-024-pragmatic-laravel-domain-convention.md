# ADR-024 — Pragmatic Laravel domain convention

Owner role: Architecture and engineering leads. Related phases: P00, P01, P02, P03, P10. Record date: 2026-10-04.

Origin: `DIRECTED`. Disposition: `ACCEPTED` for the user's explicit choice of the [pragmatic Laravel DDD convention](https://dev.to/maiobarbero/pragmatic-domain-driven-design-in-laravel-with-laravel-boost-3bcm). This supersedes [ADR-023](adr-023-context-code-boundaries-and-controls.md). Acceptance fixes the Laravel convention; it does not approve unresolved service boundaries, dependency versions, repository settings or completed implementation.

## Context and decision

The preceding design translated the requirement for contexts and microservices into a framework-independent PHP core and a second persistence model. The user chose a Laravel-native convention instead. Business ownership and deployment independence remain necessary, but do not require that additional mapping inside every service.

Apply the chosen convention independently in Governance, Catalogue, Assurance and the console. Each application maps its own `App\` namespace to its own `app/` directory. A capability such as Catalogue's IntentRevisions is part of its owning context, not a separately deployed service. The [source structure](../architecture/context-code-structure.md) defines the project-specific locations and examples; [Laravel conventions](../engineering/laravel-conventions.md) defines everyday implementation rules.

Catalogue may keep its owned Eloquent intent model and revision invariants in Domain, and implement an authorized revision Action using the service's local transaction. It does not require an additional record mapper or repository solely to hide Eloquent. A remote Governance permission gateway is a real integration boundary and therefore has a consumer-owned contract and an Infrastructure implementation. Service-private database access remains mandatory in both cases.

Retain the machine-readable [context map](../../architecture/context-map.yaml), independent locks/images, schema-owned public contracts, worker ownership, dependency checks and [code-review controls](../engineering/code-control.md) introduced with ADR-023. Repeated `App\` names are resolved within their owning Composer application; they never authorize one service to autoload another service's source. Python and frontend source conventions retain their own documented checks rather than mechanically adopting PHP directories.

## Alternatives and consequences

| Choice | Consequence for this product |
| --- | --- |
| Framework-independent PHP core with duplicate persistence records | Superseded; would add mappings and interfaces to every Catalogue revision and Governance grant before demonstrating a need |
| User-selected pragmatic Laravel convention with explicit service controls | Accepted convention; developers can use the framework while tenancy, authorization, transactions and public contracts remain testable responsibilities |
| One shared Laravel application or shared business model package | Rejected as an implication of this change; would undermine independent ownership and builds |
| Add the author's development package | Outside scope: the user explicitly selected the convention only |

The [author's repository](https://github.com/maiobarbero/laravel-boost-ddd) supplies the reference convention and examples. The user explicitly declined adding the program. No Laravel Boost DDD or Boost dependency, installation step or package-adoption work is part of this decision. Maintain the project's own architecture checks and tests, with the framework tools selected through the normal compatibility process.

## Delivery and verification

P00.02 reconciles capability ownership and source/contract boundaries; P00.03 verifies the exact framework and project-owned analysis/test toolchain. P01.01 scaffolds independent Laravel applications, registers architecture tests in the normal test command and demonstrates both allowed and prohibited dependencies. P01.04 establishes actual required checks and review owners; P10.06 verifies their continued operation and any exceptions.

Positive fixtures must admit an owned Eloquent model, an Action using Laravel authorization and a local transaction, a simple authorized scoped read, normal entrypoints and two independently built services with their own `App\` namespace. Negative fixtures must reject Domain-to-Application/Infrastructure/delivery references, Application-to-Infrastructure/delivery references, sibling-source autoload exposure and unregistered shared dependencies. Full PHP analysis must cover aliases, attributes, inheritance and container wiring as far as supported, with documented residual review obligations.

Behavioral proof remains separate: wrong-tenant and wrong-actor denial, immutable revision rules, concurrency conflicts, rollback and durable outbox recovery. P02/P03 bind those tests to actual Governance/Catalogue behavior. An architecture test cannot establish authorization or durability, and a skipped suite for absent application code cannot close G01.

Affected delivery requirements: R01, R02 and R35 through the [delivery register](../implementation/delivery-register.yaml). Source schemas and wire contracts do not change solely because PHP classes move. Execution status and evidence remain unchanged until real implementation and review occur.

## Revisit conditions

A change to the user-selected convention needs explicit user direction. A new capability, shared utility or adapter can use the documented review process without reopening the convention. New service boundaries, build inputs, dependencies or analyzer exceptions require coordinated registry, specification and fixture changes. Reassess tooling on framework/package upgrades; do not silently weaken architecture or behavior tests to accommodate generated code.
