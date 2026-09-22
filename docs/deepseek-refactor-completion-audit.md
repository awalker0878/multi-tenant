# DeepSeek Refactor Completion Audit

> Status: active completion audit
>
> Baseline audited: main at 1b7756e4df52ebe58ac8d93266977a27915dc3dc
>
> Governing specification: docs/deepseek-master-refactor-provisioning-prompt.md
>
> Purpose: close the remaining repository-side gaps in the portable provisioning refactor without weakening existing architecture, safety, authority, qualification, or lifecycle boundaries.

## 1. Authority and use

This document is the working completion audit for the refactor defined by docs/deepseek-master-refactor-provisioning-prompt.md.

It does not replace the master prompt. If this audit and the master prompt differ, the master prompt governs unless a newer accepted architecture decision explicitly changes the requirement.

This audit converts the remaining gaps into verifiable completion gates. A gate is not complete because a document says it is complete, because a fixture passes, because code exists in the expected directory, or because an interface has been scaffolded. A gate is complete only when the current active code path, tests, documentation, examples, and cleanup all agree.

The required operating rule remains:

    migrate -> verify -> delete superseded implementation

Git is the history. The working tree must describe the current system.

## 2. Completion semantics

Use these states for every audit item:

| State | Meaning |
| --- | --- |
| COMPLETE | Repository-side implementation, regression coverage, active documentation, examples, and cleanup satisfy the requirement. |
| PARTIAL | Useful implementation exists, but at least one required behavior, integration, test, or cleanup step remains repository-side. |
| BLOCKED_EXTERNAL | All repository-side work is complete and only real external evidence, inventory, credentials, qualification, approval, commissioning, or change authority remains. |
| NOT_STARTED | No material implementation exists. |
| INVALID | Current behavior contradicts the master prompt or a fail-closed architecture rule and must be corrected before completion. |

Do not relabel repository-side work as BLOCKED_EXTERNAL merely because live infrastructure is unavailable. Implement the complete repository boundary, schemas, handoffs, plan bindings, tests, refusal behavior, and evidence contracts first.

## 3. Current overall assessment

The portable planning architecture is substantially implemented:

- one portable WorkloadSecurityDomain request contract exists;
- schema, profile resolution, semantic policy, placement, allocation planning, desired-state generation, and compilation are real code;
- the existing hosting-wsd-environment/1 and tools/compile_wsd.py path is reused;
- Nutanix, VMware/NSX, and OpenStack realization paths exist;
- Terraform and Ansible catalogs exist;
- five golden reference requests exist;
- current documentation clearly identifies the portable front end;
- unsupported public, IPv6-only, dual-stack, GPU, higher-assurance, and similar extensions are explicitly deferred rather than silently claimed;
- native qualification, production authorization, and fixture-vs-authoritative distinctions are generally documented honestly.

The refactor is not complete because several remaining defects break the integrity chain between eligibility, placement, approval, authoritative allocation, the existing delivery runner, generation-aware execution, and final verification.

The highest priority is to finish the vertical path rather than add new capabilities.

## 4. Ordered completion gates

### GATE-C01 — Native qualification must gate placement

Severity: P0  
State at baseline: INVALID  
State: COMPLETE

Affected master-prompt requirements include R7, sections 21-23, 40, 62, 63, 76, 77, 88, 91, 99, and 100.

#### Current problem

provisioner/placement/resolver.py calls provisioner.placement.eligibility.gate() for each platform and records platform_blockers, but those blockers do not participate in the blockers used to calculate CandidateEvaluation.eligible.

As a result, a candidate can be marked eligible and an AUTHORITATIVE inventory can produce PLACED while the capability registry simultaneously says the platform family has no selected or natively qualified product tuple.

The current placement regressions explicitly prove both conditions:

- authoritative inventory can place;
- every current platform registry gate is unqualified.

Those conditions must not both be accepted as a production-capable placement decision.

#### Required implementation

1. Make platform-family/native-qualification blockers mandatory placement blockers.
2. Preserve the distinction between:
   - platform capability not implemented;
   - capability implemented but product tuple unselected;
   - product tuple selected but native qualification absent or stale;
   - cell-local capability absent.
3. Ensure explicit platform selection does not bypass mandatory qualification.
4. Ensure platform:auto evaluates all candidates and rejects every unqualified platform.
5. Preserve rejected-candidate reasons in the placement artifact.
6. Do not turn fixture inventory into placement authority.
7. Do not invent qualification to make golden tests pass.

