# DeepSeek Refactor Completion Execution Prompt

## Mission

Read these files completely before changing code:

1. docs/deepseek-master-refactor-provisioning-prompt.md
2. docs/deepseek-refactor-completion-audit.md
3. README.md
4. docs/README.md
5. docs/provisioning/README.md
6. docs/NEXT_WORK.md
7. the active architecture, engineering, implementation, ADR, Terraform, Ansible, delivery, assurance, and testing documents referenced by those indexes.

Then execute the remaining repository-side refactor to completion.

The master prompt remains the governing specification. The completion audit converts the currently known remaining defects into ordered gates. If repository evidence exposes another repository-side defect required to satisfy the master prompt, fix it too. Do not restrict the work only to defects already listed.

This is an implementation assignment, not a request for another plan.

## Operating mode

Operate as a senior platform/infrastructure engineer completing an in-progress architectural refactor.

Use this loop continuously:

    inspect
    -> reproduce the defect with a focused regression where practical
    -> understand current ownership and existing mature mechanisms
    -> implement the smallest coherent correction
    -> run focused tests
    -> update active documentation/examples
    -> migrate callers
    -> delete superseded implementation
    -> inspect diff
    -> commit
    -> run broader validation periodically
    -> rescan
    -> continue

Do not stop after:

- summarizing the audit;
- writing a new plan;
- adding TODOs;
- adding interfaces without behavior;
- adding compatibility shims instead of migrating callers;
- making only documentation changes for a code defect;
- making only code changes while active documentation becomes false;
- fixing one platform and leaving the portable path inconsistent on the other two;
- passing fixtures while a fail-closed production boundary is still wrong;
- identifying an external blocker when repository-side contracts/tests/refusals can still be completed;
- creating a second delivery/orchestration implementation beside the existing one.

Continue until every repository-side item in docs/deepseek-refactor-completion-audit.md is COMPLETE and the remaining items are genuinely BLOCKED_EXTERNAL.

Do not repeatedly ask for confirmation. Use the existing active documentation and ADRs to resolve decisions. Where the repository leaves a small implementation choice open, make the safest reasonable choice consistent with current architecture.

## Non-negotiable rules

### 1. Preserve architecture-first ownership

The repository's infrastructure/reference architecture remains authoritative over tooling convenience.

Portable intent, resolved desired state, platform realization, execution, observation, reconciliation, conformance, and authorization are different responsibilities. Do not collapse them.

### 2. Reuse mature mechanisms

Before implementing a new mechanism, inspect the existing implementation.

In particular, reuse and integrate where applicable:

- tools/compile_wsd.py
- tools/wsd_handoff.py
- tools/delivery_run.py
- tools/delivery_steps.py
- tools/execution_journal.py
- tools/terraform_run.py
- tools/terraform_apply.py
- existing capacity/reservation machinery
- existing IPAM/NetBox machinery
- existing DNS lifecycle machinery
- existing guest execution machinery
- existing native observers
- existing reconciliation/recovery/fencing mechanisms
- existing containment mechanisms
- existing Terraform compositions/modules/stacks
- existing Ansible roles/playbooks
- existing qualification/assurance gates

Do not replace mature mechanisms simply because the new provisioner package exists.

### 3. Migrate, verify, delete

When a new path supersedes an old path:

    migrate all active callers
    -> update tests/examples/docs
    -> verify the new path
    -> delete the superseded active path
    -> register retired interfaces where appropriate

Do not leave two current-facing implementations indefinitely.

### 4. Do not fabricate authority

Never invent:

- production inventory;
- selected product/API tuple;
- capacity confirmation;
- IPAM allocation confirmation;
- DNS registration confirmation;
- credentials;
- formal qualification evidence;
- native observations;
- recovery evidence;
- site commissioning;
- production authorization;
- live success results.

Fixtures and mocks prove repository behavior only.

### 5. No live infrastructure changes

