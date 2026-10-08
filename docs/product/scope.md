# Product scope and release boundaries

Owner: product lead with application, platform and service owners. Related work: P00.01, P00.04, P09, P11; R01, R05–R14, R18–R28, R35–R36; ADR-014, ADR-021 and ADR-022.

## Product outcome

Provide a tenant-aware operator application that turns portable application intent into an assessed, approved and observed hosting operation. Users must understand which requirements can be satisfied, what a change will do, who authorized it, what actually happened and how to recover when the outcome is uncertain.

The product owns its catalogue, governance, plans, operation authority and evidence records. Infrastructure platforms and service providers continue to own their actual resources and service state. Tenant isolation, resource ownership and execution scope apply across every workflow.

## Initial delivery boundary

| Area | Included outcome | Boundary of the initial release |
| --- | --- | --- |
| User access | Federated identity, tenant membership, delegated actions and attributable approval | Approved identity integration and roles; no general-purpose identity directory |
| Application catalogue | Application deployments, workloads, placement intent, dependencies and immutable revisions | The reviewed domain model and selected representative application |
| Infrastructure inventory | Commissioned site endpoints, read-only observations, completeness and freshness | Selected VMware source and OpenStack target tuples; other profiles remain explicit |
| Assessment | Capability/policy matching, explainable eligibility and destination comparison | Required unknown or unsupported outcomes block execution |
| Planning | Immutable effects, resource mappings, service prerequisites, risks and recovery boundaries | Each plan binds exact revisions, environment, method and scope |
| Provisioning | Selected OpenStack/Linux application with networking, guest and shared-service readiness | Exact image, backend, security and service profile qualified by Q05/Q06 |
| Migration | P08 VMware-to-OpenStack native migration | Explicitly selected method, isolated clone/export, copy-only conversion/transformation and qualified delta or cold cutover under ADR-014 |
| Operations | Controlled cancellation, reconciliation, recovery and retirement | Only the operations and failure cases included in the support record |
| Assurance | Traceable evidence and exact-scope qualification/acceptance | Claims apply to the recorded tuple and product revision |

The first application is a bounded multi-workload service with stateful data. Its selection records source membership, dependencies, datasets, keys, boot/device constraints, required network flows, service dependencies, acceptance queries and allowed outage. The [walkthrough](application-walkthrough.md) is the synthetic model used to challenge those requirements.

For rebuild/restore, the selection also pins target image and application artifacts, configuration and secret references, application/database version compatibility, the capture/restore mechanism and consistency procedure. The target must be reproducible without copying an opaque source operating-system disk. Final cutover quiesces application writes, establishes an application-consistent capture and independently excludes source/other writers before permitting target writes. “Offline” describes this application outage; it does not imply whole-VM disk conversion. Actual image, guest and tool versions remain P00 inputs rather than inherited historical selections.

## Release expansion

P09 selects additional platform operations, migration directions, guest profiles, data methods and brownfield adoption. The [support matrix](../implementation/support-matrix.md) contains all six directed cross-platform routes and relevant profile dimensions. Selecting a tranche creates concrete packages, campaigns and capacity needs; it does not confer inherited qualification.

P07 provisions OpenStack through native APIs. P08 selects one explicitly qualified migration method from source and destination capability profiles. Generic whole-VM movement uses an isolated migration copy, `ExportVm`/NFC, verified transfer, any explicitly planned copy-only conversion and destination native APIs. Guest transformation occurs on the copy. Restarting production after a baseline requires a qualified application or file delta method; opaque workloads without one require cold migration. No method is an automatic fallback. Native provisioning and migration require separate Q05/Q06 and Q07 qualification.

The initial release does not promise live migration, zero downtime, universal guest conversion, all API/backend combinations, every same-family relocation topology or autonomous operation across disconnected trust boundaries. Required capabilities remain represented even when their implementation is deferred. A later release may include them only after scope selection and relevant evidence.

## Roles and separation of duties

Application owners define intent and application acceptance. Tenant administrators manage delegated access within their tenant. Operators prepare and execute admitted work. Approvers review exact plans and change windows. Platform and service operators own their native endpoints, service readiness and recovery prerequisites. Assurance reviewers judge evidence independently of the implementation claim.

One person may hold several organizational responsibilities, but the authorization policy must enforce any required action-level separation. Support or emergency access is time-bounded, scoped and audited; it cannot bypass tenant context or invent a qualification result.

## Adoption and retained data

Greenfield deployment means a new product runtime and its own data model. Managing existing infrastructure is a separate adoption capability: observe first, identify all current writers, define exact object/field ownership, prove no-change reconciliation and obtain transfer authority.

P00.01 determines whether previous operational intent, evidence or state must be retained. Where required, preserve originals, inventory provenance and references, reconcile import results and prevent simultaneous old/new writers. Active workflow authority is not imported blindly. An archive/import decision must identify owner, retention, access, reconciliation and disposition conditions.

## Scope-change control

For each requested addition, identify the user outcome, affected requirements, service/contracts, native tuples, data/security assumptions, campaign changes, staffing/access dependencies and schedule impact. Record the decision under ADR-022 or the relevant domain ADR. Update the phase cards, support matrix, canonical delivery mappings and operating procedures together.

A scope reduction must state which users, operations or combinations are excluded. A required security or recovery outcome cannot be weakened while preserving the same support claim. Release readiness uses G10/G11 and the evidence-backed scope rather than the number of implemented adapters.