#### Required regressions

Add tests proving:

- authoritative inventory + unqualified platform -> hold, never PLACED;
- explicit unqualified platform -> hold;
- platform:auto skips an unqualified candidate when another qualified candidate exists;
- platform:auto holds when all candidates are unqualified;
- cell capability failure remains distinguishable from platform qualification failure;
- fixture inventory remains non-authoritative even when its synthetic capability shape is compatible;
- selected product tuple and qualification identity are recorded in the placement decision.

#### Completion evidence

- no placement result can be authorized when mandatory platform qualification fails;
- placement tests cover both qualified and unqualified registries through controlled fixtures or injected registry data;
- docs/provisioning/placement-model.md describes the actual fail-closed behavior;
- docs/NEXT_WORK.md contains only the external act of selecting/qualifying real tuples, not repository-side placement gating work.

#### Completion record

Qualification is now a mandatory placement blocker and a decision is authorized only when the qualification source is authoritative.

| Requirement | Where it is satisfied |
| --- | --- |
| 1. mandatory blockers | `resolver._candidate()` adds `BLOCKER_QUALIFICATION`; `CandidateEvaluation.eligible` is `not blockers` |
| 2. four-way distinction | `check_platform_capabilities.eligible()` emits `product_tuple:UNSELECTED`, `capability:<id>:NOT_IMPLEMENTED`, `capability:<id>:NOT_NATIVE_QUALIFIED`, `product_tuple:<tuple>:NOT_NATIVE_QUALIFIED`, plus `assurance_profile:<name>` and cell-local `cell_blockers` |
| 3. explicit selection cannot bypass | an explicitly preferred platform still has to clear the same blocker set |
| 4. `platform:auto` rejects unqualified candidates | every candidate is evaluated; an unqualified candidate cannot be eligible |
| 5. rejected reasons preserved | `CandidateEvaluation.blocker_classes`/`qualification_blockers`/`cell_blockers` are serialized into the placement artifact |
| 6. fixtures stay non-authoritative | `DeclaredQualification.authoritative` is always `False`; `place()` raises when an authoritative inventory meets a non-authoritative source; `PlacementDecision.authorized` requires `qualification_identity['authoritative']` |
| 7. no invented qualification | `sources/capabilities/platform_registry.json` is unchanged and still qualifies nothing; the external `native-qualification` conformance check stays `PENDING_EXTERNAL_EVIDENCE` |

New behaviour is fail-closed: `HOLD_PLATFORM_NOT_QUALIFIED` joins `HOLD_PRIORITY` after the specific per-candidate capability hold, an unrecorded qualification is explicit (`UNRECORDED_QUALIFICATION`) rather than an empty object, and a non-authoritative decision carries the limit "Native qualification is absent; this decision rests on a declared qualification assumption".

Regressions: `tests/provisioning/placement/test_placement.py` (qualified and unqualified sources, authoritative/declared refusal), `tests/provisioning/schema/test_schema.py` (unrecorded and declared qualification never authorize), `tests/provisioning/compiler/test_cross_platform.py`, `tests/test_platform_capabilities.py`. `python -m pytest tests/provisioning -q` reports 253 passed / 515 subtests, and `scripts/check_repository.py`, `scripts/check_documentation.py`, and `scripts/check_retired_interfaces.py` pass. The reviewed corpus in `examples/` was regenerated to match; `plan_digest` is unchanged.

---

### GATE-C02 — Multi-zone placement must produce one coherent realization envelope

Severity: P0/P1  
State at baseline: INVALID

Affected requirements include R7, R11, R13, sections 21-24, 41, 63, 71, 76, 88, 91, and 100.

#### Current problem

Placement ranks OZ and RZ candidates independently. The first selected zone sets the top-level site_key and platform, while later zones can select a cluster from another site or platform.

provisioner/compiler/desired_state.py then assumes every selected cluster belongs to the single top-level selected site. This can fail late with INVENTORY_INCOMPLETE or, if identifiers collide across sites, resolve the wrong cluster.

The current hosting-wsd-environment/1 contract is a single-site/single-platform environment contract. Placement must therefore choose a coherent candidate set compatible with that contract.

#### Required implementation