Complete repository-side implementation, tests, schemas, owner handoffs, and refusal behavior without contacting or mutating live infrastructure.

Do not weaken a gate merely to make an offline test pass.

### 6. Fail closed

Unknown, stale, mismatched, unqualified, unauthorized, or uncertain state must hold or refuse according to the existing architecture.

A timeout does not mean a mutation failed.

Use:

    hold
    -> observe
    -> reconcile
    -> decide

Never blindly retry an uncertain external mutation.

### 7. Small commits

Make small, coherent commits throughout.

Each commit should do one understandable thing and include related tests/docs where behavior changes.

Do not create one giant completion commit.

## Required execution order

Work in the following order unless direct repository evidence shows a prerequisite that must move earlier.

---

## Phase 1 — Fix native-qualification placement gating

Target audit gate: C01.

First add or strengthen a regression that demonstrates the current contradiction:

- capability registry reports platform unqualified;
- authoritative inventory otherwise matches;
- placement incorrectly returns PLACED.

Then fix placement so platform-level qualification blockers are mandatory candidate blockers.

Requirements:

- platform:auto rejects unqualified candidates;
- explicit platform selection also rejects unqualified candidates;
- cell-local capability blockers remain separate from platform-family qualification blockers;
- rejected-candidate reasons remain complete;
- fixture inventory remains non-authoritative;
- do not populate fake product tuples.

Run focused placement tests after each coherent change.

Suggested commit sequence:

    test(placement): expose native qualification bypass
    fix(placement): reject unqualified platform candidates
    docs(placement): document qualification as mandatory eligibility

Do not move to Phase 2 while authoritative placement can be PLACED on a registry-unqualified platform.

---

## Phase 2 — Fix coherent multi-zone placement

Target audit gate: C02.

Add tests with multiple sites/platforms before changing the algorithm.

The current hosting-wsd-environment/1 contract is one site/platform realization. The selected primary WSD placement must therefore be a coherent envelope.

Implement candidate-set evaluation so all required primary zones are satisfiable inside the selected realization envelope.

Do not independently select OZ from one site/platform and RZ from another and then hide that mismatch behind one top-level site.

Model intentionally separate recovery placement separately from primary placement.

Required tests:

- asymmetric OZ/RZ scores across two sites;
- different platforms under auto;
- OZ-only site + RZ-only site must not combine into a fake valid primary environment;
- duplicate cluster IDs in different sites;
- same-site multi-cell placement if allowed;
- deterministic tie break between two complete valid envelopes;
- explicit site/cell pins.

Suggested commits:

    test(placement): expose cross-site zone selection
    fix(placement): select coherent realization envelope
    test(placement): cover multi-site and duplicate cluster identities
    docs(placement): document envelope selection

---

## Phase 3 — Repair dependency direction and CLI layering

Target audit gate: C11.

Fix tests/provisioning/unit/test_architecture.py so test_a_cli_command_imports_no_other_command actually executes its assertion. Code after continue must not remain unreachable.

Then remove CLI command-to-command imports.

Move shared plan construction and read-only projection logic into reusable non-CLI services. CLI modules must remain transports.

Desired direction:

    core/domain/services/execution
        ^
        |
      CLI transport

Not:

    apply -> CLI plan command
    status -> CLI plan command
    verify -> CLI plan command
    evidence -> CLI plan command

Preserve:

    python -m provisioner.cli ...

Required tests:

- command-to-command import fails architecture test;
- no source outside CLI imports the transport;
- tools/compile_wsd.py does not import provisioner;
- architecture test contains no unreachable assertion.

Suggested commits:

    test(architecture): make CLI dependency assertion effective
    refactor(cli): move shared plan service below transport
    test(cli): enforce transport-only command modules
    docs(provisioning): update dependency direction

---

## Phase 4 — Make profiles versioned authoritative policy inputs

Target audit gate: C08.

