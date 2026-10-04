# Enterprise Workload Mobility and Secure Hosting

An enterprise application for planning and operating multi-tenant hosting across **VMware, Nutanix and OpenStack**. It brings application requirements, infrastructure discovery, placement assessment, approvals, provisioning, migration and recovery into one governed operator experience.

**Current state:** the accountable reviewer has [approved G00 advancement](docs/qualification/gate-reviews/g00-user-decision-2026-10-04.md), and P01 delivery/runtime foundation work is underway toward G01. All seven principal application boundaries and both selected worker packages now have owned source and dependency manifests. The [complete package replay](docs/implementation/p01-laravel-foundations.md) passed all nine components. The [image record](docs/implementation/p01-laravel-images.md) retains eight passing images and the successful corrective Console image run alongside its earlier failure. Next is the P01.02 isolated installation topology; independent deployment and the remaining G01 criteria are still open. P00 retains measured Laravel/browser, Python, image, contract and PostgreSQL/attachment recovery evidence. Complete application-fixture coverage is carried into P01. Product journeys and native platform qualifications remain unimplemented/unrun; the capabilities below describe the intended product.

## What the application does

An application owner describes what an application needs: its workloads, data, dependencies, compute and storage requirements, security boundaries, shared services and recovery objectives. The platform discovers approved infrastructure, explains which destinations satisfy those requirements and produces a versioned execution plan. Authorized operators review and approve that exact plan before scoped workers perform the work at the relevant sites.

| User task | Intended result |
| --- | --- |
| Register an application | A tenant-owned catalogue of workloads, datasets, dependencies, owners and revisioned intent |
| Discover infrastructure | Current observations of approved sites, platforms, resources and capacity, with clear freshness and completeness |
| Assess a destination | An explained comparison of eligible, conditional, unsupported and unknown capabilities |
| Plan a change | An immutable proposal describing resource mappings, security policy, service dependencies, effects, downtime and recovery boundaries |
| Review and approve | Attributable decisions bound to the exact plan, scope and permitted execution window |
| Provision or migrate | Durable execution through narrowly authorized workers, with progress, native observations and explicit handling of uncertain outcomes |
| Recover, change or retire | Controlled day-two operations that preserve resource ownership, data integrity and retained evidence |
| Review assurance | Evidence showing what was requested, approved, attempted and observed, and which precise platform combinations are supported |

Portability means expressing application requirements independently of one platform and evaluating their actual realization on each destination. It does not promise identical features, topology or migration methods everywhere. Unsupported requirements remain visible and block operations that depend on them.

## Who uses it

| User | Main responsibility |
| --- | --- |
| Application owner | Describe the application, its dependencies and acceptance/recovery requirements |
| Tenant administrator | Manage tenant membership, delegated permissions, entitlements and scope |
| Planner / operator | Discover infrastructure, assess destinations, prepare plans and manage authorized jobs |
| Approver | Review risk, scope, timing and separation-of-duties requirements |
| Platform / service operator | Commission sites and integrations, maintain availability and handle recovery |
| Auditor / assurance reviewer | Examine provenance, qualification, access decisions and operating acceptance |

The console should make each task understandable through clear requirements, differences, blockers and recovery choices. Credentials, provider APIs, Terraform state and data-transfer mechanics remain behind the relevant service and worker boundaries.

## How it is organized

The implementation separates Laravel/PHP product services from Python infrastructure intelligence and execution. The console uses **Laravel 13, Inertia 3, Vue 3, TypeScript, Tailwind CSS 4 and Vite 8**. Exact candidate pins and image inputs are recorded in the P00 compatibility reports; operated adoption and complete service dependencies remain open; the [source checks](docs/reference/sources-and-reset.md) record the candidate baseline.

| Area | Responsibility |
| --- | --- |
| Laravel console | Browser sessions, navigation, forms, plan review, job status and evidence views |
| Governance and catalogue | Tenant access, approvals, application identity and desired intent |
| Inventory and planning | Observations, capability matching, policy evaluation, placement and immutable plans |
| Lifecycle and Temporal | Admission, durable workflows, execution authority, operation journaling and reconciliation |
| Assurance | Evidence custody, qualification decisions and supported-capability views |
| Site workers and adapters | Scoped discovery, infrastructure changes, guest configuration, service integration and data movement |

Services own their data and communicate through versioned APIs and events. Central services are proposed for Kubernetes within approved trust boundaries; workers run near their authorized endpoints. Application data moves directly between approved source and target paths. See the [service catalogue](docs/services/README.md), [architecture](docs/architecture/target-architecture.md) and [deployment model](docs/operations/deployment-model.md).

Each business context owns its service, data and rules. Inside each Laravel application, capabilities use the pragmatic domain convention selected in [ADR-024](docs/decisions/adr-024-pragmatic-laravel-domain-convention.md):

| Location within each Laravel application | Responsibility |
| --- | --- |
| `app/Domain/<Capability>/` | Business behavior and invariants, including Eloquent models |
| `app/Application/<Capability>/Actions/` | Use cases with a `handle()` entrypoint, authorization and local transaction orchestration |
| `app/Infrastructure/` | External clients and adapters for real integration boundaries |
| Normal Laravel directories | Controllers, requests, jobs, listeners, policies, providers, migrations and factories |