1. Define the atomic placement envelope used by the current environment contract.
2. Evaluate complete WSD candidate sets rather than selecting each zone independently across unrelated sites/platforms.
3. A valid envelope must satisfy every required zone and mandatory constraint within the permitted site/platform boundary.
4. If multiple cells inside one site are permitted, represent the zone-to-cell choice explicitly while keeping the site/platform coherent.
5. If cross-site recovery is intentionally separate from the primary environment, model it as recovery placement, not as a second primary-zone candidate hidden inside the same top-level site.
6. Fail before desired-state compilation if no coherent envelope exists.
7. Make cluster identity unambiguous within the selected inventory scope.

#### Required regressions

Add tests for:

- two sites with asymmetric OZ/RZ scores;
- two platforms under platform:auto;
- one site capable of OZ only and another site capable of RZ only;
- duplicate cluster IDs in different sites;
- same-site multi-cell placement when allowed;
- explicit site pin;
- explicit cell pin;
- recovery placement that is intentionally separate from primary placement;
- deterministic tie-breaking between two fully valid envelopes.

#### Completion evidence

- desired-state assembly never has to repair or reinterpret an incoherent placement;
- one placement artifact completely describes the selected site/platform envelope and per-zone cell/cluster choices;
- no late INVENTORY_INCOMPLETE can be caused by a placement decision that was reported as PLACED.

---

### GATE-C03 — Approved-plan identity must bind the complete reviewed decision

Severity: P0  
State at baseline: INVALID

Affected requirements include sections 25-32, 60, 71, 76, 79, 88, 91, 99, and 104.

#### Current problem

Plan.digest currently binds only:

    request digest + rendered environment document

The complete Plan contains additional reviewed facts, including policy outcome, resolved profiles, placement decision, reservation proposals, service bindings, Terraform scopes, Ansible scopes, delivery operations, conformance state, and warnings.

Some of those facts can change without changing the rendered environment. An approval that cites only the current Plan.digest can therefore fail to bind the full decision a reviewer saw.

#### Required implementation

Create a canonical immutable reviewed-plan identity that binds, at minimum:

- request digest;
- normalized request identity where distinct;
- resolved profile identifiers and versions;
- profile-catalog digest or equivalent version set;
- policy/rule-set digest and result;
- inventory snapshot/reference digest;
- selected product tuple and qualification reference;
- placement decision digest;
- capacity/reservation intent digest;
- IPAM/address intent digest;
- service-binding digest;
- desired-state digest;
- environment digest;
- compiled input digests;
- Terraform scope/root/state-key bindings;
- Ansible scope bindings;
- delivery graph digest;
- generation;
- source commit or equivalent immutable source identity;
- any approval-relevant disruptive/destructive classification.

The approved digest must be computed over the canonical reviewed-plan manifest, not over a partial projection.

Do not include volatile timestamps in the deterministic identity unless they are part of an authority record whose semantics require them.

#### Required regressions

Prove the approved digest changes when any approval-relevant field changes, including:

- capacity reservation target or committed-after values;
- service endpoint or binding class;
- placement;
- profile version;
- policy rule version;
- inventory snapshot;
- compiled input;
- Terraform state key/root;
- generation;
- delivery graph.

Prove semantically identical requests with irrelevant whitespace/order differences remain deterministic.

#### Completion evidence

hosting apply --approved-plan can prove that the external approval cites exactly the complete plan that would be executed or handed to an execution owner.

---

### GATE-C04 — Introduce a real monotonic WSD generation model

Severity: P1  
State at baseline: PARTIAL

Affected requirements include sections 26, 29-32, 33, 35, 37, 60, 79-82, 85, 88, and 91.

#### Current problem

The portable provisioner has stable request and artifact digests but no first-class monotonic WSD generation in the desired state and reviewed plan.

The existing delivery runner already requires generation and operation_id. The two models must be joined.

#### Required implementation

1. Define stable WSD identity: tenant + WSD name, with any required environment identity.
2. Define monotonic desired-state generation semantics.
3. Same desired-state digest for the same accepted generation must be replay-safe and must not create duplicate external operations.
4. Changed desired state must require a new generation.
5. A newer generation must supersede an older unfinished operation according to existing delivery/reconciliation rules.
6. Bind generation into:
   - desired state;
   - reviewed plan;
   - delivery plan;
   - owner operations;
   - observations;
   - conformance/evidence.