Do not merely add a version field and leave defaults duplicated in Python.

Implement a coherent versioned catalog model.

Each resolved profile must expose an exact version. Add defaults/constraints to catalog data where they are policy. Parser-only defaults may remain code only when they are genuinely syntax mechanics.

Requirements:

- all ten profile families remain present;
- catalog loader validates versions;
- duplicate/invalid versions fail;
- resolved state records exact versions;
- environment-specific defaults are derived from authoritative catalog data where documented;
- profile version set contributes to reviewed-plan identity later;
- support matrix remains generated from or mechanically checked against catalogs;
- remove duplicated family/default truth where safe.

Pay special attention to current hardcoded normalization defaults for assurance, network, compute, storage, recovery, services, exposure, and zones. Decide which are global parser defaults versus environment/profile policy and encode them consistently.

Suggested commits:

    feat(profiles): add versioned catalog contract
    refactor(profiles): derive policy defaults from catalogs
    test(profiles): bind resolved versions and constraints
    docs(profiles): document versioned default resolution
    chore(cleanup): remove duplicated profile truth

---

## Phase 5 — Introduce monotonic WSD generation

Target audit gate: C04.

Integrate the portable model with the generation semantics already expected by the delivery runner.

Do not implement a production counter in a local file.

Define the repository contract for authoritative current-generation storage and use test fixtures/mocks.

Bind generation into:

- desired state;
- reviewed plan;
- delivery graph;
- owner operations;
- observations;
- reconciliation;
- conformance/evidence.

Required behavior:

- same WSD + same generation + same desired-state digest is replay-safe;
- same generation + different desired state is refused;
- new desired state requires a newer generation;
- newer generation supersedes older unfinished work under existing reconciliation rules;
- stale observation cannot satisfy current generation;
- concurrent current-generation claims cannot both be accepted.

Suggested commits:

    feat(lifecycle): add WSD generation model
    test(lifecycle): enforce generation replay invariants
    feat(observation): bind native evidence to generation
    docs(lifecycle): document generation authority boundary

---

## Phase 6 — Bind approval to the complete reviewed plan

Target audit gate: C03.

Replace the current partial Plan.digest semantics with an immutable reviewed-plan manifest.

The plan identity must bind all approval-relevant facts.

At minimum bind:

- request digest;
- normalized request identity where useful;
- profile versions/catalog version set;
- policy/rule-set digest;
- inventory snapshot digest/reference;
- selected platform product tuple/qualification reference;
- placement digest;
- capacity/reservation intent;
- IPAM/address intent;
- service bindings;
- desired-state digest;
- environment digest;
- compiled artifact digests;
- Terraform roots/state keys/scopes;
- Ansible scopes;
- delivery graph;
- generation;
- immutable source commit;
- disruptive/destructive classification where applicable.

Keep canonical deterministic serialization.

The plan approval check must cite this complete reviewed identity.

Required tests mutate one approval-relevant element at a time and prove the approved digest changes.

Whitespace/order-only request changes must remain deterministic when semantics are unchanged.

Suggested commits:

    feat(plan): add canonical reviewed-plan manifest
    test(plan): bind approval-relevant fields
    refactor(authority): approve exact manifest digest
    docs(plan): document immutable approval identity

---

## Phase 7 — Compile the portable plan into the existing delivery runner

Target audit gate: C05.

This is a major integration phase. Do not create another execution engine.

Inspect tools/delivery_run.py and tools/delivery_steps.py deeply before implementation.

Create a deterministic compiler from the reviewed provisioning plan into hosting-delivery/1.

The result must include:

- source_commit;
- operation_id;
- generation;
- exact WSD scope;
- topologically ordered typed steps;
- explicit dependencies.

Map responsibilities to existing typed step kinds wherever possible.

Reuse existing owner behavior for:

