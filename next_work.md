# Next work — P00 baseline and compatibility work

Active branch: `greenfield/enterprise-microservices-plan`. The previous Laravel foundation remains reference material only. The requested `implementation/all-waves` source branch is pinned for this review at `a2963d8d43e25f08d70fbd99b0e5e19ab5c9828e`; current documentation, stack and ADR-024 take precedence. P00 execution has started: scope/domain review, an isolated compatibility attempt and route/operating-baseline review are underway. Product application implementation and native qualification have not started. [Canonical delivery state](docs/implementation/delivery-register.yaml) owns status; [progress](docs/implementation/progress.md) and [traceability](docs/implementation/traceability.md) are generated views.

## Current handoff

The [P00 baseline review](docs/implementation/p00-baseline-review.md) links the completed analytical work and concrete decisions still needed. Scope/persona, domain/ownership and route/operating-measure reviews are prepared. [Compatibility execution](docs/implementation/p00-compatibility-results.md) records successful locked frontend/Python probes and remote PHP lock replay, including the rejected TypeScript 7 candidate. Product services and native feasibility remain unimplemented/unrun.

The current preferred first migration proposal is `application_rebuild_restore` for a reproducible Linux application. Whole-VM conversion is separately scoped to P09. This updates the earlier technical proposal through the current P00 discussion; it does not import the historical runtime or qualification.

| Next work | Concrete action | Completion condition |
| --- | --- | --- |
| P00.03 — independent engineering can continue | Extend the isolated spike from the tested locks to a real Laravel/Inertia HTTP exchange and a selected formatter/static-analysis/Pest/architecture-tool tuple; capture failures and fresh lock replay | Executed, source-bound results with remaining browser/image limits explicit; no product feature or G00 completion claim |
| P00.01/P00.02/P00.05 — baseline decisions | Review the prepared scope/domain/operating recommendations, assign actual accountable owners, and decide retained-state applicability | Recorded scope, cardinality/ownership, workload/targets, retention and now-blocking decisions; BL-P00-001 resolved only for accepted scope |
| P00.03 — operated runtime inputs | Select the production image/runtime family, dependencies, trust/custody and mirror path with operating owners; use measured candidates as evidence | Immutable build inputs and actual build/integration results, with explicit supported browser and network assumptions |
| P00.04 — first-route feasibility | Supply exact VMware/OpenStack facts, reproducible application artifacts, approved consistent-capture/restore fixture and scoped lab authority using the RT/RF matrices | Actual bounded application_rebuild_restore observations; BL-P00-002 remains open until inputs and experiment evidence exist |
| P00.06 — gate review | Bind accepted decisions and remaining experiments to G00.01–G00.06; reconcile staffing and external dates | Accountable gate review with immutable evidence; passing compatibility probes alone cannot close G00 |
| P01 — after affected entry conditions | Implement the six foundation cards against accepted boundaries and proven inputs | Independent service builds, real contract/dependency checks and actual review/release enforcement |

The canonical register records scoped E1 evidence and actual acceptance dependencies. Missing owner/lab inputs do not prevent the independent P00.03 engineering work above. G00 remains unreviewed by accountable owners; native mutation requires its separate authorized campaign.

## Document each implementation increment

Use the [engineering standards](docs/engineering/README.md) and [coverage map](docs/engineering/coverage.md) when refining P00/P01. P00.03 must resolve compatible analysis/test tools and managed-browser requirements alongside framework locks. P01 must implement the documented structure, ownership, static analysis, contract and runtime checks before feature expansion; the written standards are not a completed foundation.

Apply the [pragmatic Laravel convention](docs/decisions/adr-024-pragmatic-laravel-domain-convention.md) within the [owning microservice](docs/architecture/context-code-structure.md): capability-based `app/Domain/` and `app/Application/`, Eloquent model behavior, Actions with `handle()`, external adapters in `app/Infrastructure/`, and normal Laravel entrypoints. Capabilities do not automatically become microservices. P00.02 aligns [the context registry](architecture/context-map.yaml) with that accepted convention and settles the remaining service decisions. P00.03 verifies the chosen architecture-test tooling against the actual dependency locks. P01.01/P01.04 implement PHP/Python/frontend dependency checks and actual ownership/review protection. The current registry/fixture workflow has explicit analysis limits; a source-empty pass does not close those packages.

For every coherent change, identify requirement/package IDs and the owning service. Update its behavior/contract specification and any affected ADR; put future API/event schemas in the contract tree, operational procedures under `docs/operations/runbooks/`, and qualification definitions/evidence indexes under `docs/qualification/`. The [documentation guide](docs/documentation-guide.md) defines the complete placement and naming rules.

Record actual source/artifact revisions, environment, positive/negative/recovery results, evidence identity and reviewer in `delivery-register.yaml`. Add a blocker with owner and unblock condition when necessary. Regenerate the progress/traceability views and validate references. Update this file to name the next concrete task, without copying a second status table here.

Use small coherent commits and the established GitHub connector workflow. No historical passing test, approval, credential, native support claim or operational acceptance transfers from the old programme. Scaffolding and design examples cannot be described as completed product behavior.
