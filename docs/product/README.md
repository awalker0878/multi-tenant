# Product definition

Status: proposed product specification, 2026-10-04. The repository contains a delivery plan; the capabilities below are intended outcomes, not implemented features. Product scope and acceptance are resolved through P00, with the initial route feasibility required before that phase closes.

The [scope and release boundaries](scope.md) define included outcomes and expansion rules. The [operating targets](operating-targets.md) define measurement and ratification. Use the [domain model](domain-model.md) for invariants and the [application walkthrough](application-walkthrough.md) for the connected user and service journey.

## What the application does

Enterprise Workload Mobility is a control plane for operating applications across approved hosting platforms. An operator describes an application and its requirements, discovers available infrastructure, compares possible placements and reviews a plan that explains what will change. The product obtains the required approval, coordinates long-running work through scoped workers and records the observed result and supporting evidence.

The unit of work is a business application: its workloads, datasets, dependencies, network access, security boundaries, shared services and recovery requirements. Moving a VM is one possible action within that larger lifecycle. A technically successful import does not complete a migration if the application cannot authenticate, reach its data, enforce required isolation or recover from failure.

The intended platform scope includes VMware, Nutanix AHV and OpenStack. The first proposed route is native OpenStack provisioning followed by one VMware-to-OpenStack offline migration method for a selected Linux application. P00 must demonstrate feasibility and select the exact method; application rebuild/restore is the preferred proposal for reproducible applications. Whole-VM conversion remains a separate method for applications that cannot be rebuilt, with its own P09 qualification. Each platform installation, direction, operation, guest profile and method needs its own qualification evidence.

Users access a Laravel/Inertia/Vue console. Laravel/PHP services own business governance, catalogue and assurance; Python services own inventory, planning and lifecycle coordination. Scoped workers perform discovery and approved native work. The [architecture](../architecture/target-architecture.md) defines their ownership and deployment boundaries.

## Users, jobs and visible outcomes

The roles below describe responsibilities for product design. They are not pre-approved permission bundles. P02 must define allowed actions and separation of duties at resource and environment scope.

| User | Job to accomplish | What the product must show | Acceptance evidence |
| --- | --- | --- | --- |
| Application owner | Register the application, identify accountable owners and state service/data requirements | Workload and dependency map; required flows; downtime, consistency and recovery criteria; revision history | An owner can review the complete application scope and identify missing requirements before planning |
| Tenant administrator | Delegate access within the tenant and manage its permitted environments | Membership, resource/action scopes, grants and revocations; effective restrictions | Negative permission checks and visible, attributable access changes |
| Platform administrator | Commission a site and expose approved capabilities | Endpoint trust, discovery scope, installed versions, freshness, service dependencies and readiness blockers | Read-only discovery and independently reviewed commissioning evidence |
| Planner/operator | Compare destinations and prepare executable work | Per-requirement fit, unknown facts, remediation, capacity assumptions, effect sequence and recovery boundary | A second operator can explain why a destination is eligible or blocked using the recorded inputs |
| Approver | Decide whether a specific change is permitted | Exact plan digest, affected resources, destructive effects, outage window, residual risks and authority required | Approval binds the reviewed plan; a changed plan or revoked grant is rejected |
| Execution operator | Run approved work and respond to partial failure | Job progress, confirmed outcomes, held operations, safe next actions and correlated evidence | Fault campaigns demonstrate safe resumption and explicit recovery decisions |
| Assurance reviewer/auditor | Determine what was proved and what is supported | Requirement-to-evidence trail, exact tested tuple, artifact revisions, limitations, expiry and revocations | Independent support decision; unsupported combinations remain visible |
| Service operator/SRE | Install, monitor, upgrade and recover the product | Dependency health, queues, freshness, held jobs, capacity, alert ownership and runbooks | Restore, upgrade and incident exercises plus receiving-team acceptance |

## Operator journey

1. **Describe:** select the tenant and environment, define the application and workloads, specify required service and security outcomes, and publish an immutable intent revision.
2. **Discover:** collect read-only observations from enrolled endpoints. Review coverage, native identities, freshness and ownership conflicts.
3. **Assess:** compare the intent with candidate destinations and exact capability evidence. Explain every unmet or unknown mandatory requirement.
4. **Plan:** produce a pinned, immutable action graph with resource scope, reservations, effect order, downtime and recovery conditions.
5. **Approve:** show the reviewer the full change and obtain the decisions required for that digest and scope.
6. **Execute:** recheck current authority and preconditions, coordinate durable work and verify native outcomes. Surface uncertainty as a hold requiring reconciliation.
7. **Accept and operate:** verify application health, isolation, data correctness and recoverability; publish only the qualified scope; retain operational evidence.
8. **Change or retire:** create a new intent and plan for material changes. Retirement requires explicit scope and authority, including retained data and service allocations.