- Terraform plan/apply;
- WSD domain/workload handoff;
- capacity;
- IPAM;
- DNS;
- guest plan/apply;
- acceptance;
- containment;
- platform transition;
- operations/recovery steps where applicable.

Only add a new step kind when no existing owner type can correctly express a required responsibility. If a new kind is necessary, implement its full validation, authority boundary, recovery semantics, tests, and documentation in the same slice.

hosting apply must not bypass existing execution authority. It may:

- emit the exact prepared hosting-delivery/1 handoff; or
- invoke the existing delivery runner only when all existing external authority inputs and explicit execute controls are supplied.

It must not run a private alternate Terraform/apply path.

Required tests:

- generated graph passes tools.delivery_run.validate;
- graph is deterministic;
- source commit/operation ID/generation/scope are exact;
- approved plan mismatch fails before owner execution;
- stale generation fails;
- interrupted run reuses receipts;
- uncertain owner operation reconciles before replay;
- containment remains above routine reconciliation;
- no production native contact occurs in CI.

Suggested commits:

    feat(delivery): compile provisioning plan to hosting-delivery graph
    test(delivery): validate portable graph with existing runner
    feat(cli): hand approved plan to existing delivery boundary
    test(delivery): preserve resume and uncertainty semantics
    docs(delivery): make existing runner the canonical execution path

Do not consider this phase complete if provisioner/execution/delivery.py remains a separate conceptual orchestrator. It may remain as a deterministic graph builder/view, but execution semantics must come from the existing runner.

---

## Phase 8 — Integrate authoritative capacity reservation

Target audit gate: C06.

Keep pure capacity assessment/proposal logic for planning.

Execution must use the existing authoritative capacity/reservation owner boundary.

Requirements:

- reservation intent bound to exact WSD identity/generation/plan;
- exact commissioned envelope/snapshot identity bound;
- confirmation required before dependent authoritative allocation;
- response loss produces reconciliation hold;
- concurrent reservations do not both consume the same stale capacity;
- confirmation is evidence, not inferred from proposal.

Update conformance so repository capacity checks describe preflight/proposal only.

Suggested commits:

    refactor(capacity): separate preflight from authority confirmation
    feat(delivery): bind capacity owner step to reviewed plan
    test(capacity): reconcile uncertain reservation outcomes
    docs(capacity): document proposal versus confirmation

---

## Phase 9 — Integrate authoritative IPAM and DNS lifecycle

Target audit gate: C07.

The portable request must continue to describe network intent, not CIDRs.

Planning may compute or display a deterministic proposal, but authoritative uniqueness belongs to the existing IPAM owner.

During execution:

- reserve/allocate through existing authoritative IPAM path;
- bind allocation to parent reservation, site/zone/domain, generation, and plan;
- observe/reconcile uncertain results;
- generate DNS registration only from confirmed allocation state;
- bind DNS intent completely;
- preserve retirement release order.

If current architecture expects the authoritative owner to choose the actual prefix, handle a difference from the planning proposal explicitly. Do not silently mutate the reviewed plan.

Required tests:

- proposal is not ownership;
- allocation confirmation is required;
- lost reply does not duplicate allocation;
- DNS cannot precede confirmed address ownership;
- DNS registration is generation/plan/allocation bound;
- retirement cannot release address before dependent state is removed.

Suggested commits:

    refactor(ipam): separate proposal from authoritative allocation
    feat(delivery): bind IPAM owner step
    feat(delivery): bind DNS owner step to confirmed allocation
    test(ipam): reconcile uncertain allocation
    test(dns): enforce allocation dependency and retirement ordering
    docs(ipam-dns): document authoritative lifecycle

---

## Phase 10 — Complete adapter responsibilities without duplicating compiler logic

Target audit gate: C09.

Inspect the generic compiler for platform-specific assumptions.

Move only behavior that genuinely belongs to provider realization boundaries.

Each platform adapter should expose a useful contract covering:

- qualification/capability validation;
- native placement-input contract;
- domain phase contract;
- workload phase contract;
- expected native observation identities;
- supported/unsupported realization gaps.

Do not copy compiler field lists into a second source of truth. Continue deriving native shapes from the existing compiler/Terraform configuration where that is authoritative.

Required adapter contract tests must cover Nutanix, VMware/NSX, and OpenStack without assuming identical resource graphs.

Suggested commits:

    refactor(adapters): move provider realization decisions behind contract
    test(adapters): enforce portable outcome parity
    docs(adapters): document provider-native responsibilities

---

## Phase 11 — Complete generation-aware observation, reconciliation, and conformance truthfulness

Target audit gate: C12 plus remaining C04/C05 dependencies.

Audit all status and detail text.

Repository-only evidence must not say:

- reserved;
- allocated;
- registered;
- accepted;
- qualified;
- observed;
- authorized;

when only a proposal, intent, declaration, or fixture exists.

Use exact language such as:

- capacity preflight passed;
- reservation proposed;
- address intent resolved;
- service binding declared;
- external confirmation pending.

Bind external evidence to:

- subject;
- WSD;
- generation;
- reviewed-plan digest;
- expected native identity;
- evidence source/freshness.

Wrong generation or wrong plan evidence must never satisfy conformance.

Keep activation separately authorized.

Suggested commits:

    fix(conformance): distinguish proposals from owner confirmation
    feat(reconciliation): reject stale generation evidence
    test(conformance): bind external evidence to exact plan
    docs(conformance): document evidence authority vocabulary

---

## Phase 12 — Expand cross-platform golden coverage

Target audit gate: C10.

Create a matrix of every reviewed reference request against every compatible platform fixture.

Reference requests:

- internal-development;
- internal-production;
- multi-tier;
- recovery-enabled;
- storage-heavy.

Platforms:

- Nutanix;
- VMware/NSX;
- OpenStack.

For compatible combinations, store deterministic outputs/digests.

For intentionally incompatible combinations, store/test explicit refusal reason rather than omitting the cell.

Golden outputs must avoid timestamps and other brittle values.

Golden fixture success must never claim qualification, placement authority, native contact, or production authorization.

Suggested commits:

    test(golden): expand request platform matrix
    test(golden): record explicit incompatible-platform refusals
    docs(examples): document full portable matrix

---

## Phase 13 — Cleanup and documentation convergence

Target audit gate: C13.

Only after callers have migrated:

- delete obsolete code;
- delete stale tests preserving old behavior;
- delete stale examples;
- archive or remove superseded active docs;
- update retired interface register;
- update all current indexes;
- remove completed items from NEXT_WORK/backlogs.

Do not leave the old path "just in case" unless there is an explicit compatibility requirement with an exit plan.

Run repository-wide searches for:

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

Classify meaningful hits. Remove OBSOLETE_REMOVE. Review every temporary item and ensure it has an explicit exit plan.

Suggested commits:

    docs(provisioning): converge on completed portable execution path
    chore(cleanup): remove superseded provisioning paths
    docs(backlog): retain only genuine external blockers
    test(retired): reject removed interfaces

---

## Phase 14 — Final audits and validation

Run the final audits required by sections 88-96 of docs/deepseek-master-refactor-provisioning-prompt.md.

Trace the actual path, not the intended one:

    request
    -> validation
    -> profiles
    -> policy
    -> qualified coherent placement
    -> authoritative allocation intents
    -> desired state
    -> existing environment compiler
    -> platform realization
    -> immutable reviewed plan + generation
    -> existing delivery runner
    -> owner operations
    -> native observation
    -> reconciliation
    -> conformance
    -> separate activation authority

Verify exactly one intentional active path for each responsibility.

### Required broad validation

Run all applicable existing commands, including the repository's canonical equivalents of:

    python tools/check_local.py
    python scripts/check_repository.py
    python scripts/check_documentation.py
    python scripts/check_retired_interfaces.py
    python scripts/verify_ansible.py
    python tools/verify_terraform.py --mock-tests