7. Do not invent a local filesystem counter as production authority. Use an interface/record suitable for authoritative storage and use fixtures/mocks for repository tests.

#### Required regressions

- same generation + same digest -> replay-safe;
- same generation + changed desired state -> refused;
- newer generation supersedes older plan;
- stale observation from an earlier generation does not satisfy current conformance;
- external operation receipts are generation-bound;
- concurrent generation claims cannot both become current.

---

### GATE-C05 — Integrate the portable plan with the existing hosting-delivery/1 runner

Severity: P0/P1  
State at baseline: PARTIAL

Affected requirements include R16, sections 27-32, 44, 47, 60, 61, 69, 79, 88, 91, 99, 104, and the final instruction to reuse existing mature mechanisms.

#### Current problem

provisioner/execution/delivery.py creates a useful owner-operation summary, but it is not the existing execution graph accepted by tools/delivery_run.py.

The existing runner already implements important behavior the master prompt explicitly said to preserve:

- immutable source binding;
- operation_id;
- generation;
- topologically ordered steps;
- explicit execution opt-in;
- durable execution journal;
- exact dependency receipts;
- restart/resume;
- uncertain-operation recovery;
- containment integration;
- owner-specific typed packets.

The new CLI currently stops at EXECUTION_REFUSED_REPOSITORY_PLAN_ONLY instead of compiling the reviewed portable plan into this established delivery contract.

#### Required implementation

1. Treat tools/delivery_run.py and its typed delivery-step machinery as the execution engine unless repository evidence demonstrates a justified replacement.
2. Add a deterministic compiler from the reviewed provisioning plan to hosting-delivery/1.
3. Map portable-plan responsibilities to the existing typed steps rather than adding a parallel generic runner.
4. Bind every generated step to:
   - reviewed plan digest;
   - source commit;
   - operation_id;
   - generation;
   - exact scope;
   - predecessor receipts.
5. Reuse the existing Terraform prepare/apply, WSD handoff, guest, capacity, IPAM, DNS, acceptance, containment, and reconciliation mechanisms where they own the responsibility.
6. Keep actual execution behind existing explicit authority and execute opt-in.
7. hosting apply may remain incapable of silently contacting infrastructure, but it must be able to produce or invoke the exact established execution handoff once the required external authority records are supplied.
8. Do not create a second journal, second Terraform runner, or second uncertain-mutation recovery model.

#### Required regressions

- portable plan -> deterministic hosting-delivery/1;
- generated graph validates with tools.delivery_run.validate;
- source commit, scope, generation and operation ID are bound;
- every external mutation has a typed existing step or an explicitly justified new owner type;
- existing delivery recovery tests continue to pass;
- no provisioning CLI bypass can invoke Terraform or owner mutation without the existing gate;
- approved plan digest mismatch is refused before execution;
- stale generation is refused;
- resumed execution reuses receipts and does not duplicate a completed owner operation.

#### Completion evidence

The current documented path becomes:

    portable request
    -> provisioner
    -> desired state
    -> existing WSD compiler
    -> reviewed immutable plan
    -> hosting-delivery/1
    -> existing delivery runner
    -> owner operations
    -> observation/reconciliation
    -> conformance
    -> separate activation authority

---

### GATE-C06 — Capacity reservation must use the authoritative reservation boundary

Severity: P1  
State at baseline: PARTIAL

Affected requirements include R8, sections 29-32, 61, 69, 76, 88, 91, and 99.

#### Current problem

provisioner/allocations/reservations.py computes a deterministic proposal against reviewed inventory. It correctly states that the proposal does not grant capacity.

That is suitable for planning but is not the authoritative reservation integration required by the master prompt.

#### Required implementation

1. Preserve the pure capacity arithmetic as preflight.
2. Compile a capacity-owner operation using the repository's existing reservation mechanisms and records.
3. Bind the request to the exact commissioned capacity envelope/snapshot used during placement.
4. Require authoritative confirmation before downstream allocation can treat capacity as held.
5. Handle uncertain mutation outcomes through observe/reconcile before retry.
6. Reconcile a confirmed reservation back into plan/execution evidence.
7. Prevent two concurrent WSD operations from consuming the same capacity based only on the same stale snapshot.

#### Required regressions

- proposal is never represented as confirmed reservation;
- authoritative reservation confirmation is digest/generation bound;
- changed capacity envelope invalidates stale reservation preflight;
- lost response does not trigger duplicate reservation;
- conflicting concurrent reservation is refused or reconciled through the authoritative owner.

