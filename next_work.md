# Next work — P00 baseline and compatibility work

Active branch: `greenfield/enterprise-microservices-plan`. The previous Laravel foundation remains reference material only. The requested `implementation/all-waves` source branch is pinned for this review at `a2963d8d43e25f08d70fbd99b0e5e19ab5c9828e`; current documentation, stack and ADR-024 take precedence. P00 execution has started: scope/domain review, an isolated compatibility attempt and route/operating-baseline review are underway. Product application implementation and native qualification have not started. [Canonical delivery state](docs/implementation/delivery-register.yaml) owns status; [progress](docs/implementation/progress.md) and [traceability](docs/implementation/traceability.md) are generated views.

## Read and start here

Read the [README](README.md) for the product, [documentation guide](docs/documentation-guide.md) for where future work belongs, [worked application](docs/product/application-walkthrough.md) for the complete journey and [P00 cards](docs/implementation/phases/p00.md) for acceptance-ready tasks. Treat examples as synthetic design examples, not running software.

| Sequence | Concrete action | Required output / unblock condition |
| --- | --- | --- |
| 1 — P00.01 | Review personas, first application/route, mandatory capabilities and release exclusions with accountable roles; determine whether retained operational data exists | Reviewed scope and owner assignments; unresolved owner/input becomes a concrete blocker |
| 2 — P00.02 | Review domain relationships and seven service ownership boundaries against valid/invalid examples; settle sharing, revision and authority semantics | Accepted invariants and now-blocking architecture decisions; one writer per owned state |
| 3 — P00.03, can overlap 1/2 | Execute the isolated compatibility spike, recording exact dependency locks/build results; select initial broker, identity/trust, data/runtime and installation choices | Actual E1 results and accepted NOW decisions; failed compatibility yields an explicit decision, not a silent stack change |
| 4 — P00.04, can overlap 2/3 | Obtain source/target tuple facts and approved fixtures, test initial offline-method feasibility, and design isolated lab authority plus negative/recovery campaigns | Actual bounded feasibility results and reviewed route; unavailable facts/access remain identified dependencies |
| 5 — P00.05 | Ratify measurable scale/SLO/RPO/RTO/application objectives, custody, threat/recovery cases, retention and operating responsibilities | Reviewed targets with methods/owners; provisional values are not service promises |
| 6 — P00.06 | Refine staffing/estimates and all requirement mappings; review the six G00 criteria with actual evidence and independent reviewers | G00 decision registered with evidence/blockers; later ADRs retain their explicit blocking checkpoints |
| 7 — P01 after its entry decisions | Implement the [six foundation cards](docs/implementation/phases/p01.md): independent builds, integration runtime, contracts, supply chain, dependencies and baseline recovery | Each G01 criterion independently demonstrated; no native administrator access required |

P00 decisions do not all have to be final. [The decision register](docs/decisions/decision-register.md) separates NOW choices, provisional baselines and later refinements. Proceed with independent authorized work while a dependency is unresolved; do not bypass the package it actually blocks. Neither a plan nor a documentation review authorizes native mutation.

## Document each implementation increment

Use the [engineering standards](docs/engineering/README.md) and [coverage map](docs/engineering/coverage.md) when refining P00/P01. P00.03 must resolve compatible analysis/test tools and managed-browser requirements alongside framework locks. P01 must implement the documented structure, ownership, static analysis, contract and runtime checks before feature expansion; the written standards are not a completed foundation.

Apply the [pragmatic Laravel convention](docs/decisions/adr-024-pragmatic-laravel-domain-convention.md) within the [owning microservice](docs/architecture/context-code-structure.md): capability-based `app/Domain/` and `app/Application/`, Eloquent model behavior, Actions with `handle()`, external adapters in `app/Infrastructure/`, and normal Laravel entrypoints. Capabilities do not automatically become microservices. P00.02 aligns [the context registry](architecture/context-map.yaml) with that accepted convention and settles the remaining service decisions. P00.03 verifies the chosen architecture-test tooling against the actual dependency locks. P01.01/P01.04 implement PHP/Python/frontend dependency checks and actual ownership/review protection. The current registry/fixture workflow has explicit analysis limits; a source-empty pass does not close those packages.

For every coherent change, identify requirement/package IDs and the owning service. Update its behavior/contract specification and any affected ADR; put future API/event schemas in the contract tree, operational procedures under `docs/operations/runbooks/`, and qualification definitions/evidence indexes under `docs/qualification/`. The [documentation guide](docs/documentation-guide.md) defines the complete placement and naming rules.

Record actual source/artifact revisions, environment, positive/negative/recovery results, evidence identity and reviewer in `delivery-register.yaml`. Add a blocker with owner and unblock condition when necessary. Regenerate the progress/traceability views and validate references. Update this file to name the next concrete task, without copying a second status table here.

Use small coherent commits and the established GitHub connector workflow. No historical passing test, approval, credential, native support claim or operational acceptance transfers from the old programme. Scaffolding and design examples cannot be described as completed product behavior.