Also run the existing Terraform execution/runtime labs and other CI commands affected by the changes where the local environment supports them.

If a CI-only dependency is unavailable locally:

- run everything possible;
- do not claim the unavailable gate passed;
- keep the implementation complete;
- record the exact remaining validation dependency.

Inspect GitHub workflow definitions and update them if new regression groups are not covered by the existing canonical test command.

## Documentation update rules

Do not create a new document for every implementation change.

Prefer updating the active authoritative documents:

- README.md
- docs/README.md
- docs/provisioning/README.md
- docs/provisioning/architecture.md
- docs/provisioning/request-contract.md
- docs/provisioning/profile-model.md
- docs/provisioning/placement-model.md
- docs/provisioning/desired-state-model.md
- docs/provisioning/adapter-contract.md
- docs/provisioning/terraform-boundary.md
- docs/provisioning/service-owner-boundary.md
- docs/provisioning/plan-workflow.md
- docs/provisioning/service-profile-matrix.md
- relevant architecture/engineering/implementation indexes
- docs/NEXT_WORK.md
- examples/README.md
- Terraform/Ansible READMEs when their contract changes
- docs/deepseek-refactor-completion-audit.md as gates close

Do not weaken docs to match an unsafe implementation. Fix the implementation.

## Backlog rules

docs/NEXT_WORK.md must contain only genuine remaining work.

When repository-side work is completed, remove it from the active backlog and keep durable design information in the correct authoritative document.

External blockers may remain, but each must name:

- owner;
- missing external evidence/input;
- why it matters;
- repository-side contract already completed;
- completion condition;
- hold point.

Do not preserve completed work as history in NEXT_WORK. Git is the history.

## Required progress discipline

After every few coherent commits, reassess:

- Which audit gate is now actually complete?
- What old path can now be deleted?
- What documentation became stale?
- What next dependency is shortest?
- Did the last change introduce another source of truth?
- Are fixtures being mistaken for authority?
- Is approval still bound to the exact plan/generation?
- Does uncertainty still reconcile before mutation retry?

Update docs/deepseek-refactor-completion-audit.md only when the evidence supports a status change.

Do not mark a gate COMPLETE merely because its implementation file exists.

## Final completion criteria

Do not finish until:

- C01-C13 have no repository-side INVALID or PARTIAL state;
- all known repository-side defects found during implementation are also resolved;
- the new portable path uses the existing mature compiler and delivery mechanisms rather than parallel replacements;
- qualification gates placement;
- placement is coherent;
- profiles are versioned;
- generation is first class;
- approval binds the complete reviewed plan;
- capacity/IPAM/DNS preserve authoritative owner lifecycle;
- execution uses the existing delivery runner;
- observation and conformance are generation/plan bound;
- the full compatible request/platform golden matrix is tested;
- CLI dependency direction is enforced;
- active documentation matches code;
- obsolete active code/docs/tests/examples are removed;
- NEXT_WORK contains only real external/native/organizational blockers;
- final repository/documentation/code-path/stale-path/test/backlog/commit audits pass;
- git status is clean.

At completion, update docs/deepseek-refactor-completion-audit.md with:

- final status of every gate;
- exact final commit SHA;
- validation commands actually run;
- validation results;
- explicit external blockers still open;
- a statement that no live infrastructure was changed unless there is real separately supplied evidence proving otherwise.

## Final instruction

Begin with C01.

Do not stop at analysis.

Do not replace implementation with another planning document.

Make the failing test, implement the correction, update the docs, commit the coherent slice, and continue through the ordered gates.

When a new path replaces an old one:

    migrate -> verify -> delete

When an external dependency blocks native execution:

    finish the repository-side contract -> record the external boundary -> continue

Continue until the repository-side refactor is complete.