The [worked application example](application-walkthrough.md) follows these steps with synthetic records and failure cases. The [domain model](domain-model.md) defines which records mean desired, observed, authorized and executed state.

## Usable delivery milestones

Milestones describe what a user can do when the named gates pass. Their current status remains in [progress](../implementation/progress.md); this page is not a second completion tracker.

| Milestone | First phase | Useful outcome | Limit on the claim |
| --- | --- | --- | --- |
| Catalogue workspace | P03 | Create and revise a multi-workload application with ownership, dependencies and security/service intent | No discovery, placement or native support implied |
| Read-only assessment | P04–P05 | Inspect actual commissioned inventory, compare destinations and review explained plans | Observations and plans grant no native write authority |
| Complete simulated journey | P06 | Review, approve and execute the application workflow against controlled doubles; rehearse faults and holds | Simulation is labeled throughout and proves no native capability |
| Native provisioning | P07 | Provision, verify, recover and retire the selected OpenStack application under approved qualification campaigns | Ordinary operation requires the independently qualified exact tuple and current authorization |
| Native offline migration | P08 | Rehearse and move the selected VMware application to OpenStack with data and writer authority checks | No reverse, warm/live or different-method support inferred |
| Operated pilot and release | P10–P11 | Run an accepted tenant/application scope with trained operators, exercised recovery and a published support matrix | Support covers only the released artifacts and accepted tuples |

## Success measures and acceptance questions

P00 assigns accountable owners, baselines, measurement windows and thresholds. The existing [cross-cutting targets](../implementation/phased-plan.md#5-cross-cutting-quality-and-operating-targets) are proposed inputs; no new target is approved by this document.

| Outcome | Measurement and evidence source | Acceptance question |
| --- | --- | --- |
| Usable application model | Representative user task completion and validation errors in the catalogue journey | Can an application owner express the selected real workload without undocumented side records? |
| Explainable placement | Requirement-level assessment results, pinned inputs and observed freshness | Can an operator explain both acceptance and rejection of each candidate? |
| Predictable change | Plan-versus-observed effect comparison, approved window and actual timings | Did execution change only its authorized resource/field scope and meet the application objective? |
| Preserved protection | Native positive/negative flow tests, service receipts and restore evidence | Are isolation, identity, monitoring and recovery usable after activation? |
| Recoverable execution | Fault-campaign outcomes, held-operation age and operator recovery steps | Can interrupted work resume or recover without duplicating effects or losing accepted writes? |
| Bounded support claims | Every published capability linked to a current qualification dossier | Can the reviewer trace the claimed operation to the exact tested conditions? |
| Operability | Install/upgrade/restore exercise, alert delivery and receiving-team review | Can a trained operator run the service without depending on its original developer? |

## Scope boundaries

- The first release is a hosting and workload-mobility product. Billing, a general-purpose ITSM suite and an enterprise password directory are not initial product capabilities.
- Existing systems remain authoritative for native resources, address allocation, DNS, backup and other shared services. The product consumes scoped owner contracts and records receipts.
- Application portability means explicitly represented requirements plus proven destination outcomes. A uniform UI does not imply identical platform features.
- Brownfield discovery is observation-only. Managed adoption requires a later explicit ownership transfer and qualification path.
- Sovereignty, availability and security are evaluated against the actual deployment and operating arrangements. Product naming does not establish any of these properties.
- Qualification campaigns may test unqualified candidates only in an isolated, explicitly approved lane. Campaign authorization cannot be used for production work.

## Keeping the product specification current

Update this page when user tasks, first-release scope or milestone outcomes change. Update [the domain model](domain-model.md) when meanings, ownership or cardinalities change; resolve the associated ADR before those choices become implemented contracts. Update [the walkthrough](application-walkthrough.md) when a user-visible workflow or recovery boundary changes. Service details belong in [service specifications](../services/README.md), wire examples in [contract examples](../contracts/examples.md), and implementation/evidence status in the implementation registers. Link these records in the same change so a product description cannot silently outpace support.
