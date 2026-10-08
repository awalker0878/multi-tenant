# Capability qualification and runtime assurance: evaluation and implementation plan

Repository: [awalker0878/multi-tenant](https://github.com/awalker0878/multi-tenant/tree/main)  
Reviewed commit: [51f4a2afe650456a5afa31ce21f376116862238e](https://github.com/awalker0878/multi-tenant/commit/51f4a2afe650456a5afa31ce21f376116862238e)  
Review date: 8 October 2026  
Deliverable: evaluation and proposed implementation plan. No repository changes or native qualification are claimed.

## Recommended direction

Keep Assurance qualification decisions as the authority for supported capabilities. Make each decision traceable to verified evidence for an exact directed route, method, installed platform tuple and artifact set. Current runtime observations can confirm that the qualified conditions still hold, or suspend their use when they do not. Adapter declarations identify an implemented candidate; they cannot publish support or restore withdrawn qualification.

The core gap is the provenance and feedback path between a declared capability, independently observed behaviour, an accountable qualification decision, and the next assessment. Moving every enumeration into one table would resolve vocabulary drift, but would leave that gap open.

There is an important current-state limitation: Inventory's general planning projection explicitly returns declaration provenance, unassessed dimensions and empty capabilities/capacity. The real endpoint therefore fails closed for these requirements. A fabricated or incorrectly populated record can make the pure assessment engine return eligible, but this review did not demonstrate that a deployed endpoint currently supplies such a record.

## Findings against the seven concerns

| Concern | Evaluation on reviewed main | Resolution |
| --- | --- | --- |
| 1. Hard-coded method set | Confirmed. Generic assessment accepts four operation strategies; Inventory, Planning expansion/support and Lifecycle separately enumerate five migration methods. These are different concepts and naming schemes, not four versus five equivalent methods. | Introduce canonical, versioned identifiers for actions, execution strategies, migration methods and recovery modes, with explicit compatibility aliases. Generate consumer vocabularies from the same definitions. |
| 2. Scattered capability matching | Confirmed as an ownership and consistency risk. Inventory performs platform-specific profile/mapping validation; Planning matches requirements and qualifications; Lifecycle checks execution prerequisites. Those responsibilities should remain distinct. Directional qualification already exists in the P09 tranche/support path. | One Assurance-owned support resolution for exact routes, based on one definition registry. Keep native validation and execution safety in their owning contexts. |
| 3. Capacity | Partly confirmed. Assessment checks four scalar dimensions: vCPUs, memory, storage and addresses. It does not solve per-resource placement or reserve capacity. Lifecycle has a durable reservation journal, receipt checks and a PostgreSQL-backed competing-plans test. A production reservation-owner composition was not found in the downloaded Lifecycle source. | Connect authoritative owners and allocate a complete resource vector against actual pools and placement constraints. Keep assessment advisory until admission acquires bound leases. |
| 4. Dependencies | Confirmed in generic assessment: communication tuples are matched by exact value equality; dependency lists make a result conditional. However, native workflows already require independent policy-path evidence, including allow/deny cases. | Bind each intended flow to native topology, effective policy and measured path evidence, and feed that evidence into subsequent assessments. |
| 5. Isolation and failure domains | Confirmed in generic assessment. Mandatory isolation requirements are appropriate, but a matching True value is insufficient evidence. Existing AHV validation checks scope, policies in ENFORCE state and distinct quarantine networks; native policy probes add useful partial assurance. | Replace support assertions with evidence references to explicit isolation controls and actual placement/domain relationships. Verify the relevant controls and negative paths for the claimed scope. |
| 6. RPO/RTO | Confirmed for generic recovery matching, with an additional bug: values are compared by equality rather than an objective-specific numerical comparator. Migration code has measured lag/data-loss checks, native backup_restore observations and campaign timing/budget checks. Those are not a reviewed recovery profile automatically consumed by the next general assessment. | Define typed objective comparisons, collect application-level recovery measurements, and publish independently reviewed recovery qualification bounds with an invalidation path. |
| 7. Mutable wiring | Confirmed as a maintainability risk. Planning assigns three validation callbacks after construction; missing callbacks fail closed at relevant call sites. MigrationSupport is supplied by the production router, but MigrationPlans also permits its support callback to be None. Planning and Lifecycle duplicate stage tables. | Require immutable validation dependencies, remove optional qualification wiring for advertised operational flows, and derive stage descriptions from a pinned method definition while retaining mandatory domain safety checks. |

### Evidence supporting the findings

- [Generic method allowlist](https://github.com/awalker0878/multi-tenant/blob/51f4a2afe650456a5afa31ce21f376116862238e/services/planning/src/planning/domain/assessment.py#L84), [Qualification record checks](https://github.com/awalker0878/multi-tenant/blob/51f4a2afe650456a5afa31ce21f376116862238e/services/planning/src/planning/domain/assessment.py#L145), [Equality-based requirement matching](https://github.com/awalker0878/multi-tenant/blob/51f4a2afe650456a5afa31ce21f376116862238e/services/planning/src/planning/domain/assessment.py#L204) and [Four-dimensional capacity check](https://github.com/awalker0878/multi-tenant/blob/51f4a2afe650456a5afa31ce21f376116862238e/services/planning/src/planning/domain/assessment.py#L246).
- [Current Inventory planning projection](https://github.com/awalker0878/multi-tenant/blob/51f4a2afe650456a5afa31ce21f376116862238e/services/inventory/src/inventory/application/planning.py#L52): its empty capabilities and declaration provenance explain the current fail-closed behaviour.
- [Planning qualification reader](https://github.com/awalker0878/multi-tenant/blob/51f4a2afe650456a5afa31ce21f376116862238e/services/assurance/app/Http/Controllers/PlanningQualificationController.php) and [Migration qualification reader](https://github.com/awalker0878/multi-tenant/blob/51f4a2afe650456a5afa31ce21f376116862238e/services/assurance/app/Http/Controllers/MigrationQualificationController.php): exact records are read from protected mounted registries. The readers do not resolve the evidence and reconstruct qualification from verified case results.
- [Existing evidence finalization](https://github.com/awalker0878/multi-tenant/blob/51f4a2afe650456a5afa31ce21f376116862238e/services/assurance/app/Application/Evidence/Actions/ManageEvidence.php): verifies bytes and owner binding for simulation evidence, explicitly limits acceptance to E2, and does not establish native support.
- [Directed route matrix](https://github.com/awalker0878/multi-tenant/blob/51f4a2afe650456a5afa31ce21f376116862238e/services/planning/src/planning/domain/expansion.py), [Exact migration support checks](https://github.com/awalker0878/multi-tenant/blob/51f4a2afe650456a5afa31ce21f376116862238e/services/planning/src/planning/application/migration_support.py) and [Lifecycle methods and stage prerequisites](https://github.com/awalker0878/multi-tenant/blob/51f4a2afe650456a5afa31ce21f376116862238e/services/lifecycle/src/lifecycle/domain/migration.py).
- [Reservation journal](https://github.com/awalker0878/multi-tenant/blob/51f4a2afe650456a5afa31ce21f376116862238e/services/lifecycle/src/lifecycle/application/reservations.py), [Admission receipt requirements](https://github.com/awalker0878/multi-tenant/blob/51f4a2afe650456a5afa31ce21f376116862238e/services/lifecycle/src/lifecycle/domain/admission.py#L115) and [Competing-plans reservation test](https://github.com/awalker0878/multi-tenant/blob/51f4a2afe650456a5afa31ce21f376116862238e/services/lifecycle/tests/test_reservations.py#L107).
- [Independent native probes](https://github.com/awalker0878/multi-tenant/blob/51f4a2afe650456a5afa31ce21f376116862238e/workers/lifecycle/src/lifecycle_worker/infrastructure/evidence_probes.py), [Bound independent observation validation](https://github.com/awalker0878/multi-tenant/blob/51f4a2afe650456a5afa31ce21f376116862238e/services/lifecycle/src/lifecycle/domain/native_workflow.py#L246) and [Signed package and installed implementation verification](https://github.com/awalker0878/multi-tenant/blob/51f4a2afe650456a5afa31ce21f376116862238e/workers/lifecycle/src/lifecycle_worker/infrastructure/extension_trust.py).
- [Mutable Planning callback fields](https://github.com/awalker0878/multi-tenant/blob/51f4a2afe650456a5afa31ce21f376116862238e/services/planning/src/planning/application/planning.py#L16) and [Current production composition](https://github.com/awalker0878/multi-tenant/blob/51f4a2afe650456a5afa31ce21f376116862238e/services/planning/src/planning/bootstrap/server.py#L26).
- [ADR-018](https://github.com/awalker0878/multi-tenant/blob/51f4a2afe650456a5afa31ce21f376116862238e/docs/decisions/adr-018-qualification-lane-and-operational-admission.md), [ADR-022](https://github.com/awalker0878/multi-tenant/blob/51f4a2afe650456a5afa31ce21f376116862238e/docs/decisions/adr-022-release-support-and-requalification.md) and [Assurance ownership specification](https://github.com/awalker0878/multi-tenant/blob/51f4a2afe650456a5afa31ce21f376116862238e/docs/services/assurance.md) already establish the intended separation between implementation, qualification and operating acceptance.

The signed adapter-package path already checks installed Python implementation bytes against a signed manifest for its admitted built-in operations. Independent probes also check native behaviour for commissioned cases. The missing work is broader coverage and a trusted connection from these results to capability qualification and assessment. Neither signatures nor artifact hashes establish semantic correctness by themselves.

## Checks executed for this evaluation

These were bounded, synthetic pure-domain checks against the downloaded source. They did not use a running installation, native APIs or a reservation database.

| Check | Observed result | Meaning |
| --- | --- | --- |
| Repository planning fixture | eligible, reserved=False; demand 4 vCPUs / 8192 MiB / 80 GiB / 2 addresses | Eligibility does not reserve resources. |
| Replace evidence_refs with evidence://nonexistent/record | Still eligible | assess checks a non-empty reference list; it does not resolve those references. This is a record-validation gap, not a demonstrated public-input bypass. |
| Qualification expires exactly at assessment time | unknown | Existing expiry protection works at the boundary. |
| Remove tenant-isolation observation | unknown | Missing mandatory observations do not pass. |
| Supply the current Inventory projection's unassessed/empty capability shape | unknown | The current general projection fails closed. |
| Request RPO 120 seconds; provide observed and qualified value 60 seconds | blocked: constraint_not_satisfied | Generic equality rejects a better numerical bound. |
| Assess twice against the same headroom | eligible in both cases | Assessment is advisory. This does not demonstrate double allocation at admission. |
| Compare Planning and Lifecycle stage sequences for five methods across six modes | 30 of 30 matched | Existing duplicated tables currently agree; future divergence remains a maintenance risk. |

The full repository test suite and native campaigns were not run. The scratch interpreter lacks pytest; the existing PostgreSQL concurrency test was inspected, not executed. The implementation plan below therefore specifies acceptance work still required.

## Target model and ownership

Use one definition registry and one authoritative qualification publication path, rather than a shared cross-service business-logic package.

| Object | Owner | Contents and limits |
| --- | --- | --- |
| Capability/method definition | Reviewed contracts, published through Assurance | Stable ID, revision, value type, unit, comparator, applicable action/strategy/method, required dimensions/cases, constraints and supported contract versions. A definition carries no support grant. |
| Adapter declaration | Lifecycle/Inventory adapter build owner | Implemented IDs, handler bindings, package/image/source digests and contract versions. Describes candidate implementation only. |
| Runtime observation | Inventory and independently enrolled observers | Exact subject, native scope, original measurement time, expiry, configuration/topology generation, artifacts, measured values, case result and protected evidence receipt. |
| Qualification decision | Assurance reviewer | Exact tuple/route/artifacts, required case coverage, verified evidence receipts, reviewed bounds, conditions/exclusions, evidence level, decision revision, validity and withdrawal state. |
| Placement and reservation | Authoritative capacity, storage and address owners | Concrete resource mappings, complete demand vector, physical pool identity, policy version, lease/fence and current owner receipts. |
| Assessment and immutable plan | Planning | Required capability evaluations, explanatory findings and pinned definition/qualification/observation revisions. Does not grant a native effect. |
| Admission and execution | Lifecycle | Current approval, live support validity, reservation leases, authority/fencing and stage-specific independent checks. |
| Operating acceptance | Designated receiving owner, recorded by Assurance | E4 acceptance and limits, kept distinct from native E3 qualification and individual change approval. |

Capability definitions should contain separate identifiers for action, execution strategy, migration method and recovery mode. For example, application.migrate, native_api_export_import and VM_COLD_EXPORT currently describe related but different layers. Do not silently collapse them into one enum.

All services consume the same immutable definition revision through generated contract projections or a validated local snapshot published by Assurance. Plans pin its digest. Unknown IDs, missing implementation handlers, incompatible revisions and undeclared extensions fail closed. Native adapter code remains explicitly registered and reviewed; a registry row cannot load arbitrary code or create an implementation.

For any required capability, assessment eligibility needs all of the following:

1. A known definition with an implemented and correctly bound adapter declaration.
2. An accepted qualification decision for the exact applicable scope, tuple and artifacts.
3. Verified evidence coverage for the definition's required cases.
4. Current independent observations showing that the qualified conditions still hold.
5. Workload/policy constraints satisfied with the definition's typed comparator.
6. No applicable contradiction, withdrawal, unresolved dependency or expiry.

Execution additionally needs a feasible concrete placement, authoritative reservations, current approval and fenced stage authority. An assessment can pass while resources remain unreserved; make that distinction explicit in the API and Console.

Use the existing eligible / conditional / blocked / unknown vocabulary. Known violations are blocked; missing, stale or unverifiable evidence is unknown; unresolved explicit dependencies remain conditional. None of the latter three authorizes an operational native effect. A successful probe cannot elevate E2 into E3 or create E4 operating acceptance.

## Proposed contracts

Add versioned contracts rather than changing the meaning of existing immutable bytes.

| Proposed contract | Essential fields |
| --- | --- |
| capability-definition-v1 | ID/revision, value schema, unit/comparator, action/strategy/method, required cases, constraints, contract versions, definition digest |
| capability-observation-v1 | Subject/scope, capability ID/revision, measured value, native/configuration/topology generations, observer, original measurement time, expiry, artifacts, evidence receipt |
| qualification-v2 | Exact scope, definition/profile/route/artifact digests, decision ID/revision, reviewer, evidence receipts and case coverage, reviewed constraints/bounds, E3/E4 tier, validity, suspension/revocation revision |
| runtime-conformance-v1 | Definition and qualification binding, attempted stage/operation, expected and observed outcome, probe-suite revision, independent observer, measured values, protected evidence reference |
| placement-reservation-v2 | Owner, physical pool, plan/demand/placement digests, resource allocations, allocation policy/generation, lease and fencing token, expiry, receipt revision, state |
| support-resolution-v1 | Pinned definitions and decisions, verified evidence summary, current validity epoch, exact permitted scope/limits and reasons; no native-write grant |

Qualification evidence references must resolve to finalized, authorized custody records. Bind producer identity, source/artifacts, environment, subject, tested requirements and original observation time. Verify hashes and required case completeness before an authorized independent reviewer records a decision. Keep protected evidence bytes behind existing custody boundaries; expose only authorized summaries to Planning and Console.

Mounted legacy records may remain an import/publication transport, but cannot manufacture trusted qualification. Import them as unverified unless backed by the new validated decision/receipt path. Avoid translating a legacy supported or qualified flag directly into an accepted v2 decision.

For generic numeric requirements, implement registered comparators: at_most for recovery time/data-loss bounds, at_least for capacity quantities, membership for enumerated choices, and domain-specific predicates for relational/topology constraints. Arbitrary callers cannot select a weaker comparator. Validate units; a seconds allowance cannot substitute for a byte allowance.

## Delivery sequence

The work items below are proposed implementation increments, not existing delivery-register completion claims.

### CT-00 — Make current support claims and validation boundaries explicit

Purpose: preserve the current fail-closed state while creating a safe foundation for additional observations.

- Expose the actual reason for unknown capabilities in the Console. Separate assessed requirements from reserved capacity and admission status.
- Make operational qualification/support validators required constructor dependencies. Extract validation into independent services/ports to avoid the current Planning/MigrationPlans callback cycle.
- Use explicit denied/unavailable implementations for installations that do not commission a capability. Missing advertised validation dependencies must fail startup/composition checks.
- Require verified record provenance before positive support can be published. Retain the existing isolated-campaign lane and its non-waivable isolation/custody checks.

Change: Planning application/composition, migration plan support wiring, Assurance qualification readers, Console assessment presentation.

Gate: neither an arbitrary non-empty evidence reference nor an omitted operational support validator can produce a trusted positive result. Current empty Inventory observations remain unknown. Missing callbacks must not be replaced with permissive defaults.

### CT-01 — Introduce the canonical registry and typed matcher

Purpose: remove independently maintained platform/method vocabulary and incorrect comparison semantics.

- Add contracts/capabilities/definitions-v1.json and associated schemas.
- Extend the repository's contract-generation checks to produce PHP, Python and TypeScript projections and explicit v1 aliases. Verify generated output in CI.
- Replace manually maintained method/platform lists in Inventory readiness/workload, Planning model/assessment/expansion/support, Lifecycle migration/expansion and worker declarations.
- Make generic assess dispatch through registered requirement evaluators. Retain platform mapping validators as specialised handlers rather than pretending all native semantics are identical.
- Describe stage DAGs and required case identifiers in the versioned method definition. Planning compiles that description; Lifecycle verifies the same pinned version and still enforces mandatory safety invariants.
- Reject a definition advertising a method for which the installed implementation has no handler or conformance suite.

Gate: one definition change propagates consistently to every consumer; a new unknown method cannot execute; 60-second RPO satisfies a 120-second maximum while 180 seconds fails; wrong units fail; the existing 30 stage combinations preserve their reviewed behaviour. A new method needs one definition plus implementation/qualification work, without editing unrelated consumer enums.

### CT-02 — Close the qualification and runtime evidence loop

Purpose: ensure correctly populated, reviewable support records and current conditions.

- Implement native evidence finalization and qualification decisions within Assurance using its existing custody pattern. Keep the E2 simulation path separate.
- Add an append-only decision/revocation history and a current support projection with a monotonically advancing validity revision/epoch.
- Connect installed adapter/image/implementation digests, independent native probes and required-case coverage to an exact qualification.
- Extend Inventory's planning projection to emit verified current observations, native tuple provenance and concrete resource/domain bindings. Do not mark enrolled configuration as observed.
- Publish capability observations from actual native readers and commissioned evidence producers. Reuse signed commissioning receipt verification where applicable.
- Reject missing, conflicting, future-dated, mismatched or incomplete records. Re-reading an old result must not refresh its measurement timestamp.
- On drift or a required conformance failure, hold the affected scope immediately and publish a durable, idempotent invalidation. Planning marks affected plans stale; Lifecycle checks current validity before an effect instead of depending solely on event delivery.
- A later passing result can supply new evidence, but restoring qualification requires the appropriate review decision. Do not automatically re-enable support.

Gate: a missing evidence object cannot be qualified; a declaration/runtime contradiction prevents the next assessment and next applicable effect; out-of-order/duplicate events cannot restore an older positive decision; unrelated qualified scopes are not globally withdrawn.

### CT-03 — Add feasible placement and production reservation authority

Purpose: prevent two admissible jobs from consuming the same physical headroom and account for fragmentation.

- Collect capacity by host/cluster, storage pool/class, network/address pool, tenant quota and failure domain. Bind every snapshot to its native generation and allocation policy.
- Evaluate each workload's shape, NUMA/host constraints when required, storage class/locality, affinity/anti-affinity, domain placement and reserve policy. Aggregate capacity alone is not placement feasibility.
- Apply explicit CPU/memory/storage overcommit policies, HA/maintenance headroom and tenant/physical limits.
- Commission a stable authoritative owner for each physical pool. Reuse Lifecycle's durable reservation journal; implement production Owner ports and wire them into admission/native custody.
- Reserve a complete placement/resource vector atomically within each authority. Lock or conditionally update shared physical pools independently of tenant labels; two tenants must not partition the same physical capacity into separate ledgers.
- Bind receipts to the exact plan, placement, demand, owner revision, lease and fence. Multi-owner allocation uses a durable hold/compensation sequence; dispatch occurs only after all required receipts are confirmed.
- Reconcile live provider allocations with ledger reservations without double-counting materialized allocations. Uncertain outcomes and expired live leases stay held until the owner proves they are unused.
- Where provider APIs cannot enforce reservation exclusivity, require a commissioned control boundary for competing writes or another accepted enforcement mechanism. A local ledger plus periodic polling cannot guarantee exclusion of unmanaged external changes; hold the claim until that boundary is established.

Gate: two concurrent plans needing the same remaining allocation yield one admitted allocation and one held/denied result; enough aggregate memory spread across unsuitable hosts is rejected; partial owner failure, lease loss and lost replies cannot cause a second allocation or automatic release of a live resource.

### CT-04 — Evaluate network, isolation and failure-domain evidence

Purpose: replace generic True/value matches with explicit, scoped assurance.

- Compile each communication dependency into an intended directed flow between actual mapped endpoints, with protocol/port, address family, routing/VRF/VPC context and applicable ingress/egress/return policy.
- Read effective route and firewall/security policy through enrolled native readers. Pair configuration evaluation with authorised positive and negative path probes; reachability alone cannot establish policy isolation.
- Reuse native policy_paths and required-service probes, but bind each result to its actual requirement and topology/policy revision. Include same-host, inter-host and edge coverage where the claim requires it.
- Evaluate tenant/project boundaries, RBAC/service identities, network policy, storage/key access and required separation controls. A VPC/project ID or ENFORCE flag alone does not establish the full isolation claim.
- Bind failure-domain requirements to actual mapped workload locations and the relevant hierarchy/shared dependencies: host, cluster, rack, zone, storage or other required fault boundary. A logical zone label must not imply independently observed physical separation.
- Recheck actual post-placement mappings and mandatory isolation controls before workload activation. Configuration drift withdraws the affected observation/support use.

Gate: a blocked required route, unexpectedly allowed cross-tenant path, disabled relevant policy or same-domain placement contradicts the claim; missing physical/topology evidence remains unknown. Record the tested coverage and exclusions rather than claiming universal isolation.

### CT-05 — Feed measured recovery into the next assessment

Purpose: qualify recovery objectives from observed application recovery rather than declared values.

- Collect protected RecoveryObservation records for restore/recovery exercises and relevant incidents.
- Define the RTO clock boundary in the requirement: from the selected failure/recovery trigger to verified application readiness, including dependencies, restored data and usable keys. Workflow elapsed time alone is insufficient.
- Derive RPO from an independently bound source commit/checkpoint boundary and the recovered consistency boundary. Preserve sequence/time/byte units; do not infer time loss from byte loss without qualified evidence.
- Bind measurements to dataset identity, size/change rate, recovery method, artifacts, topology, capacity/load and required services.
- Publish a reviewed RecoveryProfile containing tested ranges, sample count, conditions, worst observed/accepted bound and freshness. Do not invent percentile confidence from a single drill.
- Use objective-specific numerical matching. A missed objective or invalid measurement suspends the affected scope, triggers reassessment and requests retest; positive measurements become evidence for review rather than self-issued support.

Gate: an accepted 60-second RPO bound can satisfy 120 seconds for the qualified workload envelope; a 180-second observation cannot; a restore that completes while the application or keys remain unusable cannot satisfy RTO; a failed required drill makes the next assessment held/unknown or blocked with a clear reason.

### CT-06 — Exercise the complete path and retire duplicated authority

Purpose: demonstrate the composed system rather than just testing individual tables.

- Start with one explicitly commissioned VMware-to-OpenStack VM_COLD_EXPORT route, exact installed tuple and bounded representative application. Keep provisioning qualification distinct from migration qualification.
- Run definition validation, record finalization, independent review, observation publication, assessment, allocation, approval, admission, native execution, drift/failure invalidation and subsequent reassessment end to end.
- Run the existing denied, uncertainty, writer-fencing, reconciliation, recovery and tenant-boundary suites alongside new capability tests.
- Verify every advertised entrypoint, including plan read/validity, migration variants, native plan execution, campaign scheduling, enterprise operations and worker effects. No path may rely on the old boolean-only qualification shortcut.
- Compare the new engine in read-only shadow mode. Explain all changes from current results before switching the authoritative assessment path.
- Keep old method-definition versions available for compatible reads and recovery of existing immutable jobs. Never reinterpret approved plan bytes under a new definition or reorder stages during an in-flight workflow.
- Complete workflow replay/upgrade checks, publish supported definition/contract ranges, and remove hand-maintained duplicate enums/aliases only after all consumers have transitioned.
- Retain scope-specific kill/hold controls, signed/source-bound test evidence and explicit E3/E4 receiving decisions. Expand additional routes only after their own cases and review pass.

Gate: a declared capability whose observed behaviour differs is detected, held, and reflected in the next decision; approval cannot overcome a withdrawn claim; no stale cache or missing callback permits a native effect; the same evidence/definition revisions are explainable across Console, Planning, Assurance and Lifecycle.

## File-level implementation map

Existing paths below were inspected; new names are proposals.

| Area | Existing files to modify | Proposed additions |
| --- | --- | --- |
| Canonical vocabulary and contracts | contracts/schemas/planning/qualification-v1.json via a new version; expansion/tranche and adapter-package contracts; scripts/p05/generate_contracts.py, scripts/p07/generate_product_contracts.py and scripts/p09/generate_contract.py | contracts/capabilities/definitions-v1.json; capability definition/observation, qualification-v2, runtime conformance and placement receipt schemas; one capability generation/check command |
| Assurance support authority | PlanningQualificationController.php, MigrationQualificationController.php; Application/Evidence/Actions/ManageEvidence.php for shared custody primitives, preserving E2 semantics | app/Domain/Qualification/; app/Application/Qualification/Actions/ for finalize/decide/suspend/revoke/resolve; owned qualification/evidence projection migrations and durable outbox |
| Inventory projection | application/planning.py; domain/readiness.py, workload.py, migration.py, vmware.py and ahv.py; infrastructure/readiness_evidence.py; worker profile/native readers | domain/capabilities.py; application/capability_observations.py; infrastructure verified-observation projection and native topology/capacity readers |
| Planning | domain/assessment.py, model.py, expansion.py, migration_plan.py, compilation.py; application/planning.py, migration_support.py and migration_plans.py; infrastructure/owners.py; bootstrap/server.py | domain/matching.py and placement.py; required application validation/support/placement ports; immutable constructor composition |
| Lifecycle admission and capacity | application/reservations.py and execution.py; domain/admission.py, migration.py and native_workflow.py; native custody/owner clients and bootstrap composition | production reservation Owner adapters; capacity/placement policy validation; lease/vector receipt persistence and admission composition |
| Runtime conformance | worker infrastructure/extension_trust.py, evidence_probes.py and migration_method.py; service native observation validation and workflow persistence | capability/qualification-bound conformance publisher and reviewed recovery measurement producer |
| Console and delivery evidence | planning contracts/workspace, inventory operator/readiness views; docs/implementation/support-matrix.md, phased/delivery register inputs and relevant runbooks | operator-facing evidence/limits/expiry/retest presentation; exact-source acceptance ledger |

Respect the existing context map and dependency direction. Generated contract definitions are integration data; services must not import another service's private domain or access its database. Use the repository's Laravel Domain/Application convention inside Assurance and the existing Python layering elsewhere.

## Acceptance ledger

| ID | Scenario | Required outcome |
| --- | --- | --- |
| A01 | Valid-looking qualification contains a missing, tampered or foreign evidence receipt | No trusted positive support. |
| A02 | Declaration advertises a capability; required independent case fails | Exact scope held; new assessments and applicable effects denied pending review/retest. |
| A03 | Adapter bytes, platform/API/backend or required topology changes | Qualification cannot carry forward silently. |
| A04 | Two plans reserve the same remaining physical vector concurrently, including across tenants | At most one valid allocation; no oversubscription or cross-tenant disclosure. |
| A05 | Aggregate capacity is sufficient but no valid workload placement exists | Placement rejected or held with a concrete explanation. |
| A06 | Required flow is blocked, or a forbidden path is reachable | Dependency/isolation failure overrides declarations and prior qualification. |
| A07 | Anti-affinity workloads occupy the same required fault boundary | Domain requirement fails; labels alone cannot satisfy it. |
| A08 | RPO 60 satisfies maximum 120; RPO 180 does not; seconds and bytes differ | Correct typed comparisons and units. |
| A09 | Restore exceeds RTO, violates consistency or lacks keys/services | Failed recovery evidence affects the next assessment. |
| A10 | Qualifying evidence expires, is superseded or is revoked between plan approval and effect | Lifecycle holds before the effect; approval is not a bypass. |
| A11 | Invalidation is delayed/duplicated/reordered; cache is stale; owner is unavailable | Current authority checks fail closed and preserve decision ordering. |
| A12 | Optional callback/handler is omitted from an advertised execution path | Composition or explicit runtime denial, never skipped qualification. |
| A13 | Owner accepts allocation/effect but reply is lost | Reconciliation, with no speculative retry/release or hidden fallback method. |
| A14 | Old approved plan survives a registry/workflow upgrade | Pinned-version compatibility or explicit hold; no reinterpretation. |
| A15 | New method/platform is registered without an implementation or qualification | Visible candidate/unknown status; no native execution. |
| A16 | E2 simulation passes; E3 native or E4 receiving decision is absent | No automatic promotion of evidence level or operating acceptance. |

Release evidence must identify source commit, definition/artifact digests, environments, cases run, original observations, failed/skipped cases, reviewer decisions and limits. An engineering or synthetic test pass does not close native qualification.

## Rollout and completion criteria

1. Land truthful status reporting and required validation wiring while maintaining current holds.
2. Publish versioned definitions and validated evidence/qualification contracts.
3. Populate native observations through authenticated producers; never backfill observed status from declarations.
4. Commission capacity owners and the required network/isolation/recovery evidence for the first route.
5. Run shadow assessment and investigate every changed eligibility result.
6. Execute the exact native campaign and independent receiving review; activate the new authority path only for accepted scopes.
7. Update the delivery/support records and remove superseded duplicate definitions after consumer and workflow compatibility checks.

The work is complete when the product can explain an exact support claim from definition through adapter identity, independently measured evidence, reviewed qualification, current placement/leases and live admission—and a contradictory runtime result changes the next assessment without waiting for the original expiry timestamp.
