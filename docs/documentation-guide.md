# How this product is documented

Status: documentation working convention. Applies to future design, implementation, qualification and operating changes. The [source record](reference/sources-and-reset.md) owns historical/reset details.

## 1. Organize by question and ownership

Keep product intent, target design, delivered behavior and observed evidence distinguishable. Each fact has a canonical home; other documents summarize it and link to that home. The repository README explains the product and directs readers. It is not the detailed specification or progress database.

| Location | Owns | When it changes |
| --- | --- | --- |
| `docs/product/` | User journeys, vocabulary, entity semantics and application examples | A user-visible concept, workflow or domain invariant changes |
| `docs/architecture/` | Cross-service ownership, trust boundaries, topology and design rules | A boundary, data owner, dependency or trust assumption changes |
| `docs/services/<service>.md` | Service responsibilities, data, interfaces, failure and operating behavior | A service changes behavior, persistence, permissions or dependencies |
| `docs/engineering/` | Shared implementation standards, primary-source rationale and control-to-package verification mapping | Framework behavior, engineering policy, CI enforcement or a cross-cutting risk changes |
| `docs/contracts/` | Human-readable API/event conventions and examples | Contract semantics or cross-language usage changes |
| `contracts/openapi/`, `contracts/asyncapi/`, `contracts/schemas/` | Future canonical machine-readable API/event/message definitions | Schemas are implemented; clients and rendered references derive from these sources |
| `docs/decisions/` | Decision register and full ADR rationale | A consequential choice is proposed, accepted, rejected or superseded |
| `docs/implementation/phased-plan.md` | Programme sequence, scope and milestones | Scope, dependency order or a delivery milestone changes |
| `docs/implementation/phases/pNN.md` | Detailed phase package specifications | Package scope, dependencies, acceptance or operating impact changes |
| `docs/implementation/delivery-register.yaml` | Canonical execution status, delivery mappings and real evidence references | Work progresses, a gate is reviewed, a blocker arises or evidence changes |
| `docs/implementation/progress.md`, `traceability.md` | Derived reader views of the register | Regenerate; do not independently maintain the same fields |
| `docs/implementation/gates.md` | Acceptance criteria, evidence expectations and review responsibilities | Pass conditions or required environments change |
| `docs/implementation/requirements-and-qualification.md` | Requirement wording, invariants, evidence levels and campaign intent | A requirement or qualification obligation changes |
| `docs/implementation/support-matrix.md` | Planned release scope and support dimensions | A combination enters/leaves scope; actual support remains evidence-bound |
| `docs/operations/` | Deployment model and environment-independent runbooks | Installation, configuration, monitoring, upgrade or recovery changes |
| `docs/qualification/` | Feasibility records, campaign designs and sanitized gate-review indexes | A concrete campaign or review is prepared; raw evidence remains in approved systems |
| `docs/releases/` | Release process, manifest rules, readiness, notes and release-specific records | A release candidate is assembled and accepted |
| `docs/reference/` | External sources and historical provenance | Source evidence changes or historical material must be retained |
| `docs/templates/` | Reusable authoring structures | Repeated omissions require a better template |
| `next_work.md` | Immediate queue and navigation to package definitions | The next actionable work changes; do not duplicate the entire backlog or statuses |

Paths described as future are not implemented artifacts. When adding a real schema, move authoritative field definitions into it and retain explanatory examples in service/contract docs. Service docs still own why an interface exists, authorization and business semantics.

## 2. New work follows a linked record

1. Identify the user outcome and affected R-series requirements. New requirements receive a stable ID and recorded source or proposal rationale.
2. Select the phase/package, identify prerequisite decisions and contracts, and write a concrete work-package card before implementation.
3. Update the domain/service specification. Use an ADR for boundaries, trust, persistence, compatibility, major dependencies or support scope.
   Link applicable [engineering controls](engineering/coverage.md), their verification and any reviewed exception; keep detailed common conventions in the engineering guide rather than copying them into each service.
4. Specify positive, negative and recovery behavior. Give gate criteria stable IDs and identify the test environment and evidence level.
5. Implement contracts, code, deployment and meaningful tests in coherent increments. Reference requirement/package/decision IDs in change descriptions.
6. Record actual verification references and limitations in the delivery register. Regenerate views and update the next queue.
7. Update deployment/runbooks when operating behavior changes. Review qualification impact before publishing a support claim.

A documentation writing task may finish while implementation stays `NOT_STARTED`. Gate success is an explicit reviewer decision against evidence; it is never inferred from document length, code presence or a suggested command.

## 3. Naming and lifecycle

Use descriptive lowercase hyphenated filenames. Preserve P00–P11, PNN.NN, RNN, ADR-NNN and QNN IDs; never recycle an ID for another obligation. Gate IDs and statuses follow the [gates](implementation/gates.md) and [status model](implementation/status-model.md).

Add full decisions as `docs/decisions/adr-NNN-short-title.md` using the [ADR template](templates/adr.md). Record origin separately from disposition and identify the latest safe decision gate. A directed technology choice can coexist with open implementation details.

Detailed designs identify status, owner role, related IDs and last reviewed date/revision. Label proposed examples. When implementation differs, update the design in the same change or record a time-bounded tracked divergence. Preserve superseded decisions with replacement links. Put task procedures under `docs/operations/runbooks/`; keep cross-cutting deployment, observability, threat and support design documents directly under `docs/operations/`.

Operational credentials, live inventory, endpoint addresses, Terraform state and native evidence belong in approved operational systems. Repository records use synthetic examples and authorized evidence references. Historical completion flags never become new evidence.

## 4. Documentation required with each change

| Change | Documentation and evidence impact |
| --- | --- |
| New entity/invariant | Domain model, owning service, schema/example, requirement mapping and invariant tests |
| API/event | Source schema, semantic examples, compatibility policy, client impact and contract-test reference |
| Workflow/activity | Lifecycle specification, state/sequence diagram, retry/uncertainty/recovery rules and replay/failure evidence |
| Platform adapter | Capability declaration, affected support combinations, campaign design and scoped native evidence |
| Access/secret policy | Governance/trust model, permissions, credential lifecycle/runbook and negative tests |
| Database migration | Migrator privileges, compatibility window, upgrade/recovery procedure and representative data verification |
| Deployment/dependency | Version/BOM, configuration/network flows, rollback constraints and restore/upgrade evidence |
| UI task | Journey, error/held/empty/permission states, accessibility and browser verification |
| Release | Artifact manifest, support scope, qualification-impact review, upgrade notes, known issues and acceptance |

Each implementation review explains what changed for the user, which authority owns it, what remains compatible, what was verified and which evidence or external dependency is missing.

## 5. Maintain one source for each fact

The [status model](implementation/status-model.md) owns status meaning; [requirements and qualification](implementation/requirements-and-qualification.md) owns E0–E4 evidence levels; the [decision register](decisions/decision-register.md) owns decisions; the delivery register owns execution state. Link to these definitions instead of copying their enums.

Keep the phase plan as an overview and maintain detailed work in the phase pages. Review each phase against actual learning before implementation starts. Maintain procedures in the operating runbooks and bind their execution results to the tested artifact/environment rather than inferring readiness from written instructions.

Run the documentation generation/validation commands in [CONTRIBUTING](../CONTRIBUTING.md). Structural checks do not prove product behavior, native safety or operating acceptance.
