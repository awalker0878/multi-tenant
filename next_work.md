# Next work — P01 delivery and runtime foundation

Active branch: `greenfield/enterprise-microservices-plan`. The requesting user approved advancement from G00 on 2026-10-04. The [accountable decision](docs/qualification/gate-reviews/g00-user-decision-2026-10-04.md) accepts the product, architecture and development baseline and explicitly carries remaining work to its receiving checkpoints. **P01 is the active phase; G01 is the next exit gate.** The [delivery register](docs/implementation/delivery-register.yaml) owns state; [progress](docs/implementation/progress.md) and [traceability](docs/implementation/traceability.md) are generated views.

## Current handoff

Start with the [P01 work packages](docs/implementation/phases/p01.md), [approved development selections](docs/implementation/p00-engineering-selections.md), [decision register](docs/decisions/decision-register.md) and [G01 review](docs/qualification/gate-reviews/g01.md). The first implementation increment creates the Planning service's independently owned Python package and bootstrap. Complete the remaining deployables from the measured P00 inputs, with no dependency on disposable spike code or historical runtime code.

| Work | Next concrete action | Evidence needed before G01 |
| --- | --- | --- |
| P01.01 — Independent applications | Build Console, Governance, Catalogue and Assurance in Laravel, and Inventory, Planning and Lifecycle in Python; add only the selected owned worker packages. Give each its own locks, build and minimal health entrypoints. | Seven principal images and selected workers build from clean inputs; service-only changes and source/contract boundaries are checked. A bootstrap alone does not complete a service. |
| P01.02 — Local/integration installation | Implement isolated Compose and Kubernetes installation with explicit synthetic identities, configuration and dependency health. Incorporate the carried Permit Desk application/configuration fixture and pinned candidate topology. | Empty-environment installation, authenticated health, dependency failures and complete reproducible fixture inventory. |
| P01.03 — Contracts and messaging | Author versioned contracts, validate before generated decoding, then implement service-owned outbox/inbox against real PostgreSQL and broker dependencies. | Cross-language positive/negative fixtures, transactional rollback, duplicate delivery and restart observations. |
| P01.04 — CI and trusted artifacts | Add per-service checks and actual code-review enforcement, then SBOM/provenance/signing and verified promotion using selected registry/trust inputs. | Required-check/review enforcement and rejection of unsigned or altered artifacts. |
| P01.05 — Dependency and identity isolation | Pin and deploy PostgreSQL, Temporal, broker, evidence store and required session/cache components with private roles and controlled migrations. | Cross-service/schema denial, invalid/revoked identity and failed-dependency behavior. |
| P01.06 — Baseline recovery | Restore synthetic service state and evidence, restart services, deliver an alert and recover a failed deployment. Complete carried full-application/configuration recovery coverage. | Actual data/digest equality, restart/alert receipt and recovery observations with native writes disabled. |

The [P00 evidence index](docs/implementation/p00-baseline-review.md) and [G00 engineering examination](docs/qualification/gate-reviews/g00-engineering-assessment-2026-10-04.md) remain historical evidence. Existing PHP/Python, browser, image, contract-tool and PostgreSQL/attachment observations count only for their measured scopes. Reuse unchanged passing mechanisms; add the missing product-source, application and integration checks.

## Carried inputs and checkpoint ownership

The user's reviewer identity, G00 approval, baseline decision scope, migration direction/method and later checkpoints are recorded with immutable provenance in the [input record](docs/qualification/feasibility/input-record.md). Do not request that baseline approval again. Remaining unknown integration and native fields describe actual inputs still needed, not a reason to stop independent foundation work.

- Complete the representative application/configuration fixture and candidate topology in P01.02/P01.06 before G01; retain the two measured PostgreSQL/attachment recovery boundaries.
- Obtain actual runtime, registry/signer, trust, network and dependency facts before the affected P01 integration. Local development artifacts do not establish operated deployment or promotion controls.
- Obtain installed VMware/OpenStack facts and permitted discovery scope before G04 work, and exact campaign effects/authority before G07/G08 native tests. Native qualifications remain unrun.
- Retain application outage/data objectives before P08, operating/retained-state obligations at P10/P11, and staffing/dependency dates when supplied. Approval does not invent these facts.

The original P00 task axes continue to show any carried incomplete work; the accountable G00 advancement decision is recorded separately. No unperformed check becomes a pass. Whole-VM conversion stays a separate P09 option; the approved first migration direction uses `application_rebuild_restore`.

Historical `implementation/all-waves` source is pinned at `a2963d8d43e25f08d70fbd99b0e5e19ab5c9828e` for reference. Current documentation, stack and ADR-024 take precedence; no historical implementation, passing result or authority transfers.

## Document each implementation increment

Use the [engineering standards](docs/engineering/README.md) and [coverage map](docs/engineering/coverage.md) when refining P00/P01. P00.03 has measured framework/tool locks, candidate image builds and schema/client tooling. Production adoption, complete service dependencies, managed-browser requirements and the actual mirror/trust path still need operating decisions and evidence. P01 must implement the documented structure, ownership, static analysis, contract and runtime checks before feature expansion; the written standards are not a completed foundation.

Apply the [pragmatic Laravel convention](docs/decisions/adr-024-pragmatic-laravel-domain-convention.md) within the [owning microservice](docs/architecture/context-code-structure.md): capability-based `app/Domain/` and `app/Application/`, Eloquent model behavior, Actions with `handle()`, external adapters in `app/Infrastructure/`, and normal Laravel entrypoints. Capabilities do not automatically become microservices. P00.02 aligns [the context registry](architecture/context-map.yaml) with that accepted convention and settles the remaining service decisions. P00.03 has verified the candidate architecture tools against actual spike locks and intentional violations; P01 must map these rules to the complete registered product source. P01.01/P01.04 implement PHP/Python/frontend dependency checks and actual ownership/review protection. The current registry/fixture workflow has explicit analysis limits; a source-empty pass does not close those packages.

For every coherent change, identify requirement/package IDs and the owning service. Update its behavior/contract specification and any affected ADR; put future API/event schemas in the contract tree, operational procedures under `docs/operations/runbooks/`, and qualification definitions/evidence indexes under `docs/qualification/`. The [documentation guide](docs/documentation-guide.md) defines the complete placement and naming rules.

Record actual source/artifact revisions, environment, positive/negative/recovery results, evidence identity and reviewer in `delivery-register.yaml`. Add a blocker with owner and unblock condition when necessary. Regenerate the progress/traceability views and validate references. Update this file to name the next concrete task, without copying a second status table here.

Use small coherent commits and the established GitHub connector workflow. No historical passing test, approval, credential, native support claim or operational acceptance transfers from the old programme. Scaffolding and design examples cannot be described as completed product behavior.