---

### GATE-C07 — IPAM and DNS must use the authoritative owner lifecycle

Severity: P1  
State at baseline: PARTIAL

Affected requirements include R9, R10, sections 31-32, 37, 61, 69, 76, 79, 88, and 91.

#### Current problem

The provisioner deterministically selects a free prefix from a reviewed inventory snapshot and emits DNS intent. That is good planning behavior, but it is not authoritative uniqueness or confirmation.

The repository already contains NetBox/IPAM, IPAM record, DNS registration, and delivery-step machinery that must remain the mutation authority.

#### Required implementation

1. Keep consumer requests free of CIDRs/provider identifiers.
2. Use the planning allocator only to express intent or a proposed allocation where useful.
3. During controlled execution, call the existing authoritative IPAM owner path.
4. Bind authoritative allocation to:
   - WSD identity;
   - generation;
   - parent capacity reservation;
   - selected site/zone/domain;
   - allocation intent digest.
5. Confirm/observe before using an uncertain result.
6. Generate DNS registration only from confirmed authoritative allocation state.
7. Bind DNS registration to the confirmed allocation and complete normalized DNS intent.
8. Implement retirement release ordering using the existing owner contracts.
9. Never release reusable addressing before dependent DNS/native state is safely withdrawn.

#### Required regressions

- planning prefix is not treated as authoritative ownership;
- confirmed IPAM can differ from a proposal without silently changing the approved plan;
- if authoritative allocation is expected to be exact, a mismatch creates reconciliation hold;
- lost IPAM/DNS reply is reconciled, not duplicated;
- DNS cannot be registered before the bound IPAM allocation is confirmed;
- retirement cannot release address ownership before dependent registration/native teardown is complete.

---

### GATE-C08 — Profile catalogs must become versioned policy inputs

Severity: P1  
State at baseline: PARTIAL

Affected requirements include R4, sections 25-26, 40, 58, 71, 74, 75, 88, and 91.

#### Current problem

All ten required profile families exist, but catalog entries do not contain explicit profile versions, defaults, or constraints as required by the master prompt.

Several defaults remain hardcoded in provisioner/compiler/normalize.py, which creates a second source of policy/default truth and makes approval binding weaker.

#### Required implementation

1. Add an explicit versioned profile/catalog model.
2. Represent portable defaults and constraints as reviewed profile/catalog data where they are policy rather than parser mechanics.
3. Keep implementation constants only where they are truly implementation mechanics.
4. Record the exact resolved profile versions in desired state and plan identity.
5. Add schema/loader validation for version/default/constraint fields.
6. Generate or validate the service-profile matrix from the authoritative catalogs.
7. Remove duplicated family/default lists where a single machine-readable source can safely own them.
8. Update request normalization so defaults are derived from the authoritative catalog/environment model where the architecture says they are.

#### Required regressions

- profile version change changes desired-state/plan identity;
- catalog with missing/duplicate/invalid version is refused;
- environment-specific defaults resolve deterministically;
- docs/service-profile matrix cannot drift from catalogs;
- deferred profile remains explicitly refused.

---

### GATE-C09 — Adapter contract must own real realization behavior, not only descriptors

Severity: P1/P2  
State at baseline: PARTIAL

Affected requirements include R13, sections 41, 62-64, 84, 88, 91, and 100.

#### Current problem

The three adapter modules exist and correctly avoid native contact, but they are primarily metadata wrappers around existing compiler field sets and module identities.

The master prompt's adapter boundary expects provider-specific validation and compilation behavior to be clearly owned without duplicating the existing compiler.

#### Required implementation

Do not rewrite mature provider logic merely to fill methods. Instead:

1. Define the exact adapter responsibilities that are missing from generic code.
2. Move only genuinely provider-specific portable-to-native mapping decisions behind the adapters.
3. Keep tools/compile_wsd.py as the existing internal compiler where it is already the right authority.
4. Make generic provisioning code ask the selected adapter for provider-specific realization contracts rather than branch on platform-specific assumptions.
5. Ensure each adapter exposes:
   - capability/qualification validation contract;
   - required native placement inputs;
   - domain/workload phase contract;
   - expected native readback identities;
   - supported/unsupported realization gaps.
6. Keep execution and platform contact outside the adapter if existing owner tools already own it.