Each independently built Laravel service owns its own `App\` namespace. Capabilities within one context can collaborate directly; direct Eloquent access is the default, and repositories or DTOs need a concrete reason. Python services retain their own domain/application/infrastructure/interfaces structure. Across service boundaries, internal models and use cases remain private and integration uses versioned contracts. The [context registry](architecture/context-map.yaml), [source structure](docs/architecture/context-code-structure.md) and [code-control policy](docs/engineering/code-control.md) define ownership, dependency checks and required review. The [foundation checks](scripts/p01/README.md) select affected private packages and dependent workers. Repository review enforcement and the remaining integration checks are P01 deliverables.

## First release and delivery milestones

The approved initial direction first provisions a selected Linux application on OpenStack, then migrates a VMware deployment by **rebuilding the application on OpenStack and restoring its application-consistent data**. The target uses reviewed images, application artifacts and configuration; cutover requires source-writer fencing, verified data and controlled target write admission. The approved direction retains the remaining application/configuration feasibility work at P01/G01. Exact installed tuples, application outage/recovery objectives and native outcomes remain required at their discovery, provisioning and migration checkpoints.

Whole-VM disk capture/conversion is a separate P09 option for applications that cannot be rebuilt, with its own feasibility and qualification. It is never a silent fallback. Historical rebuild/restore code and tests supply design information only; they establish no implementation or support on this branch.

| Milestone | What a user can demonstrate | Phases |
| --- | --- | --- |
| Application workspace | Create a tenant-scoped application and inspect immutable intent revisions | P02–P03 |
| Read-only assessment | Discover the selected infrastructure and compare a destination with explanations | P04–P05 |
| Simulated lifecycle | Review, approve and follow a durable job, including failures and held outcomes | P06 |
| Native provisioning | Provision, verify, protect and retire the selected application | P07 |
| Native migration | Rehearse, cut over and recover the selected VMware-to-OpenStack route | P08 |
| Expanded and operated service | Qualify selected additional combinations, prove resilience and accept a pilot | P09–P11 |

These are future milestones. The [progress view](docs/implementation/progress.md) records actual delivery state; the [support matrix](docs/implementation/support-matrix.md) defines planned scope. Read the [worked application example](docs/product/application-walkthrough.md) to follow one synthetic application through the whole product.

## Where to start

| Your purpose | Read first |
| --- | --- |
| Understand the product | [Product overview](docs/product/README.md) → [worked example](docs/product/application-walkthrough.md) |
| Understand domain and architecture | [Domain model](docs/product/domain-model.md) → [target architecture](docs/architecture/target-architecture.md) → [service specifications](docs/services/README.md) |
| Build consistent Laravel services and UI | [Engineering standards](docs/engineering/README.md) → [coverage and delivery map](docs/engineering/coverage.md) → [research assessment](docs/reference/laravel-practices-review.md) |
| Implement the next increment | [Next work](next_work.md) → [P01](docs/implementation/phases/p01.md) → [contract examples](docs/contracts/examples.md) |
| Plan and track delivery | [Phase plan](docs/implementation/phased-plan.md) → [detailed phase documents](docs/implementation/phases/README.md) → [traceability](docs/implementation/traceability.md) → [gates](docs/implementation/gates.md) |
| Deploy and operate | [Operations index](docs/operations/README.md) → [deployment model](docs/operations/deployment-model.md) |
| Review readiness and support | [Requirements](docs/implementation/requirements-and-qualification.md) → [qualification procedures](docs/qualification/README.md) → [release guidance](docs/releases/README.md) → [progress](docs/implementation/progress.md) |
| Add or change documentation | [Documentation guide](docs/documentation-guide.md) → [templates](docs/templates/README.md) |

The [documentation index](docs/README.md) maps the complete set. Active branch: `greenfield/enterprise-microservices-plan`. The [reset and source record](docs/reference/sources-and-reset.md) explains its relationship to earlier work.

## Baseline evidence

G00 advancement is approved; incomplete baseline checks remain assigned to their receiving checkpoints. The [baseline review](docs/implementation/p00-baseline-review.md) connects the scope/domain findings, historical source assessment, actual compatibility experiments and route/operating requirements. The [Laravel integration](docs/implementation/p00-integration-results.md) now passes 20 tests/200 assertions, quality and boundary controls, clean lock replay and a real Chromium flow. The [Python tooling experiment](docs/implementation/p00-python-tooling-results.md) passes strict typing, behavior tests and intended import-boundary rejections. Compatibility code under `spikes/compatibility/` is an isolated experiment; product behavior and native qualification remain future work. Follow [progress](docs/implementation/progress.md) for evidence and unresolved inputs, and [next work](next_work.md) for the next concrete step.


The [candidate images](docs/implementation/p00-image-results.md) now have immutable upstream inputs, measured OS/extension/package inventories and passing isolated runtime probes. The [contract-tool experiment](docs/implementation/p00-contract-tooling-results.md) validates synthetic wire schemas and reproducible PHP/Python/TypeScript generation, including intentional rejection cases and documented decoder limits. The remaining P00 work is consolidated in the [decision and input review](docs/implementation/p00-decision-and-input-review.md): actual baseline/operating decisions, exact application/platform/lab inputs, bounded rebuild/restore observations and accountable G00 review.


P00 now also has [executed rebuild/restore fixture results](docs/implementation/p00-restore-fixture-results.md), [selected development decisions](docs/implementation/p00-engineering-selections.md), an [executable RT/IP input record](docs/qualification/feasibility/input-record.md) and a [criterion-level G00 engineering assessment](docs/qualification/gate-reviews/g00-engineering-assessment-2026-10-04.md). The restore experiment measures real database/file state and both fixture recovery boundaries; it does not claim a deployed Permit Desk application or VMware/OpenStack qualification. G00 advancement is approved; actual integration/operating inputs and the remaining application/configuration evidence retain their assigned later checkpoints.
