# Service specifications

Apply the common [engineering standards](../engineering/README.md) with each service specification. Laravel conventions govern console, governance, catalogue and assurance; cross-language contracts, isolation, delivery and evidence rules apply to Python contexts and worker pools as well. Service owners document applicable [controls](../engineering/coverage.md), local performance/retention limits and reviewed exceptions rather than inventing independent conventions.

Status: product behavior and contracts below remain E0 design material. All seven application roots and Inventory/Lifecycle worker roots now contain private P01 foundations. Their local READMEs describe implemented diagnostics; the [complete package replay](../implementation/p01-laravel-foundations.md), [Python foundations](../implementation/p01-python-foundations.md) and [image records](../implementation/p01-laravel-images.md) bind actual execution evidence. Product routes and schemas in these specifications remain proposals until their owning work packages implement and verify them. Publish machine-readable contracts before implementing consumers.

The [target architecture](../architecture/target-architecture.md) defines context boundaries. The [domain model](../product/domain-model.md) defines shared vocabulary; service pages specify the owner, behavior and failure boundaries. The [worked application](../product/application-walkthrough.md) connects them into one proposed journey.

## Service map

| Service | Runtime / repository destination | Owns | First useful delivery |
| --- | --- | --- | --- |
| [Console](console.md) | Laravel/Inertia/Vue; `apps/console/` | Browser sessions and presentation | P02.05; P03.04 |
| [Governance](governance.md) | Laravel/PHP; `services/governance/` | Tenant authority, delegated grants and exact-plan approvals | P02.01–P02.04 |
| [Catalogue](catalogue.md) | Laravel/PHP; `services/catalogue/` | Applications and immutable requested intent | P03.01–P03.05 |
| [Inventory](inventory.md) | Python; `services/inventory/` | Registered endpoints and sourced native observations | P04.01–P04.05 |
| [Planning](planning.md) | Python; `services/planning/` | Capability profiles, assessments and immutable plans | P05.01–P05.06 |
| [Lifecycle](lifecycle.md) | Python/Temporal; `services/lifecycle/` | Admission, native-operation authority, journals and managed bindings | P06.01–P06.03; P07–P09 |
| [Assurance](assurance.md) | Laravel/PHP; `services/assurance/` | Evidence custody and scoped qualification decisions | P06.04; P07.06; P10–P11 |

Workers are separately deployed execution pools attached to their owning context. They do not become independent owners of jobs, grants, approvals or evidence policy. Shared-service integration workers operate under lifecycle authority; discovery workers report to inventory.

## Rules shared by every specification

1. A service writes only its own database. Cross-context validation uses authenticated APIs and pinned records; disposable event projections are not current authorization or native truth.
2. Routes below are relative to the owning service origin. `/v1/tenants/{tenant_id}` selects a tenant; authenticated claims and current grants determine whether that tenant and action are allowed.
3. User delegation and service identity are both verified. A console request does not bypass checks in the receiving service; service credentials alone do not confer arbitrary tenant authority.
4. Versioned immutable resources are never edited in place. Mutable pointers/configuration require concurrency controls. Deletion preserves active references, audit and required retention.
5. Domain mutation, retry record and outbox entry commit atomically. Consumers persist deduplication and their local effects together. A broker outage can delay propagation; it cannot silently discard committed facts.
6. Logical jobs, native operations and discovery/assessment tasks have distinct identifiers and owners. A background assessment is not authorization to run an infrastructure workflow.
7. No service interprets a timeout as proof that an external mutation failed. Unknown outcomes are explicit and reconciled by the effect owner.

See [contract conventions](../contracts/README.md) and [illustrative exchanges](../contracts/examples.md). Per-service names and payloads remain proposals until P01.03 contract review; route examples are not generated client documentation.

## Bootstrap and first service slice

P01 has started the independent application boundaries with diagnostic health entrypoints. Laravel liveness reports process health and readiness returns HTTP 503; Python packages are one-shot diagnostics whose readiness exits nonzero. They do not connect to service dependencies or perform native operations. Synthetic integration fixtures and persistent runtime readiness remain P01.02/P01.05 work. P02 establishes an approved identity provider, service identities and the initial governance administrator; that administrator creates tenant `t_demo` and grants in the isolated fixture environment. Catalogue then creates its tenant-scoped environments, WSDs and logical domains before accepting an application intent referencing them.

Catalogue is the first complete product slice, not an authorization island. P03 can develop against the locked governance contract with explicit test doubles, but its integrated acceptance requires real governance and identity services. Test fixtures never become a production default administrator, implicit tenant or bypass flag.

## How these specifications evolve

Each service page records purpose, excluded responsibilities, aggregates, contracts, identity rules, consistency, dependencies, operations and verification. Extend that page when behavior changes; do not copy architecture rules into unrelated phase notes. Add a focused subordinate document only when an algorithm, state machine or runbook needs its own lifecycle, and link it from the owning service.

Keep schema definitions under `contracts/` once they exist; these human-readable pages explain their meaning. A proposed route is promoted to a locked contract only after owner review, examples and cross-language compatibility checks. Record breaking changes in an ADR and compatibility plan before changing the contract major version.

Every implementation PR links the relevant requirement, phase package, changed contract and evidence. Use the [status model](../implementation/status-model.md) and [gate register](../implementation/gates.md) to report delivery and verification separately; editing this page never advances qualification.

First review dependencies: ADR-004/006/009/012/013; P00.02/P00.03/P00.06 and P01.03. Later service decisions retain their own deadlines in the decision register.