#### Required regressions

Contract tests for all three platforms must prove:

- required zones represented;
- placement preserved;
- network intent preserved;
- isolation/security outcome represented;
- service binding preserved;
- recovery intent represented when supported;
- unsupported capability refused;
- provider-specific native fields never leak into the portable request;
- adapter declarations cannot drift from the existing compiler/Terraform modules.

---

### GATE-C10 — Cross-platform golden coverage must include every compatible reference request

Severity: P2  
State at baseline: PARTIAL

Affected requirements include R20, sections 41-44, 64, 71, 88, 93, 99, and 100.

#### Current problem

The five required golden reference requests exist and replay deterministically. Cross-platform golden evidence currently covers only internal-production across Nutanix, VMware, and OpenStack.

#### Required implementation

Create the compatibility matrix:

    reference request x compatible platform fixture

At minimum evaluate:

- internal-development;
- internal-production;
- multi-tier;
- recovery-enabled;
- storage-heavy;

against Nutanix, VMware/NSX, and OpenStack wherever the implemented profile set is compatible.

If a scenario is intentionally incompatible with one platform, store and test the explicit refusal rather than omitting it.

#### Required regressions

For each matrix cell:

- same portable semantics;
- deterministic request/profile/placement/desired-state/environment/plan digests;
- expected provider-native realization root;
- no provider-native fields in input;
- expected realization gaps explicitly recorded;
- no fixture claims native contact or production authority.

---

### GATE-C11 — Fix dependency-direction enforcement and remove CLI command coupling

Severity: P1/P2  
State at baseline: INVALID

Affected requirements include sections 46-47, 66-68, 75, 88, 91, 93, and 104.

#### Current problem

tests/provisioning/unit/test_architecture.py contains an unreachable assertion in test_a_cli_command_imports_no_other_command: code after continue cannot run.

Several CLI command modules import provisioner.cli.plan as a reusable service. That contradicts the architecture statement that commands do not import one another.

#### Required implementation

1. Fix the unreachable regression first so the intended rule actually runs.
2. Move shared plan construction/read operations into reusable non-CLI modules.
3. Make validate/resolve/plan/apply/status/verify/evidence thin transports over the same core services.
4. Ensure command modules do not import another command module.
5. Preserve the module entry point python -m provisioner.cli.

#### Required regressions

- AST dependency test actually executes its assertions;
- mutation test or controlled fixture proves a command-to-command import would fail;
- no source outside CLI imports the transport;
- no CLI command imports another CLI command;
- tools/compile_wsd.py remains independent of provisioner.

---

### GATE-C12 — Conformance language must distinguish proposals from confirmed owner state

Severity: P1/P2  
State at baseline: PARTIAL

Affected requirements include sections 38-40, 69, 76, 81, 86-88, and 91.

#### Current problem

The conformance layer generally does the right thing by keeping capacity-confirmation, address-confirmation, service-acceptance, native observation, qualification, and production authorization pending.

However repository checks use wording such as "Capacity was reserved against reviewed inventory" while the reservation object explicitly says it is only a proposal and grants no capacity.

This can mislead reviewers even if the overall report remains blocked.

#### Required implementation

1. Rename repository-side checks to describe what is actually proven:
   - capacity preflight/proposal;
   - address allocation intent/proposal;
   - service binding resolution.
2. Keep owner confirmation as separate mandatory external evidence.
3. Ensure conformance output never uses "reserved", "allocated", "registered", "accepted", "observed", "qualified", or "authorized" for repository-only proposals unless the corresponding authoritative evidence exists.
4. Bind external evidence to plan digest and generation before it can satisfy a check.
5. Make stale/wrong-generation evidence remain pending or fail.

#### Required regressions

- proposal-only plan cannot produce wording or status equivalent to confirmed ownership;
- wrong plan/generation external record does not satisfy conformance;
- missing observation never becomes PASS;
- required unknown evidence blocks activation.

---

### GATE-C13 — Final documentation, backlog, and retired-path cleanup

Severity: P1  
State at baseline: PARTIAL

Affected requirements include sections 9-16, 45, 51, 54-59, 74-75, 86, 88-96, 101, 103, 105, and 107.

#### Required implementation

After the code changes above:

1. Update authoritative active documents instead of adding parallel narratives.
2. Keep docs/deepseek-master-refactor-provisioning-prompt.md as the governing specification.
3. Keep this audit current until all repository-side gates are complete.
4. Update:
   - README.md;
   - docs/README.md;
   - docs/provisioning/*;
   - docs/architecture and engineering indexes where needed;
   - docs/implementation indexes;
   - docs/NEXT_WORK.md;
   - examples/README.md;
   - Terraform/Ansible READMEs if their active contract changes.
5. Remove completed repository-side work from NEXT_WORK and implementation backlogs.
6. Preserve genuinely external blockers.
7. Update provisioner/retired_interfaces.json when an interface/path/schema/command is retired.
8. Search all active code/docs/tests/examples for stale path, schema, CLI, terminology, and implementation references.
9. Delete obsolete active code, tests, examples, and compatibility paths after callers migrate.
10. Do not leave temporary migration aliases unless an explicit compatibility requirement and exit plan exist.

#### Required final stale-term audit

Classify meaningful occurrences of:

    TODO
    FIXME
    TBD
    legacy
    deprecated
    compat
    compatibility
    obsolete
    superseded
    old
    previous
    temporary
    migration
    shim
    fallback

as CURRENT_REQUIRED, HISTORICAL_ONLY, TEMPORARY_WITH_EXIT_PLAN, or OBSOLETE_REMOVE.

Resolve every OBSOLETE_REMOVE before completion.

## 5. Required implementation order

Use this dependency order unless repository evidence proves a safer order:

1. Add failing regression for C01 and fix native-qualification placement gating.
2. Add failing regressions for C02 and fix coherent multi-zone placement.
3. Fix C11 dependency-direction test and CLI command coupling.
4. Implement C08 versioned profiles/default ownership.
5. Implement C04 generation model.
6. Implement C03 complete reviewed-plan manifest/digest.
7. Implement C05 compiler to existing hosting-delivery/1.
8. Integrate C06 capacity authority.
9. Integrate C07 IPAM/DNS authority.
10. Complete C09 adapter responsibilities only where real provider-specific behavior belongs.
11. Complete generation-bound observation/reconciliation and C12 conformance semantics.
12. Expand C10 golden cross-platform matrix.
13. Perform C13 documentation/backlog/retired-path cleanup.
14. Run the final repository audit from sections 88-96 of the master prompt.

Do not start advanced profile expansion before this sequence is complete.

## 6. Commit discipline

Use small coherent commits. Examples:

    test(placement): expose qualification bypass
    fix(placement): reject unqualified platform candidates
    test(placement): expose incoherent multi-zone selection
    fix(placement): select coherent site platform envelope
    test(architecture): enforce command dependency direction
    refactor(cli): move shared plan service below transport
    feat(profiles): add versioned profile metadata
    refactor(profiles): derive portable defaults from catalogs
    feat(lifecycle): bind WSD generation to desired state
    feat(plan): bind complete reviewed manifest digest
    feat(delivery): compile provisioning plan to hosting-delivery graph
    feat(capacity): hand reservation intent to authoritative owner
    feat(ipam): bind authoritative allocation lifecycle
    feat(dns): bind registration to confirmed allocation
    test(golden): cover every request platform matrix cell
    docs(provisioning): update completed execution path
    chore(cleanup): retire superseded provisioning interfaces

Before every commit:

- run the smallest relevant tests;
- inspect the diff;
- update active docs when behavior changed;
- update examples when interfaces changed;
- migrate active callers;
- remove superseded implementation when safe;
- verify no credential/secret/live state entered the repository.

After every few commits, rerun broader tests and rescan for the old path.

## 7. Required test and quality gates

Before declaring repository-side completion, pass all applicable existing and new gates.

### Python and contract

- complete unittest discovery through tools/check_local.py or the repository's current canonical test command;
- provisioning schema tests;
- profile/policy tests;
- placement tests;
- compiler tests;
- adapter contract tests;
- delivery integration tests;
- generation/idempotence/concurrency tests;
- reconciliation/conformance tests;
- documentation/retired-interface tests;
- full golden replay.

### Terraform

Preserve and pass the existing Terraform gates:

- dependency lock review;
- terraform fmt/validate as implemented by repository tooling;
- module/root validation;
- plan-only provider mocks;
- saved-plan execution lab;
- stale-state rejection;
- private artifact permission tests;
- no production infrastructure contact from CI.

### Ansible

Preserve and pass:

- syntax;
- safe local staging;
- check mode where supported;
- idempotence;
- negative cases;
- guest configuration ownership boundaries.

### Repository/documentation

Pass:

- scripts/check_repository.py;
- scripts/check_documentation.py;
- scripts/check_retired_interfaces.py;
- active-link and active-path checks;
- generated/source-of-truth consistency checks.

A local or synthetic PASS never equals native qualification or production authorization.

## 8. External blockers that must remain external

The following may legitimately remain after repository completion:

- actual authoritative site/cell inventory;
- actual selected installed product/API tuples;
- live credentials;
- formal native qualification campaign evidence;
- commissioned capacity envelopes;
- authoritative reservation confirmations;
- authoritative IPAM/DNS confirmations;
- selected security-edge realization;
- production change window;
- production authorization;
- actual native observation;
- recovery exercise evidence;
- operational handover evidence.

For each such blocker, the repository must still contain:

- the input contract;
- validation;
- fail-closed missing/stale behavior;
- generation/digest binding;
- owner boundary;
- reconciliation behavior;
- tests using fixtures/mocks;
- active documentation;
- explicit NEXT_WORK entry if genuinely still pending.

Never fabricate these values or convert fixtures into authority.

## 9. Definition of repository-side completion

Repository-side completion requires all of the following:

### Portable intent

- one active WorkloadSecurityDomain request contract;
- no provider-native IDs in normal consumer fields;
- versioned profiles and deterministic defaults;
- actionable validation diagnostics.

### Placement

- mandatory qualification gates candidate eligibility;
- platform:auto evaluates all eligible qualified candidates;
- one coherent site/platform realization envelope is selected;
- every rejected candidate has a reason;
- fixture placement remains non-authoritative.

### Planning integrity

- one desired-state model;
- monotonic generation;
- immutable reviewed-plan manifest;
- complete digest binding;
- deterministic generated artifacts.

### Execution integration

- portable plan compiles into the existing hosting-delivery/1 graph;
- existing Terraform/Ansible/owner tools remain the execution mechanisms;
- no second execution engine or journal;
- authority remains explicit;
- exact approved plan/generation is applied;
- uncertain mutation observes/reconciles before retry.

### External authorities

- capacity, IPAM, DNS, shared services, backup, identity, edge/security, and production activation preserve their existing owner boundaries;
- proposal is not confirmation;
- external evidence is generation/digest bound.

### Verification

- desired vs observed comparison exists;
- stale/wrong-generation evidence is rejected;
- conformance does not promote unknown evidence;
- activation remains separately authorized.

### Cross-platform

- Nutanix, VMware/NSX, and OpenStack preserve provider-native realization;
- compatible reference requests replay across the full platform matrix;
- differences are explicit rather than silently dropped.

### Documentation and cleanup

- one active provisioning story;
- active docs match current paths;
- NEXT_WORK contains only real remaining work;
- retired interfaces cannot reappear;
- obsolete code/tests/examples/docs are removed or clearly archived;
- final repository, documentation, code-path, stale-path, test, backlog, and commit audits pass.

## 10. Stop conditions

Do not declare this audit complete while any C01-C13 item remains INVALID or PARTIAL for repository-side reasons.

Do not stop because:

- the next task is complicated;
- native infrastructure is unavailable;
- one platform needs different native shapes;
- a migration requires several small commits;
- docs already describe the desired behavior;
- existing tests happen to pass.

When native work is externally blocked, finish the repository-side contract and continue to the next audit gate.

## 11. Final deliverable

When all repository-side gates are complete:

1. update this document so every C01-C13 item is COMPLETE or BLOCKED_EXTERNAL with an explicit external reason;
2. update docs/NEXT_WORK.md to contain only genuine external/native/organizational remaining work;
3. run the master prompt's sections 88-96 final audits;
4. record the exact final commit SHA and validation commands/results;
5. make a final cleanup commit if any obsolete path or stale documentation was found;
6. do not claim native qualification, site commissioning, production authorization, or live infrastructure success without real external evidence.

The final repository should be explainable as:

    declare portable WSD intent
    -> resolve versioned policy and profiles
    -> select a qualified coherent placement
    -> bind authoritative resource intents
    -> compile provider-native realization
    -> bind the complete reviewed plan and generation
    -> execute through existing controlled owner mechanisms
    -> independently observe and reconcile
    -> verify conformance
    -> activate only under separate authority
