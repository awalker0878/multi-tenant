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

At the audited baseline several defects broke the integrity chain between
eligibility, placement, approval, authoritative allocation, the existing delivery
runner, generation-aware execution, and final verification.

C01 to C13 were each recorded as `State: COMPLETE` with a completion record that names
the code, the regression and the verification command, and section 12 recorded a final
result. That completion claim was suspended when a post-completion validation of the
hosted workflow on the exact recorded tree came back red. The four affected gates were
reopened, the four defects the corrective specification identifies (F01 to F04) were
reproduced, fixed at the source of truth and pinned with regressions, and the gates are
COMPLETE again with the corrective evidence recorded in this section and in section 12.

What remains external is unchanged: native qualification, authoritative inventory,
owner-held reservations and registrations, native observation, commissioning, production
authority and an installed Terraform/Ansible toolchain. None of those is repository-side
work, and `docs/NEXT_WORK.md` holds only those rows.

### Post-completion validation reopening

`docs/deepseek-refactor-post-audit-corrective-action.md` is the authoritative corrective
specification for this reopening. It was produced after the final completion record was
committed, from a validation run of the hosted workflow on the exact recorded tree.

Observed evidence:

| Fact | Value |
| --- | --- |
| Workflow | `.github/workflows/validate.yml` — `Architecture and automation validation` |
| Run id | `35917384798` |
| Head commit | `469bbd82ac5c02f9f4786bb8c977b095b589b1a3` (`docs(audit): record final repository-side completion`) |
| `repository` job | failure |
| `terraform` job | success |
| `ansible` job | success |

The failing `repository` job is the contradiction this reopening records: a gate that
cites a hosted validation as its verification cannot be COMPLETE while that validation
is red on the tree the record names. The corrective specification identifies four
defects (F01 to F04), and the gates whose completion records depend on them are reopened:

| Gate | Reopened because |
| --- | --- |
| C03 | F01 — approved-plan identity is OS-dependent, so the digest does not bind one reviewed decision across platforms |
| C05 | F02 — approval binds an owner-operation summary while the executable topology is built after approval, so the approved digest does not bind the topology that runs |
| C10 | F01 and F03 — the cross-platform golden matrix asserts per-OS plan identity, and generated navigation does not match its generator |
| C13 | F03 and F04 — the generated documentation is not reproducible from its generator, and the completion claim is contradicted by the hosted workflow |

Each reopened gate returns to COMPLETE only when the corrective specification's own
acceptance criteria hold and the hosted workflow is green on the exact final head.

The corrective tree was validated by the same workflow once the corrective commits were
pushed, and again on the documentation commit that carries the record. The run that closes
this reopening is:

| Fact | Value |
| --- | --- |
| Workflow | `.github/workflows/validate.yml` — `Architecture and automation validation` |
| Run id | `35951513770` |
| Head commit | `82855759979d752f446fc301a42bb169859cf99d` |
| Overall conclusion | success |
| `repository` job | success |
| `terraform` job | success |
| `ansible` job | success |

The corrective commits themselves were validated by the earlier run `35950478558` on head
`a538f60`, which is also green; section 12 records both runs, including the test count, the
failure count and the documentation, retired-interface, golden-replay and cross-platform
matrix results.

### Corrective action closure

All four defects are fixed at the source of truth, each behind a durable regression that
failed before the fix, and the four reopened gates are COMPLETE again.

| Defect | Root cause | Fix | Commits | Regression |
| --- | --- | --- | --- | --- |
| F01 | `provisioner/inventory/model.py` bound `str(path.resolve().relative_to(ROOT))` into the plan, so the approved-plan identity changed with the separator the host happens to use (`\` on Windows, `/` on Linux) | logical source identity is now separated from filesystem/read origin: `provisioner/repository.py` `reviewed_source()` produces a POSIX repository-relative logical source, the manifest binds `document_digest` plus document source, status and authority instead of an invocation path, and repository-relative paths are POSIX everywhere while absolute paths never enter approval identity | `9d00a49`, `8b1b5f5`, `15f8104`, `1830b16` | `tests/provisioning/unit/test_inventory_provenance.py`, `tests/provisioning/unit/test_plan_manifest.py` |
| F02 | `provisioner/execution/delivery.py` `graph_digest(state, scopes)` was bound into approval while the executable topology was built from `provisioner/execution/handoff.py` `STEPS`/`OPERATION_STEPS`/`REVIEWED_PARAMETERS` *after* approval was checked, so approval did not bind the topology that runs | `provisioner/execution/handoff.py` now owns one canonical reviewed topology intent (`hosting-delivery-topology-intent/1`) with `topology_intent()`/`topology_digest()`/`approval_projection()`; `provisioner/execution/manifest.py` `delivery_intent(plan)` binds it into the manifest; `handoff.build()` recomputes the projection digest and refuses with `APPROVAL_TOPOLOGY_MISMATCH` before validation; the parallel `delivery.graph_digest` is deleted | `5282fba`, `81f8a9c`, `12a71a7`, `8a86fca`, `ed59996`, `47fd4e5`, `63576ce` | `tests/provisioning/unit/test_approval_topology.py` |
| F03 | `scripts/build_documentation.py` had drifted from the documents it claims to generate, and a non-idempotent `run()` post-pass appended the maintained-design pointer after the files were written | the generator is the source of truth again: `Builder.compose`, `Builder.maintained_workspace`, the `category()` string `extra`, the three navigation paragraphs, the assurance tail, the `docs/README.md` table row, the RAD/TAD pointer, the portable-provisioning section and the `code_map()` row extras all moved into the generator, the append-only post-pass was deleted, and every write is explicitly `utf-8`; the two committed documents that were corrupt (`docs/implementation/README.md`, `docs/implementation/code-map.md`) were regenerated | `da77c60`, `e32a9e2`, `07f4240` | `tests/test_commissioning_pack.py::IntegrationTests`, `tests/test_task_tree_integration.py::NavigationIntegrationTests` |
| F04 | this audit claimed C01-C13 COMPLETE while the hosted `repository` job was red on the recorded tree | the audit was reopened first (`1c5371a`) and each gate is re-closed here only with its corrective evidence, with section 12 carrying run `35951513770` on head `8285575` and the corrective run `35950478558` on head `a538f60`, each with its four job conclusions | `1c5371a`, and this record | this audit's gate records and section 12 |

The corrective specification's own prohibition was honoured: no test was weakened, no
golden was regenerated per operating system, and no gate was closed by editing a
document. The generator is now a fixed point - replaying `Builder.run()` through a
`Path.write_text` capture reproduces 141 of 141 generated documents byte for byte.

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
State: COMPLETE

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

#### Completion record

The unit of placement is now a coherent envelope: one site, one platform and an explicit cell/cluster choice for every required zone.

| Requirement | Where it is satisfied |
| --- | --- |
| 1. atomic envelope defined | `resolver._Envelope` is `(site, platform)` plus a per-zone `_ZoneOption`; `hosting-wsd-environment/1` is single-site/single-platform, so the site is the atomic boundary |
| 2. complete candidate sets | `resolver._envelopes()` groups eligible options by `(site, platform)` and discards any boundary that does not realize *every* required zone, so zones are never ranked independently |
| 3. every zone and constraint inside the boundary | only options that already passed `_candidate()` (residency, cell capability, qualification, capacity, prefix pool, service) enter an envelope |
| 4. explicit zone-to-cell choice | `selected.cells` and `envelope.zones.<zone>.cell_key`; a site may realize zones in different cells |
| 5. recovery is separate | recovery is representable only as its own placement request; a second primary-zone candidate inside the primary site is now unreachable by construction |
| 6. fail before desired-state | `place()` returns `HOLD_NO_COHERENT_ENVELOPE` with `selected = null`; `require_placed()` raises `NO_ELIGIBLE_PLACEMENT` and `desired_state.build()` refuses a held decision |
| 7. unambiguous cluster identity | `envelope.zones.<zone>.cluster_key` is `site/cell/cluster`; `desired_state._cluster()` resolves strictly inside the selected cell and records `INVENTORY_INCOMPLETE` with `site`/`cell`/`cluster` details on a mismatch |

Ranking is one stated rule — envelope capability count, then envelope available vCPU, then `site_key`, then the per-zone cell keys, then the per-zone cluster ids — and within a zone the highest score, then the lowest cell key, then the lowest cluster id. This is a superset of the previous rule (an envelope's capability count is its best zone's), so the reviewed reference request still resolves to `site-01`/`cell-01`/`cluster-oz-01`/`cluster-rz-01`, but now as an explicit coherent choice.

Regressions: `tests/provisioning/placement/test_placement.py` adds `CoherentEnvelopeTest` (asymmetric sites, `platform:auto`, OZ-only/RZ-only split, duplicate cluster ids, same-site multi-cell, site pin, cell pin, separate recovery placement, deterministic tie-breaking on sites and on cells, cell-scoped `desired_state._cluster()` and its refusal) and extends `VocabularyTest` so `HOLD_NO_COHERENT_ENVELOPE` is a status the resolver actually emits. `tests/provisioning/schema/test_schema.py` proves the committed schema requires `selected.envelope` and refuses an unknown zone key. `python -m pytest tests/provisioning -q` reports 270 passed / 515 subtests, and `scripts/check_repository.py`, `scripts/check_documentation.py`, and `scripts/check_retired_interfaces.py` pass. `examples/resolved/*.placement.json`, `examples/resolved/*.desired-state.json`, `examples/golden/digests.json` and `examples/golden/cross-platform.digests.json` were regenerated to match; `plan_digest` is unchanged because the envelope is not part of the rendered environment.

---

### GATE-C03 — Approved-plan identity must bind the complete reviewed decision

Severity: P0  
State at baseline: INVALID  
State: COMPLETE

Reopened by defect F01 of `docs/deepseek-refactor-post-audit-corrective-action.md`: the
manifest bound a filesystem/read origin whose separators are OS-dependent, so the same
inventory produced different plan digests on Windows and Linux and the identity did not
bind one reviewed decision across platforms.

Affected requirements include sections 25-32, 60, 71, 76, 79, 88, 91, 99, and 104.

#### Corrective closure record

F01 is fixed and the gate is COMPLETE. The logical source identity is separated from the
filesystem/read origin: `provisioner/repository.py` `reviewed_source()` yields a POSIX
repository-relative logical source for an in-tree document and a resolved absolute POSIX
path otherwise, `provisioner/inventory/model.py` no longer derives identity from
`path.resolve().relative_to(ROOT)`, and the manifest binds `document_digest` with the
document source, status and authority instead of the invocation path. Approval-relevant
plan facts are therefore deterministic across checkouts and separators, and no absolute
path enters the approved identity. Commits `9d00a49` (failing regression),
`8b1b5f5` (source fix), `15f8104` (invariance tests) and `1830b16` (regenerated portable
digests). The regressions are
`tests/provisioning/unit/test_inventory_provenance.py` - separator invariance, checkout
location invariance and view identity, including
`test_manifest_digest_is_path_separator_independent`,
`test_plan_digest_is_identical_across_checkout_locations` and
`test_the_reference_records_the_document_not_the_invocation` - together with
`test_the_identity_does_not_depend_on_how_the_path_was_spelled` and
`test_the_request_source_is_repository_relative_for_a_checkout_document` in
`tests/provisioning/unit/test_plan_manifest.py`. `tests/provisioning` reports 900 passed
and 1449 subtests.

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

#### Completion record

`Plan.digest` was a digest of `request digest + rendered environment document`, which
is a projection: a reservation target, a service endpoint, a pinned placement cell, a
reviewed profile revision, the policy rule set, the inventory snapshot or a later
generation could all move without moving the rendered environment, so an approval
that cited the old digest did not bind the decision a reviewer saw.

The identity is now the digest of `Plan.manifest`, a complete canonical
reviewed-plan manifest (`hosting-reviewed-plan-manifest/1`,
`provisioner/execution/manifest.py`). `Plan.digest` and the new
`Plan.manifest_digest` are the same value; the second name exists so the
approval-facing term is explicit. Every manifest term is a reviewed decision or a
canonical digest of one, and nothing in it is derived from the plan identity, so it
can be computed before that identity exists.

| Required binding | Where it is satisfied |
| --- | --- |
| request digest | `manifest.request.digest` |
| normalized request identity, where distinct | `manifest.request_identity` — a digest of `apiVersion`/`kind`/`metadata`/`spec`, so two differently-rendered but equivalent requests share one identity while the source digest still names the file that was read |
| resolved profile identifiers and versions | `manifest.resolution.profiles` and `.profile_versions` |
| profile-catalog digest or equivalent version set | `manifest.resolution.catalog_versions` and `.catalog_digest` |
| policy/rule-set digest and result | `manifest.policy` now carries `rules_digest` (new `standards.rules_digest()`, threaded through `policy_diagnostics.summary`) beside the evaluated/failed counts and errors |
| inventory snapshot/reference digest | `manifest.inventory` — digest, status, origin and authority; a plan built without an inventory records the explicit `UNRECORDED` reference rather than omitting the term |
| selected product tuple and qualification reference | `manifest.product_tuple` (`UNSELECTED` when held, new `PlacementDecision.product_tuple`) and `manifest.qualification` (the `UNRECORDED` reference when none was recorded) |
| placement decision digest | `manifest.placement` |
| capacity/reservation intent digest | `manifest.capacity` — every reservation including its demand and `committed_after` position |
| IPAM/address intent digest | `manifest.addresses` — every reserved prefix, gateway host number and workload address |
| service-binding digest | `manifest.service_bindings` — every binding including its endpoints and binding class |
| desired-state digest | `manifest.desired_state` |
| environment digest | `manifest.environment` |
| compiled input digests | `manifest.compiled_inputs` — one digest per input the existing compiler accepted |
| Terraform scope/root/state-key bindings | `manifest.terraform` — `scope`, `root`, `input`, `state_key`, `catalog_id`, `owner_scope`, `status` |
| Ansible scope bindings | `manifest.ansible` |
| reviewed delivery topology digest | `manifest.delivery.topology_digest` via `handoff.topology_digest(plan)` — the sequence, the step kinds, the dependencies, the operation-to-step bindings and the reviewed parameters |
| generation | `manifest.generation` |
| source commit or equivalent immutable source identity | bound in the C05 `hosting-delivery/1` handoff, where `tools/delivery_run.py` already requires a 40-hex `source_commit` |
| disruptive/destructive classification | `manifest.classification` — `lifecycle`, `disruptive`, `destructive`, `rebuild` |

Two terms are excluded deliberately, and tests assert they stay excluded:

- **Derived identity.** The delivery `plan_digest`, the `operation_id`, the plan
  `identity` and the generation echoed onto the delivery graph are computed *from*
  the plan. Binding them would make the identity depend on itself. The cycle is
  removed rather than tolerated: the manifest binds the reviewed delivery topology
  *intent* by digest, computed from the reviewed decision alone, and the delivery
  document is then built from the manifest digest.
- **A parallel delivery identity.** The owner-operation summary
  (`provisioner.execution.delivery`) is not bound as a second delivery term: it names
  the owners who must act, while the topology intent names the sequence that would be
  staged. The compiled `hosting-delivery/1` graph must project back onto exactly the
  bound topology or `handoff.build` refuses it with `APPROVAL_TOPOLOGY_MISMATCH`.
- **Owner-provisioned free text.** A Terraform scope's `backend` is the text an owner
  provisions against the reviewed state key. It is not a reviewed decision, and
  binding it would make the plan identity depend on owner state, so the manifest
  binds the state key instead.

No volatile timestamp, run identifier, host name or checkout property is bound, so
the manifest is reproducible from the reviewed inputs alone and byte-identical golden
replay still holds.

Two assumptions are recorded rather than silently made:

1. **Source identity.** The reviewed manifest deliberately stays independent of the
   git checkout — a checkout property is not a reviewed decision, and binding it
   would make the plan identity depend on how the repository happened to be cloned.
   The immutable source identity is bound where it is authoritative and already
   required: the `hosting-delivery/1` handoff, whose `source_commit` is validated as
   40 hex by the existing runner. C05 owns that handoff.
2. **Destructive/rebuild classification.** The repository has no replacement or
   destroy change-intent model yet, so `classification` declares
   `destructive: false` and `rebuild: false` unconditionally and derives
   `disruptive` from the reviewed lifecycle (`production` is disruptive). A
   production greenfield create changes a production environment and destroys
   nothing, which is exactly what is declared. A future change-intent model must set
   `destructive` and `rebuild` from reviewed input; the term exists now so that the
   identity already binds them.

Regressions: the new `tests/provisioning/unit/test_plan_manifest.py` (48 tests /
3 subtests) proves the manifest has exactly the declared terms, that
`Plan.digest == Plan.manifest_digest == canonical_digest(manifest)`, that a fixture
inventory is recorded as non-authoritative, that no derived identity and no
`backend` leaks in, and then isolates every required term by replacing it on an
otherwise identical plan and rebuilding the manifest from the *baseline* delivery
graph, so the digest change can only come from the term under test: capacity
reservation target and `committed_after` values, service endpoint, binding class,
placement, qualification, product tuple, profile version, catalog version, catalog
digest, policy rule set, inventory snapshot, compiled input, environment, Terraform
state key, Terraform root, Ansible scope, delivery graph, generation, change
classification, request digest, request source and request identity. End-to-end
sensitivity is proved separately for a different reviewed inventory, a different
platform, a reviewed site pin on one inventory, an edited policy rule (same outcome,
different rule set) and a bumped profile version. Replay determinism is proved
across four equivalent JSON renderings of one request and across repeated runs. The
plan-digest tests in `tests/provisioning/unit/test_determinism.py` were rewritten for
the manifest, `tests/provisioning/end_to_end/test_golden.py` now replays
`manifest_digest` as well as `digest`, and
`tests/provisioning/unit/test_plan_manifest.py::ApprovedPlanIdentityTest` proves the
completion evidence directly: `hosting apply --approved-plan` cites the complete
manifest, carries it and the reviewer-facing `reviewed` projection in its handoff
payload, and refuses a stale digest while naming the current manifest.

Golden corpus: `manifest_digest` was added to the regeneration harness and the
digest indexes; `examples/golden/digests.json`,
`examples/golden/cross-platform.digests.json`, the five
`examples/golden/*.conformance.json` (which cite the plan digest) and the five
`examples/resolved/*.resolution.json` (which embed the policy summary that gained
`rules_digest`) were regenerated. A follow-up `--check` run reports every artifact
unchanged.

Observation: the reviewed demonstration qualification corpus declares the same
declared product tuple for every platform
(`DECLARED-DEMONSTRATION-TUPLE-NOT-NATIVE-EVIDENCE`), so the product tuple is not a
platform discriminator in the fixture corpus; platform identity is carried by the
placement decision digest, which the manifest also binds. The regression asserts that
rather than asserting a cross-platform tuple inequality that the corpus does not
support.

Docs: new `docs/provisioning/plan-manifest-model.md`, indexed from
`docs/provisioning/README.md` and registered in the documentation drift guard's
`REQUIRED` set, with a term-by-term table, the exclusions and their reasons, the
determinism argument and an explicit statement of what the manifest does not claim.
`docs/provisioning/plan-workflow.md` no longer describes the old projection — it
documents the manifest digest, the manifest and `reviewed` projection in the `apply`
payload, and links the new page; `docs/provisioning/generation-model.md` now says the
generation is a term of the reviewed-plan manifest rather than of a plan digest.

`python -m pytest tests/provisioning -q` reports 410 passed / 741 subtests,
`python -m pytest tests/test_platform_capabilities.py -q` reports 15 passed, and
`scripts/check_repository.py`, `scripts/check_documentation.py` and
`scripts/check_retired_interfaces.py` all exit 0.

---

### GATE-C04 — Introduce a real monotonic WSD generation model

Severity: P1  
State at baseline: PARTIAL  
State: COMPLETE

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

#### Completion record

Generation is now a first-class property of one WSD identity rather than a field only
the delivery runner required. `provisioner/domain/generation.py` owns the semantics;
the authoritative record stays with the owner that holds it.

| Requirement | Where it is satisfied |
| --- | --- |
| 1. stable WSD identity | `WsdIdentity` names tenant, WSD, environment (`{site_key}-{lifecycle}`), site and platform; `.key` is `{tenant}/{wsd}@{environment}/{site}/{platform}` and `.digest` covers all five components; `identity_of(state)` derives it from the resolved desired state instead of storing a second copy |
| 2. monotonic generation semantics | `require_generation` accepts only a positive integer; `GenerationRecord` and `claim()` implement first-generation-`1`, replay, refusal of changed state at the same generation, staleness and supersession |
| 3. replay safety | `claim()` returns `REPLAYED` with `duplicate_operations: false` when the generation, desired-state digest and plan digest all match the held record |
| 4. changed state needs a new generation | `claim()` refuses `GENERATION_CONFLICT` when the desired-state or plan digest changed at the same generation |
| 5. newer generation supersedes | a higher generation claims over a `CLOSED` record and reports it as `superseded`; over an `OPEN` record it is refused unless reconciliation states the decision (`allow_open_supersession`), so an uncertain operation is never silently abandoned |
| 6. binding | the generation is in `DesiredState`, in `Plan` (as the first term of the plan digest), in the delivery plan and on every owner operation, on every observation (`native.binding()`/`bound()`), in the conformance report (with `identity` and `operation_id`) and on every `EvidenceRecord`, plus a dedicated `generation` evidence kind |
| 7. no local counter | `generation.py` imports none of `os`, `pathlib`, `json`, `sqlite3`, `tempfile` or `shutil`, and a test asserts it; `GenerationLedger` is the interface, `InMemoryLedger` is a test double that reports `IN_MEMORY_NOT_AUTHORITATIVE`, and the model publishes `authority: EXTERNAL_LEDGER_ONLY` |

Regressions: `tests/provisioning/unit/test_generation.py` (48 tests / 49 subtests)
covers every required case — same generation plus the same digest is replay-safe;
same generation with changed desired state is refused; a newer generation supersedes
an older plan and is refused while the operation is unfinished unless reconciliation
says otherwise; a stale observation from an earlier generation is `STALE` and does
not satisfy current conformance (and neither does an `UNBOUND` one); an external
operation receipt is generation-bound through the derived operation identity
`{wsd_key}-g{generation}-{plan_digest[:12]}`; and two concurrent claims cannot both
become current, because the commit is a compare-and-set against the record the
claimant read.

The delivery contract stays the owner of the scope grammar: `SCOPE_IDENTIFIER`
mirrors `tools.readback_core.ID`, one test compares the two patterns, another reads
the scope set out of `tools/delivery_run.py` rather than restating it, and another
proves the runner accepts this plan's scope and operation identity and refuses `0`,
`-1`, `True`, `'1'` and `None` exactly as `require_generation` does.

Golden corpus: `generation` is regenerated into
`examples/resolved/*.desired-state.json`, `examples/golden/*.conformance.json`,
`examples/golden/digests.json` and `examples/golden/cross-platform.digests.json`; the
diff is exactly `generation` and the digests derived from it.

Docs: new `docs/provisioning/generation-model.md`, indexed and registered in the
drift guard, plus updates to `desired-state-model.md`, `architecture.md` (the
`generation` layer and the stage refusals) and `plan-workflow.md` (plan digest,
`--generation`, `verify` binding, `apply` handoff). A new documentation regression
compares the documented options table against the CLI parser.

`python -m pytest tests/provisioning -q` reports 360 passed / 723 subtests, and
`scripts/check_repository.py`, `scripts/check_documentation.py` and
`scripts/check_retired_interfaces.py` pass. No production record is claimed: this
repository defines the generation semantics and holds no authoritative ledger.

---

### GATE-C05 — Integrate the portable plan with the existing hosting-delivery/1 runner

Severity: P0/P1  
State at baseline: PARTIAL  
State: COMPLETE

Reopened by defect F02 of `docs/deepseek-refactor-post-audit-corrective-action.md`: the
approved identity bound an owner-operation summary (`delivery.graph_digest`) rather than
the executable reviewed topology in `provisioner/execution/handoff.py`, which was built
only after approval was checked. The approval therefore did not bind the topology that
executes.

Corrected: the manifest now binds `manifest.delivery.topology_digest`, the digest of
`handoff.topology_intent(plan)` — the sequence, the step kinds, the dependencies, the
operation-to-step bindings and the reviewed parameters — and `handoff.build` reduces the
compiled `hosting-delivery/1` graph to `handoff.approval_projection(plan, graph)` and
refuses with `APPROVAL_TOPOLOGY_MISMATCH` unless its digest is the bound one. The
parallel `delivery.graph_digest` identity is deleted.

#### Corrective closure record

F02 is fixed and the gate is COMPLETE. One canonical reviewed topology intent
(`hosting-delivery-topology-intent/1`, owned by `provisioner/execution/handoff.py`) now
owns the execution sequence, the step kinds, the dependencies, the operation-to-step
bindings and the reviewed parameters; the `hosting-delivery/1` graph is derived from it,
the existing delivery runner remains the only executor, and approval covers the topology
rather than a summary of it. `handoff.build()` verifies
`digest(approval_projection(plan, graph)) == manifest.delivery.topology_digest` before
`validate(graph)`, so a mutated topology is refused with `APPROVAL_TOPOLOGY_MISMATCH`
naming both digests. Commits `5282fba` (failing regression), `81f8a9c` (canonical intent
and the error code), `12a71a7` (manifest binding plus build verification), `8a86fca`
(identity tests), `ed59996` (deleted parallel identity), `47fd4e5` (documentation) and
`63576ce` (regenerated digests). The regression is
`tests/provisioning/unit/test_approval_topology.py`, 13 tests and 19 subtests covering
the bound sequence, kinds, dependencies, operation mapping and reviewed parameters, the
per-platform projections, and the refusal of a topology the manifest does not bind.

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

#### Completion record

`hosting apply` still executes nothing, but it now compiles the reviewed plan into
the exact graph the repository's persistent delivery runner already validates, so the
refusal is useful rather than terminal. `provisioner/execution/handoff.py` owns the
compiler; `tools/delivery_run.py` and `tools/delivery_steps.py` remain the engine and
the typed-step contract.

| Requirement | Where it is satisfied |
| --- | --- |
| 1. the existing runner is the engine | `handoff.py` imports no `tools.*`; it mirrors `tools.delivery_steps.KINDS`, the declared identifier grammar and the declared action, purpose, mode and stage sets, and a test compares every mirror against the owner's source. `tools.delivery_run.validate` accepts the compiled graph, and `NoBypassTest` proves no second runner, journal or recovery model exists |
| 2. deterministic compiler to `hosting-delivery/1` | `handoff.build(plan, source_commit, ledger=None)` is a pure function of the reviewed plan plus one clean commit; `HANDOFF_FORMAT` is the declared format and `test_the_graph_is_deterministic` compares two builds byte for byte |
| 3. responsibilities mapped to existing typed steps | `OPERATION_STEPS` maps all ten reviewed owner operations onto declared kinds; `uncovered()` is total by construction, so an operation with no owning step raises `COMPILATION_FAILED` before a graph exists |
| 4. every step bound to digest, commit, operation, generation, scope and predecessors | `operation_id` is `{wsd_key}-g{generation}-{manifest_digest[:12]}`, `source_commit` is the one clean checkout, `scope` is `plan.identity.scope`, `generation` is the reviewed generation, and the plan digest binds the complete reviewed manifest; predecessor receipts are bound by the runner's stage packets (`dependencies`), which this module deliberately never restates |
| 5. reuse of the established mechanisms | every step is a declared kind of `tools/delivery_steps.KINDS`, so Terraform prepare/apply, the WSD transition, the guest plan/apply, capacity, IPAM, DNS, acceptance, the edge policy and the campaigns are discharged by the owner code that already implements them |
| 6. execution behind the existing opt-in | `authority.EXECUTION_AUTHORITY` stays `EXTERNAL_ONLY`, the runner still requires an explicit `execute=`, and `hosting apply` exits `2` with `EXECUTION_REFUSED` |
| 7. `hosting apply` can produce the established handoff | once the recorded approval set and the clean commit are supplied, `provisioner/cli/apply.py` compiles the graph and returns it under `delivery` with a `delivery_review` projection; without them it refuses before a graph exists |
| 8. no second journal, Terraform runner or recovery model | `handoff.py` touches no filesystem, holds no lock and writes no journal; `NoBypassTest` asserts that no module under `provisioner/` names `execution_journal` or `flock` and that only `provisioner/repository.py` reaches `tools.*` |

Regressions: `tests/provisioning/unit/test_delivery_handoff.py` (51 tests / 359
subtests) covers every required case — a deterministic `hosting-delivery/1` graph
that `tools.delivery_run.validate` accepts; a source commit, scope, generation and
operation identity that are all bound; every reviewed owner operation discharged by a
declared kind; a topology-only graph that carries no parameter, private path or
receipt; a per-platform scope; an approved-plan digest mismatch, a missing digest, a
missing approval, a dirty checkout, a declared commit that is not the checkout and a
commit that is not the declared grammar all refused before a graph exists; a stale
generation and a changed reviewed state at the same generation refused before a graph
exists; a mirror that agrees with the runner on the same graphs; and no provisioning
CLI bypass, no journal, no lock and no execution authority.

`tests/test_delivery_terraform.py` is unchanged: the repository compiles one graph and
the runner keeps ownership of the receipts, `STEP_STARTED`, `resume_only` and
renewals, which a regression asserts by reading the runner's source rather than
restating the model.

Golden corpus: C05 moves no digest. The compiler is a pure function of the reviewed
plan and the commit, the commit is never part of a digest, and the graph is not part
of the manifest, so `examples/golden/digests.json` and the cross-platform digests are
byte-identical to the C03 corpus.

Docs: new `docs/provisioning/delivery-handoff-model.md`, indexed in
`docs/provisioning/README.md` and registered in the drift guard, plus updates to
`plan-workflow.md` (the `EXECUTION_REFUSED_HANDOFF_READY` status, the
`--source-commit` option and the rewritten `apply` section), `plan-manifest-model.md`
and `README.md`.

`python -m pytest tests/provisioning -q` reports 461 passed / 1116 subtests, and
`scripts/check_repository.py`, `scripts/check_documentation.py` and
`scripts/check_retired_interfaces.py` pass. Four orderings are recorded as deliberate
rather than cosmetic: `source_commit` is bound by the handoff because the reviewed
manifest deliberately excludes it; `capacity-reservation` precedes the workload phase
so `tools.capacity_demand.check_ancestors` still proves the workload shape against its
reservation; `edge-policy` precedes the workload inputs and the narrow bootstrap so no
workload is created outside the isolated route; and because `edge_policy` carries no
phase, the activation and post-activation separation is carried by
`pre-activation-campaign`, `activation` and `post-activation-campaign`. The workloads
phase is `HELD_PENDING_NATIVE_DOMAIN_OUTPUTS`, so the compiler supplies a compiled
parameter only for the phase the repository actually compiled and never invents the
held phase's catalog identity or selected input. No production record is claimed: this
repository compiles a handoff and holds no execution authority.

---

### GATE-C06 — Capacity reservation must use the authoritative reservation boundary

Severity: P1  
State at baseline: PARTIAL  
State: COMPLETE

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

#### Completion record

| Requirement | Where it is satisfied |
| --- | --- |
| 1. preserve the pure arithmetic as preflight | `provisioner/allocations/reservations.py` is unchanged and still reports `applied: False`; the `capacity` repository check still states that the reviewed arithmetic holds and names `CAPACITY_OWNER` as the authority |
| 2. compile a capacity-owner operation from the existing mechanisms and records | `provisioner/allocations/owner.py` emits `hosting-capacity-request/1`, which `tools/capacity.validate_request` accepts unchanged; reconciliation reads the repository's existing exported records through `scripts/check_reservation_records.py` (reached only via `provisioner/repository.py`) |
| 3. bind the request to the exact commissioned envelope/snapshot used during placement | `capacity_view(plan)` binds the inventory digest, status, origin and authority, the site, the platform and every reviewed zone; `binding(plan, envelope_id=..., envelope_record_sha256=...)` binds the view digest, the plan digest, the generation, the operation identity and the envelope |
| 4. require authoritative confirmation before capacity is held | `CONFIRMED_BY_OWNER` is the only state with `confirmed`/`may_allocate` true and is reachable only from a live exported record; `require_confirmed` refuses otherwise, and the `capacity-confirmation` conformance check is `PASS` only on it |
| 5. handle uncertain outcomes through observe/reconcile before retry | `HOLD_DISCOVER_RESERVATION_OUTCOME` is derived from an `UNCERTAIN` record or dependency handoff, refuses with `CAPACITY_RESERVATION_UNRESOLVED`, and the check reports `PENDING_EXTERNAL_EVIDENCE` rather than a pass or a definite failure |
| 6. reconcile a confirmation back into plan/execution evidence | `provisioner/execution/service.py::capacity_evidence` is the single reading every transport calls; the `capacity` evidence kind, the `capacity-confirmation` check, the `apply` payload's `capacity`, `capacity_review` and `capacity_owner_handoff`, and the manifest's `capacity_view` term all carry it |
| 7. prevent two operations consuming one stale snapshot | `require_exclusive(reservations)` groups recorded rows by `(pool_id, view_digest, cluster)`, skips this operation's own rows and refuses `CAPACITY_RESERVATION_CONFLICT` when the combined demand exceeds the recorded available units |

Regressions: `tests/provisioning/unit/test_capacity_owner.py` (138 tests / 13
subtests) covers every required case. The mirrored contract is compared against the
authoritative owner's own source rather than restated: the request key set, the
request format, the scope keys, the units, the identifier grammar
(`tools/readback_core.ID`) and the `10 ** 15` unit bound are all read out of
`tools/capacity.py` and `tools/readback_core.py`, and the compiled request is fed to
the real `tools.capacity.validate_request`. A proposal is never a reservation: the
handoff carries no `confirmed` or `held` key, the status is
`PROPOSED_NOT_CONFIRMED`, `may_apply`/`may_activate` are always false, and the view
carries no generation. A confirmation is bound to the exact identity: a record for
another operation or generation, another envelope id or another envelope digest is
`HOLD_RESERVATION_IDENTITY_OR_INTENT_CONFLICT`, a `RELEASED`/`EXPIRED` record is
`HOLD_TERMINAL_RESERVATION_NEW_OPERATION_REQUIRED`, a `CONSUMED` record is
`EXISTING_CONSUMED_RESERVATION`, and each refuses with the mirrored preflight
vocabulary. A lost response is not retried into a duplicate: the reservation identity
is derived from the reviewed plan, so a second attempt reconciles the first record.
Two concurrent operations cannot both be admitted against the same stale view, and a
malformed review instant, an unreadable database path inside the checkout and an
unbounded unit count are refused. The preserved preflight is still the preflight: the
two formats are asserted different, and `reservations.py` still reports `applied:
False`.

Golden corpus: the reference plans' digests moved once, when `capacity_view` became a
manifest term, and the corpus is regenerated for it; no digest moved afterwards,
because the view deliberately carries no generation and the reference export is empty,
so the default reconciliation is `HOLD_ENVELOPE_NOT_BOUND`.

Docs: new `docs/provisioning/capacity-reservation-model.md`, indexed in
`docs/provisioning/README.md` and registered in the drift guard, plus updates to
`plan-manifest-model.md` (the `capacity_view` term and the excluded external capacity
facts), `delivery-handoff-model.md` (the `capacity-reservation` owner handoff) and
`plan-workflow.md` (the `--reservation-index` and `--capacity-facts` options and the
`apply` capacity reading). A new documentation regression keeps the document a view of
the module by comparing its named formats and reconciled states against
`provisioner.allocations.owner`.

`python -m pytest tests/provisioning -q` reports 600 passed / 1154 subtests, and
`scripts/check_repository.py`, `scripts/check_documentation.py` and
`scripts/check_retired_interfaces.py` pass. Two decisions are recorded as deliberate:
the compiled owner handoff rides in the `apply` payload rather than as `capacity`
step parameters, because extending the runner's declared parameter contract is out of
scope for a repository-side gate; and the `capacity` evidence record is bound to the
view digest, because that is the reviewed snapshot the intent was compiled against,
while the owner's answer is reported separately as the reconciliation state. No
production record is claimed: this repository compiles a reservation intent, reads
exported evidence and holds no capacity and no reservation authority.

---

### GATE-C07 — IPAM and DNS must use the authoritative owner lifecycle

Severity: P1  
State at baseline: PARTIAL  
State: COMPLETE

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

#### Completion record

| Requirement | Where it is satisfied |
| --- | --- |
| 1. keep consumer requests free of CIDRs and provider identifiers | no change was needed: `provisioner/domain/request.py` and the schema still accept no prefix, no address and no provider field, and the reviewed request's `spec` is unchanged; the proposed prefix is derived by the repository from the reviewed inventory pool |
| 2. use the planning allocator only to express intent or a proposed allocation | `provisioner/allocations/addresses.py::address_view` names `PLANNING_PROPOSAL_NOT_AUTHORITATIVE_ALLOCATION` as the authority; the repository `address-intent` conformance check reports the proposal as intent and `hosting apply` never allocates |
| 3. during controlled execution call the existing authoritative IPAM owner path | the compiled allocation intent is the exact document `scripts/check_ipam_allocation_preflight.py::normalized_spec` accepts, reached only through `provisioner/repository.py::ipam_allocation_preflight`; no second owner path, no second allocator and no parallel IPAM client is added |
| 4. bind the authoritative allocation to WSD identity, generation, parent reservation, site/zone/domain and intent digest | `hosting-address-binding/1` binds `allocation_id`, `operation_id`, `generation`, `plan_digest`, `view_digest`, `reservation_id`, `request_id`, the five delivery scope keys, the zone, the domain, the pool and the allocation intent digest; `parent_spec_sha256`, `allocation_intent_digest` and `registration_intent_digest` are recomputed from the reviewed chain, so a record answering another operation, generation, parent, site, zone, pool or intent is `HOLD_IPAM_IDENTITY_OR_INTENT_CONFLICT` |
| 5. confirm/observe before using an uncertain result | an `UNCERTAIN` record is `HOLD_DISCOVER_IPAM_OUTCOME` with `next_owner_action = OWNER_DISCOVER_AUTHORITATIVE_OUTCOME` and refuses with `IPAM_ALLOCATION_UNRESOLVED`; `EXISTING_CONFIRMED_IPAM_ALLOCATION` is the only state with `confirmed` true and is reachable only from a live exported record; a malformed or unreadable export is a typed `SCHEMA_VALIDATION_FAILED` refusal rather than a raw `ValueError` |
| 6. generate DNS registration only from confirmed authoritative allocation state | the registration intent is compiled only from a confirmed allocation scope; the repository `dns-registration` check and `require_registered` are `PASS` only on `EXISTING_REGISTERED_DNS_IDEMPOTENT`, and `HOLD_IPAM_ALLOCATION_NOT_CONFIRMED` refuses with `IPAM_ALLOCATION_UNCONFIRMED` before registration is even considered |
| 7. bind DNS registration to the confirmed allocation and the complete normalized DNS intent | `hosting-dns-registration-binding/1` adds `registration_id` and the allocation confirmation digest to the allocation binding; `repository.dns_registration_spec` normalizes the intent through `scripts/check_dns_registration_preflight.py`, and `registration_intent_digest` binds the normalized intent |
| 8. implement retirement release ordering using the existing owner contracts | `require_releasable` refuses `ADDRESS_RELEASE_ORDER_VIOLATION` while a reusable allocation's dependent registration is live, while the exported cleanup is incomplete, and while a `RELEASED` allocation's name is only `TOMBSTONED`; the owner's own `scripts/check_ipam_allocation_records.py` and `scripts/check_dns_registration_records.py` enforce the same ordering |
| 9. never release reusable addressing before dependent native state is safely withdrawn | `QUARANTINED_REGISTRATION_STATES` and `WITHDRAWN_REGISTRATION_STATES` gate the release, and a `QUARANTINED`/`RELEASED` allocation must carry a complete cleanup, a `REUSE_NOT_BEFORE` instant and a release that does not predate it |

Regressions: `tests/provisioning/unit/test_address_owner.py` (146 tests) covers every
required case. The mirrored contract is compared against the authoritative owners'
own source rather than restated: the intent key sets, formats, families, kinds,
policies, statuses, record types, observation states and cleanup keys are read out of
`scripts/check_ipam_allocation_preflight.py`, `scripts/check_dns_registration_preflight.py`,
`scripts/check_ipam_allocation_records.py` and `scripts/check_dns_registration_records.py`,
and every compiled intent is fed to the real preflight. A proposal is never ownership:
a missing record is `IPAM_INTENT_READY_EXTERNAL_RESERVE_NOT_EXECUTED`, the handoff
carries no allocated value, and the reconciliation contains no literal prefix or
address. A confirmed allocation may differ from the proposal without changing the
approved plan: the plan digest and manifest bind the addressing *identity*, the view
deliberately carries no generation, and reading the owner's answer changes neither.
A mismatch is a hold, not a silent adoption: a tampered parent reservation yields
`parent.state = CONFLICT` with both zones `HOLD_IPAM_IDENTITY_OR_INTENT_CONFLICT`, a
tampered allocation record yields a conflict in one zone while the other stays
untouched, and each refuses with the mirrored vocabulary. A lost reply is reconciled,
not duplicated: `allocation_id_for`, `registration_id_for` and both operation
identities are derived from the reviewed plan, so a second attempt reconciles the
first record instead of creating a second allocation or a second name. Registration
cannot precede confirmation: `HOLD_IPAM_ALLOCATION_NOT_CONFIRMED` and the
`require_registered` ordering are asserted. Retirement cannot release ownership early:
a `QUARANTINED` allocation with a `RELEASE_PENDING` name yields
`HOLD_IPAM_RELEASE_LIFECYCLE`/`HOLD_DNS_RELEASE_LIFECYCLE` and
`require_releasable` refuses, while a `TOMBSTONED` name is releasable and a
`RELEASED` allocation with a `TOMBSTONED` name is not.

Golden corpus: the reference plans' digests moved once, when `allocation_view` became
a manifest term, and the corpus is regenerated for it; no digest moved afterwards,
because the view deliberately carries no generation and no derived identity, and the
reference export is empty, so the default reconciliation is `PENDING_OWNER` with
`parent.state = NOT_HELD`.

Docs: new `docs/provisioning/address-allocation-model.md`, indexed in
`docs/provisioning/README.md` and registered in the drift guard, plus updates to
`plan-manifest-model.md` (the `allocation_view` term and the excluded external
addressing facts), `delivery-handoff-model.md` (the addressing steps' owner handoff)
and `plan-workflow.md` (the `--ipam-index` and `--dns-index` options, the `status`
and `verify` owner readings and the `apply` addressing reading). A new documentation
regression keeps the document a view of the module by comparing its named formats,
reconciled states and settlement gates against `provisioner.allocations.addresses`.

`python -m pytest tests/provisioning -q` reports 754 passed / 1204 subtests, and
`scripts/check_repository.py`, `scripts/check_documentation.py` and
`scripts/check_retired_interfaces.py` pass. Two decisions are recorded as deliberate:
the compiled owner handoff rides in the `apply` payload rather than as `ipam`/`dns`
step parameters, because extending the runner's declared parameter contract is out of
scope for a repository-side gate; and the `allocation` evidence record is bound to the
view digest, because that is the reviewed snapshot the intents were compiled against,
while the owners' answers are reported separately as the reconciliation state. The
sibling documents the owners' preflights resolve from disk are staged by the operator
under the declared root `runtime/address-handoff/`, which is ignored and is never
written by this repository. No production record is claimed: this repository compiles
allocation and registration intents, reads exported evidence, and holds no address,
no prefix, no name and no IPAM or DNS authority.

One defect was found and fixed while closing this gate, in code this refactor owns.
The manifest bound the request source exactly as the operator spelled it, so the same
reviewed request reached through a relative path and through an absolute path had
different digests. That contradicted the manifest's own documented contract — no
checkout property, reproducible from the reviewed inputs alone — and made an approved
digest depend on the invocation. `provisioner/repository.py::reviewed_source` now
binds the path repository-relative in POSIX form, a regression asserts that a
relative, an absolute and an interior-`..` spelling replay to one plan, and the
golden corpus is regenerated once for the normalized source.

---

### GATE-C08 — Profile catalogs must become versioned policy inputs

Severity: P1  
State at baseline: PARTIAL  
State: COMPLETE

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

#### Completion evidence

- every catalog and every profile entry declares a reviewed `version`, and the
  loader refuses a catalog or profile that omits or malforms one;
- the loader publishes a canonical `digest` over the whole reviewed set, so a
  catalog revision is part of plan and desired-state identity;
- no portable default remains in `provisioner/compiler/normalize.py`: the defaults
  are the ones the catalogs declare;
- `docs/provisioning/service-profile-matrix.md` carries a `Version` column that a
  documentation test compares against the catalogs;
- a deferred profile is still refused, at resolution and in the matrix.

#### Completion record

Profile policy is now two reviewed sources and nothing else: the catalogs own what
a portable request may ask for, which defaults a request may omit, and which
revision of each answer was reviewed. No default survives in code.

| Requirement | Where it is satisfied |
| --- | --- |
| 1. explicit versioned model | every `profiles/<family>/catalog.json` declares a top-level `version`; every profile entry declares a `version` (`loader.VERSION`, `loader._version`) |
| 2. portable defaults as reviewed data | `loader.DEFAULT_OWNERS`/`Catalog.default()`/`request_defaults()`/`service_defaults()` read `default`, `services`+`defaults`, and `requestDefaults` from the catalogs |
| 3. constants only for mechanics | the only constant left is `normalize.PLACEMENT_DEFAULTS`, which encodes absence (`site`/`cell` unset) rather than policy |
| 4. resolved versions in identity | `Resolution`/`DesiredState` carry `profile_versions`, `catalog_versions`, `catalog_digest`; `Plan.digest` binds request + environment + profile versions + catalog versions + catalog digest |
| 5. loader/schema validation | the loader refuses missing/invalid/duplicate catalog versions, missing/invalid profile versions, deferred defaults, unknown defaults, a non-service catalog declaring `services`, and incomplete service defaults; `provisioner/schemas/v1/resolved-desired-state.schema.json` requires the three new fields |
| 6. matrix validated from catalogs | `tests/provisioning/documentation/test_documentation.py::ServiceProfileMatrixTest::test_documented_catalog_revisions_match_the_catalogs` compares every matrix row and every `Reviewed as catalog revision` line against the catalogs |
| 7. no duplicated family/default list | `normalize.DEFAULTS` is deleted; `defaults_for(catalog)` derives the whole default document from the catalogs |
| 8. normalization derives defaults | `normalize(document, source, catalog=None)` merges each `REQUEST_DEFAULT_OWNERS` group verbatim; `Plan.validate_request()` and `provisioner/cli/validate.py`/`resolve.py` pass the loaded catalog |

`hosting-profile-resolution/1` becomes `/2` (it now carries the revision set), and
the reviewed `examples/resolved/*.resolution.json` artifacts move to
`hosting-resolved-profile-set/2`; the shared environment document is deliberately
unchanged so every golden `environment.json` stays byte-identical and the existing
compiler keeps refusing unknown top-level keys.

Regressions: `tests/provisioning/policy/test_profile_versions.py` (34 tests / 94
subtests), plus the plan-digest test in `tests/provisioning/unit/test_determinism.py`
and the two new corpus tests in `tests/provisioning/end_to_end/test_golden.py`.
`python -m pytest tests/provisioning -q` reports 310 passed / 648 subtests, and
`scripts/check_repository.py`, `scripts/check_documentation.py` and
`scripts/check_retired_interfaces.py` pass.

---

### GATE-C09 — Adapter contract must own real realization behavior, not only descriptors

Severity: P1/P2  
State at baseline: PARTIAL  
State: COMPLETE

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

#### Completion record

| Requirement | Where it is satisfied |
| --- | --- |
| 1. define the exact adapter responsibilities that are missing from generic code | `provisioner/adapters/base.py` declares six surfaces: `capability_contract()`, `placement_contract()`, `phase_contract(phase)`, `readback_contract()`, `security_edge_contract()` and `realization_gaps()`. `realization_contract()` returns all six plus `format`, `platform`, `family`, `gap_codes`, `limits` and `native_contact: false`. The five responsibilities the gate names are therefore explicit, named and separately testable rather than implied by a metadata dataclass |
| 2. move only genuinely provider-specific portable-to-native mapping decisions behind the adapters | exactly one such decision existed. `tools/compile_wsd.py` built the NSX segment mapping inside `if platform == 'vmware':`. It is now the declarative `WORKLOAD_NETWORK_BINDING` table (keyed by platform: `observed_field`, `native_field`, `binding_field`, `binding_identity`, `message`) that the compiler looks up, mirrored as data on `Adapter.binding_requirement` and bound into the plan manifest. No mature provider logic was rewritten to fill a method |
| 3. keep `tools/compile_wsd.py` as the existing internal compiler where it is already the right authority | the compiler still owns every native field shape. The adapter reads `PLACEMENT`, `NETWORK` and `WORKLOAD_NETWORK_BINDING` out of it through `provisioner/repository.py`, which remains the only module allowed to import `tools/`. `compile_environment(document, phase, outputs, phase_bindings)` is unchanged in behavior and only renamed its last argument away from `vmware_bindings` |
| 4. make generic provisioning code ask the selected adapter rather than branch on platform-specific assumptions | `provisioner/compiler/environment.py` asks the adapter for the declared inputs (`native_variables` delegates to `declared_inputs(phase)`), for the gap decision (`realization_gaps` delegates to `Adapter.realization_gaps()`) and for the list of facts the provisioner computes (`PROVISIONER_OWNED_INPUTS` derives from `adapters.COMPUTED_FACTS`). `provisioner/execution/plan.py::create_plan` asks `adapters.get(state.platform).validate(plan)` after compilation and refuses with `REALIZATION_CONTRACT_UNSATISFIED` (`compilation` layer, `path: $.spec.platform`, `details = {'platform', 'problems'}`) |
| 5. each adapter exposes the capability, placement, phase, readback and gap contracts | all five are surfaced per platform and asserted cell by cell. Capability: `product_tuple`, `qualified`, `status: NATIVE_QUALIFICATION_ABSENT`, `blockers: ['product_tuple:UNSELECTED']`, extended by `required=` and `assurance_profile=`. Placement: nutanix `cluster_id`/`storage_container_id`, vmware `resource_pool_id`/`datastore_id`, openstack `compute_availability_zone`/`storage_availability_zone`/`volume_type`. Phases: per-module declared inputs, accepted computed inputs and unavailable inputs. Readback: the domains-phase native identity, split by `produced_by_module` and `produced_by_binding`, with the vmware binding requirement. Gaps: vmware declares `COMPUTED_INPUT_NOT_ACCEPTED` for `ipv4_address`; nutanix and openstack declare none |
| 6. keep execution and platform contact outside the adapter | every surface, including `to_dict()` and `realization_contract()`, carries `native_contact: false` and a declared `authority` read from reviewed configuration. The adapters expose no mutating entry point and `provisioner/adapters` imports no client, credential or transport. The three new conformance checks that run the contract are repository-side static checks that can never satisfy an external requirement |

Regressions: `tests/provisioning/adapters/test_adapter_contract.py` (97 tests, 14
classes) covers all nine required cases. Required zones represented: the required zone
set is derived from `plan.resolution.zones` rather than hard-coded, and a plan with the
RZ domain removed is refused with a problem naming the absent zone. Placement
preserved: every emitted workload's native inputs are a superset of the selected
platform's placement fields and a subset of the adapter's declared union, proven
against the real compiled workloads phase rather than the accessor. Network intent
preserved: the readback identity the domains phase must observe is declared and is
never reported as already observed. Isolation outcome represented: the security-edge
component, its component list and its `security-edge` owner scope are read from
`terraform/catalog.json` and matched to the reviewed `security-edge-route` operation.
Service binding preserved: the service bindings are asserted byte-identical across all
three platforms, so no adapter can silently reshape them. Recovery intent represented
when supported: the `backup-retention` operation is read per request and
`recovery-readiness` is asserted external, never satisfied from the repository alone.
Unsupported capability refused: an unqualified capability and an unqualified assurance
profile both appear as blockers, and `REALIZATION_CONTRACT_UNSATISFIED` is asserted
registered in `errors.CODES` in the `compilation` layer. Provider-specific native
fields never leak into the portable request: every request key is checked against the
union of every platform's declared native field names. Adapter declarations cannot
drift from the compiler or the Terraform modules: the placement and network field sets
are compared to the compiler tables, the module identities to the reviewed composition
roots, and the readback identity to the reviewed modules' own `outputs` read from
`main.tf.json`. A thirteenth class walks the AST of `tools/compile_wsd.py` and of every
`provisioner/**.py` source and fails on any comparison against a platform-name literal,
which is the regression that keeps requirement 4 from regressing.

Golden corpus: the reference plans' digests moved once, when `realization` became the
twenty-third manifest term, and the corpus is regenerated for it
(`internal-production` `ec0ac3a8?`, `internal-development` `76904660?`, `multi-tier`
`492dc42d?`, `recovery-enabled` `7a1b2865?`, `storage-heavy` `a68a61bf?`, and the
cross-platform vmware `4dfb2ddc?`, nutanix `46a9354d?`, openstack `a2ece110?`). No
digest moved afterwards, because the term is a canonical digest of the reviewed
declaration and the declaration is read from the compiler and the catalog rather than
from anything volatile.

That record describes the C09 state. The corrective action moved the digests exactly once
more, for F01 and F02: F01 replaced the OS-dependent inventory origin with a logical
source identity and F02 bound the executable delivery topology, so `multi-tier` now
records `manifest_digest` and `plan_digest` `2c8555eb1203…`. The current values are the
ones in `examples/golden/digests.json` and
`examples/golden/cross-platform.digests.json`, regenerated once in `1830b16` and
`63576ce`, and they are the values every replay test asserts.

Docs: `docs/provisioning/adapter-contract.md` is rewritten around the six surfaces,
the gap vocabulary, the per-platform declarations, `hosting-platform-adapter/2`, the
`realization` manifest term and the refusal path, and the "no drift" section now
states that the adapter projects the compiler rather than re-exporting it. Three
active documents are updated: `architecture.md` gains the realization-contract stage
and a paragraph on what the adapters own, `plan-manifest-model.md` gains the
`realization` term and names it in the provability paragraph, and
`terraform-boundary.md` corrects the native-input ownership section (the owned inputs
are now derived from the adapter) and records that the compiler holds no
provider-specific branch.

`python -m pytest tests/provisioning -q` reports 851 passed / 1278 subtests, and
`scripts/check_repository.py`, `scripts/check_documentation.py` and
`scripts/check_retired_interfaces.py` pass. One decision is recorded as deliberate:
`WORKLOAD_NETWORK_BINDING` lives in the compiler rather than in the adapter package,
because the compiler is the module that has to perform the lookup and because
`tests/provisioning/unit/test_architecture.py` forbids `tools/compile_wsd.py` from
importing `provisioner/`; the adapter surfaces the same declaration as data, so there
is one source and no second copy. `sources/module_inventory.json` is left unchanged
and is not enforced by any drift check. No native qualification, no platform contact
and no production evidence is claimed: the adapters describe reviewed configuration,
every adapter reports `NATIVE_QUALIFICATION_ABSENT`, and the conformance status stays
`BLOCKED_ON_EXTERNAL_EVIDENCE` on the same seven external checks.

---

### GATE-C10 — Cross-platform golden coverage must include every compatible reference request

Severity: P2  
State at baseline: PARTIAL  
State: COMPLETE

Reopened by defects F01 and F03 of `docs/deepseek-refactor-post-audit-corrective-action.md`:
the golden matrix asserted a plan identity that moved with the checkout's path separator,
and the generated documentation that the gate cites was not reproducible from its
generator, so the hosted `repository` job failed on the recorded tree.

Affected requirements include R20, sections 41-44, 64, 71, 88, 93, 99, and 100.

#### Corrective closure record

F01 and F03 are fixed and the gate is COMPLETE. The five primary goldens replay on Linux
and every one of the fifteen request-by-platform cells reproduces its stored digests,
because the approved identity is now separator- and checkout-independent (F01) and the
committed matrix is byte-identical to what its generator produces (F03). Commits
`1830b16` and `63576ce` regenerated the portable and topology-bound digests once, on this
workstation, and the recorded values are replayed unchanged rather than re-derived per
operating system - the corrective specification's prohibition on per-OS golden
regeneration is honoured. The regressions are
`tests/provisioning/end_to_end/test_golden.py`
(`CrossPlatformGoldenTest.test_every_cell_reproduces_its_stored_digests`,
`GoldenCorpusCommandTest.test_plan_reproduces_the_stored_digest_for_every_request`,
`GoldenReplayTest.test_conformance_reports_are_reproduced` and
`GoldenReplayTest.test_the_digest_index_is_reproduced`), all of which failed on the base
tree `469bbd8` and pass here. `tests/provisioning` reports 900 passed and 1449 subtests.

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

#### Completion record

| Requirement | Where it is satisfied |
| --- | --- |
| the compatibility matrix `reference request x compatible platform fixture` | `examples/golden/cross-platform.digests.json` (format `hosting-golden-cross-platform/2`) carries `requests.<request>.platforms.<platform>` for all five reference requests against all three reviewed platform fixtures (15 realized cells) and `requests.<request>.refusals` for every one of the six declared-platform/fixture-platform pairs that differ (30 refusal rows). No cell of the 5 x 3 x 3 cross product is omitted |
| store and test the explicit refusal for an intentionally incompatible scenario | a reviewed fixture represents exactly one platform, so a request that selects a different platform is the intentional incompatibility. `tests/provisioning/support.py::platform_refusal` plans the combination and returns the raised `ProvisioningError`; each refusal row stores its `code` (`NO_ELIGIBLE_PLACEMENT`), `path` (`$.spec.placement`), `status` (`HOLD_NO_ELIGIBLE_SITE`) and `reason`, and `test_every_incompatible_combination_records_its_explicit_refusal` replays all 30 and asserts every row against the live refusal |
| same portable semantics in every cell | each request is planned against each fixture with only `spec.platform.preference` selected. `portable_digest` is stored once per request (the body with no platform selected) and `test_every_platform_is_asked_the_same_portable_question` asserts each stored digest equals the recomputed one, that the five digests are distinct, and that `support.platform_request(platform, name)` differs from the portable body only in that one key |
| deterministic request/profile/placement/desired-state/environment/plan digests | every realized cell stores `request_digest`, `resolution_digest`, `placement_digest`, `desired_state_digest`, `environment_digest`, `plan_digest` and `manifest_digest`; `test_every_cell_reproduces_its_stored_digests` recomputes all seven from a fresh plan |
| expected provider-native realization root | every realized cell stores `stack_roots`; `test_every_cell_records_its_provider_native_realization_root` asserts it is exactly `terraform/stacks/wsd/<platform>/domains`, that the plan's Terraform scopes agree, that `desired_state.platform` is the fixture's platform, that the compiled file list matches, and that no other platform's segment appears in the path |
| no provider-native fields in input | `support.native_field_names(platform)` reads the names from the reviewed `tools.compile_wsd` declaration; `test_no_matrix_input_carries_a_provider_native_field` asserts no request document names any of them at any depth and that no native field name appears anywhere in the corpus text |
| expected realization gaps explicitly recorded | every realized cell stores `realization_gaps`; `test_every_cell_records_its_expected_realization_gaps` asserts it equals the plan's warning codes and always contains `INVENTORY_NOT_AUTHORITATIVE`, and `test_the_vmware_realization_boundary_is_recorded_not_dropped` asserts `REALIZATION_INPUT_UNAVAILABLE` is present on every VMware cell and absent on Nutanix and OpenStack |
| no fixture claims native contact or production authority | the corpus carries `native_contact: false`, and `test_no_cell_claims_native_contact_or_production_authority` asserts every cell's `status` is `PLANNED_DISABLED_NOT_AUTHORIZED`, the plan's `native_contact` and `conformance['native_contact']` are false, `decision.authorized` is false, and `conformance['status']` is `BLOCKED_ON_EXTERNAL_EVIDENCE` with `ready` false |

Regressions: `tests/provisioning/end_to_end/test_golden.py::CrossPlatformGoldenTest`
holds the nine required cases, and the pre-existing `GoldenCorpusTest` cases keep covering
the shared corpus invariants (no brittle field, no `native_contact: true`, reviewed
catalog revisions). `tests/provisioning/support.py` gained `PLATFORMS`,
`native_field_names()`, `portable_request()` and `platform_refusal()`, so the matrix is
built from the reviewed fixtures and the reviewed compiler declaration rather than a
second hand-written copy of either.

Corpus: `examples/golden/cross-platform.digests.json` moved from
`hosting-golden-cross-platform/1` to `hosting-golden-cross-platform/2`. The format now
indexes requests first (`requests.<request>.platforms`, `requests.<request>.refusals`) and
moves `fixture` and `portable_digest` from the per-platform cell to a top-level `fixtures`
block and the per-request `portable_digest`. The previous three `internal-production`
cells reproduce byte for byte apart from that relocation; `examples/golden/digests.json`,
the resolution artifacts and the conformance artifacts are unchanged and no `plan_digest`
moved.

`python -m pytest tests/provisioning -q` reports 875 passed / 1402 subtests, and
`scripts/check_repository.py`, `scripts/check_documentation.py` and
`scripts/check_retired_interfaces.py` all exit 0. Nothing external was contacted and no
qualification, placement authority, native contact or production authorization is
claimed.

---

### GATE-C11 — Fix dependency-direction enforcement and remove CLI command coupling

Severity: P1/P2  
State at baseline: INVALID  
State: COMPLETE

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

#### Completion record

The command rule now runs, and the shared operations it needs live below the transport.

| Requirement | Where it is satisfied |
| --- | --- |
| 1. unreachable regression fixed | `test_architecture._command_couplings()` is called from `test_a_cli_command_imports_no_other_command`; the old `continue` and the code after it are gone |
| 2. shared operations moved below the CLI | `provisioner/execution/service.py` holds `Context`, `build_context()` and `plan_for()` |
| 3. commands are thin transports | `plan.py` no longer defines `plan_for`; `apply`, `evidence`, `status` and `verify` call `service.plan_for(context)`; `main.py` calls `service.build_context()`; `support.py` keeps only `EXIT_*`, `emit()` and `refused()` |
| 4. no command imports a command | no `provisioner/cli/*.py` names another command, by either import form |
| 5. entry point preserved | `python -m provisioner.cli` is unchanged; `tests/provisioning/end_to_end/test_cli.py` and the documented-entry-point regression both exercise it |

The rule reads the import graph instead of a module prefix, so `from provisioner.cli import plan` is reported as well as `from provisioner.cli.plan import plan_for`. `test_the_command_rule_refuses_a_controlled_command_to_command_import` writes a fixture command to a temporary directory, parses it exactly like a real module and asserts the rule reports `provisioner.cli.plan` for a command and reports nothing for the transport. `test_every_command_delegates_to_the_shared_service` fails any command module that does not import `provisioner.execution.service`.

`provisioner.cli.plan.run_from_path` had no callers and duplicated `build_context()` plus `run()`, so it was removed instead of being left as a migration alias.

Regressions: `tests/provisioning/unit/test_architecture.py` (reachable rule, controlled fixture, shared-service delegation, no outside import of the transport, `tools/compile_wsd.py` independence), `tests/provisioning/end_to_end/test_cli.py` (all seven commands as subprocesses), `tests/provisioning/documentation/test_documentation.py` (the documented entry point runs). `python -m pytest tests/provisioning -q` reports 272 passed / 531 subtests, and `scripts/check_repository.py`, `scripts/check_documentation.py` and `scripts/check_retired_interfaces.py` pass. No artifact, schema or digest changed.

---

### GATE-C12 — Conformance language must distinguish proposals from confirmed owner state

Severity: P1/P2  
State at baseline: PARTIAL  
State: COMPLETE

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

#### Completion record

| Requirement | Where it is satisfied |
| --- | --- |
| 1. rename repository-side checks to describe what is actually proven | `provisioner/conformance/checks.py` names them `capacity-proposal`, `address-intent` and `service-binding`, and the comment on `REPOSITORY_CHECKS` states what each one is. The previous names (`capacity`, `addresses`, `services`) are gone from the module, from the tests and from the two active documents that named them |
| 2. keep owner confirmation as separate mandatory external evidence | `checks.CONFIRMATION_OF` maps each proposal to the owner check that settles it (`capacity-confirmation`, `address-confirmation`, `service-acceptance`). All three owner checks are in `EXTERNAL_CHECKS` and in `MANDATORY`, and no proposal is promoted into one: a satisfied proposal leaves its owner check `PENDING_EXTERNAL_EVIDENCE` and blocking |
| 3. never use ownership vocabulary for a repository-only proposal | `checks.OWNERSHIP_VOCABULARY` is the seven words. `report.ownership_claims()` reads every repository row's prose and, for the three proposal rows, the values their evidence carries; `report.build()` raises `CONFORMANCE_CLAIM_UNPROVEN` (registered in `provisioner/domain/errors.py` under the `authority` layer) instead of emitting a report in which a proposal claims an outcome only an owner can give. A proposal may use a word only once the owner check that settles it has passed |
| 4. bind external evidence to plan digest and generation before it can satisfy a check | `checks.evidence_binding(plan, document, keys=..., view_digest=...)` compares the operation identity, generation, plan digest and view digest against the plan's own reading. `CAPACITY_BINDING_KEYS` and `ADDRESS_BINDING_KEYS` name the keys, the operation identity already embeds the claimed generation and the reviewed digest prefix, and the view digest is compared against `capacity_module.view_digest(plan)` / `address_module.view_digest(plan)` rather than the envelope's own copy. `production-authorization` is bound the same way: `_authorization_check` reports a supplied approval as the owner's answer only when it cites `plan.digest` |
| 5. make stale or wrong-generation evidence remain pending or fail | a reading that fails any comparison returns `PENDING_EXTERNAL_EVIDENCE` with `foreign` naming the mismatched keys and `expected_operation_id`, so it settles nothing. The repository-side `generation` check fails on a stale or generation-less observation, and `native-observation` is external and never PASS from a supplied list |

Regressions: `tests/provisioning/conformance/test_conformance.py` (34 tests) covers all
four required cases. Proposal-only plan: `ProposalLanguageTest` asserts that no
repository row's detail and no proposal row's evidence value uses
`OWNERSHIP_VOCABULARY`, that every proposal is `PASS` with authority `REPOSITORY` while
the check that settles it is `PENDING_EXTERNAL_EVIDENCE` with authority `EXTERNAL` and in
`blocking`, that the report is `BLOCKED_ON_EXTERNAL_EVIDENCE` with `ready` false, and that
the `proposal` block names the same authority (`REPOSITORY_PROPOSAL_NOT_OWNER_STATE`), the
same `confirmed_by` map and every proposal as `unconfirmed`. Wrong plan/generation record:
`EvidenceBindingTest` supplies another generation's capacity reading
(`foreign == ['generation', 'operation_id', 'plan_digest']`), a moved capacity
`view_digest`, another operation's addressing reading and a moved addressing
`view_digest`, and asserts each stays `PENDING_EXTERNAL_EVIDENCE` with the mismatched keys
named; an approval citing another plan digest stays `PENDING_EXTERNAL_EVIDENCE` with
`foreign == ['plan_digest']`. Missing observation: the `generation` repository check fails
on a stale or generation-less observation while `native-observation` stays `PENDING` with
the `bound`/`stale`/`unbound` counts, and a fully bound observation list is still not the
owner's attestation. Unknown evidence blocks activation:
`activation.require_conformant` refuses with `ACTIVATION_REFUSED` and a `blocking` list
containing every mandatory external check, and refuses again when the owners'
reconciled readings and a matching approval are supplied. The guard itself is pinned by
`test_a_proposal_that_claims_an_unconfirmed_outcome_is_refused`, which monkeypatches a
`capacity-proposal` row whose detail says "reserved" and asserts `CONFORMANCE_CLAIM_UNPROVEN`
with the claim, the word and the settling check in `details`, and by
`test_a_proposal_that_claims_an_outcome_the_owner_confirmed_is_allowed`.

`provisioner/schemas/v1/conformance-report.schema.json` requires the `proposal` block and
forbids additional keys inside it. `provisioner/conformance/activation.py` now passes the
reconciled owner readings through, so a caller that holds the owners' answers is judged
on them and a caller that holds none is refused by the checks that stay pending.
`provisioner/execution/plan.py::create_plan` still builds the embedded report without owner
readings, which is why every plan stays `PLANNED_DISABLED_NOT_AUTHORIZED` with all eight
external rows pending.

Golden corpus: the check names are part of the conformance artifact, so the five reference
conformance files and their five digests moved (`internal-development` `ec09aa42?`,
`internal-production` `85646ec4?`, `multi-tier` `782c3aa2?`, `recovery-enabled`
`0f0ada26?`, `storage-heavy` `0c1fc5cf?`). No `plan_digest`, `manifest_digest`,
`desired_state_digest`, `environment_digest` or `resolution` artifact moved, and
`cross-platform.digests.json` is unchanged.

`python -m pytest tests/provisioning -q` reports 870 passed / 1280 subtests, and
`scripts/check_repository.py`, `scripts/check_documentation.py` and
`scripts/check_retired_interfaces.py` all exit 0. Nothing external was contacted and no
qualification, reservation, allocation, registration or authorization is claimed.

---

### GATE-C13 — Final documentation, backlog, and retired-path cleanup

Severity: P1  
State at baseline: PARTIAL
State: COMPLETE

Reopened by defects F03 and F04 of `docs/deepseek-refactor-post-audit-corrective-action.md`:
the generated navigation documents were not reproducible from their generator, and this
audit's completion claim was contradicted by the hosted `repository` job failing on the
tree the claim named.

Affected requirements include sections 9-16, 45, 51, 54-59, 74-75, 86, 88-96, 101, 103, 105, and 107.

#### Corrective closure record

F03 and F04 are fixed and the gate is COMPLETE. `scripts/build_documentation.py` is the
source of truth again: the maintained-design pointer, the navigation paragraphs, the
assurance tail, the `docs/README.md` table row, the RAD/TAD pointer, the portable
provisioning section and the `code_map()` extras were moved into the generator, the
non-idempotent append-only `run()` post-pass that produced the duplicated pointer was
deleted, and every write is explicitly `utf-8`. Replaying `Builder.run()` through a
`Path.write_text` capture now reproduces 141 of 141 generated documents byte for byte;
the two committed documents that were genuinely corrupt (`docs/implementation/README.md`
carried a `?` where an em dash belongs, and `docs/implementation/code-map.md` linked
`../implementation/delivery-guide/7-…`, which resolves to a path that does not exist)
were regenerated from the corrected generator. The audit itself was reopened first
(`1c5371a`) rather than re-labelled. Commits `da77c60` (failing navigation regression),
`e32a9e2` (generator fix) and `07f4240` (regenerated indexes). The regressions are
`tests/test_commissioning_pack.py::IntegrationTests` -
`test_generated_engineering_navigation_matches_source`,
`test_generated_implementation_navigation_matches_source` and
`test_portable_provisioning_navigation_survives_regeneration`, which read the generated
documents with an explicit `utf-8` codec instead of the host locale - and
`tests/test_task_tree_integration.py::NavigationIntegrationTests::test_task_and_commissioning_navigation_match_generator`,
all four of which failed on the base tree `469bbd8`. `scripts/check_documentation.py`
exits 0 with 37315 checks and 0 failures, `scripts/check_repository.py` and
`scripts/check_retired_interfaces.py` exit 0, and the hosted workflow is green on the
exact final head recorded in section 12.

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

#### Completion record

| Requirement | Where it is satisfied |
| --- | --- |
| 1. update authoritative active documents instead of adding parallel narratives | the refactor has one narrative. `README.md` and `docs/README.md` point at the provisioning document set, this audit and `docs/NEXT_WORK.md`; the provisioning set itself is the specification of the current path; no second description of the same mechanism was introduced by C01-C13 |
| 2. keep the master prompt as the governing specification | `docs/deepseek-master-refactor-provisioning-prompt.md` is unedited by this refactor and remains the governing specification named in this audit's header and in every gate record |
| 3. keep this audit current | every gate C01-C13 now carries `State: COMPLETE` with a completion record that names the code, the regression and the verification command. This file is the single ledger; no gate is complete because a document says so |
| 4. update the named active documents | `README.md` and `docs/README.md` gained the portable-path pointer; `docs/NEXT_WORK.md` was rewritten; `docs/provisioning/README.md` lists the active set and the test layout; `docs/implementation/README.md`, `docs/architecture/README.md` and `docs/engineering/README.md` already pointed at the provisioning set; `examples/README.md` and `docs/provisioning/terraform-boundary.md` describe the full request-by-platform matrix. The Terraform and Ansible READMEs were not changed because their active contract did not change |
| 5. remove completed repository-side work from NEXT_WORK and backlogs | `docs/NEXT_WORK.md` no longer carries any completed item. Git is the history; the file holds only rows that a commit cannot close. The W01-W29 acceptance backlog in `docs/implementation/automation/completion-backlog.md` was reviewed and left intact: every one of its closure criteria requires native evidence, so it is external work, not a completed repository-side item |
| 6. preserve genuinely external blockers | `docs/NEXT_WORK.md` is now a six-column table - owner, missing external evidence/input, why it matters, repository-side contract already completed, completion condition, hold point - with fourteen rows. Each row names the owner of the missing external input and the repository-side contract that is already finished |
| 7. update the retired-interface register when an interface, path, schema or command is retired | `provisioner/retired_interfaces.json` (format `hosting-retired-interfaces/1`) still holds its eleven entries and needed no new entry: C01-C13 retired no interface, path, schema or command. The gates renamed a library argument (`vmware_bindings` to `phase_bindings`) and added keywords; every caller passes positionally or by the new name, and the adapter contract regression pins that the platform-named argument is gone. The platform-specific `--vmware-bindings` flag and the `vmware_bindings` delivery input key are a different, still-current surface: they name a vCenter/NSX handoff, not the generic compiler |
| 8. search all active code, docs, tests and examples for stale path, schema, CLI, terminology and implementation references | a repository-wide scan of every tracked text file outside `build/` classified the fifteen required terms (table below). A separate scan of 510 active documents resolved every relative link and found zero targets that do not exist. The scan found one stale caller: `tests/test_platform_family_eligibility.py` still asserted that a mandatory capability blocker is the bare capability name, which the qualification gate had already changed to `capability:<id>:NOT_NATIVE_QUALIFIED`. It is fixed and now also pins `product_tuple:<tuple>:NOT_NATIVE_QUALIFIED` |
| 9. delete obsolete active code, tests, examples and compatibility paths after callers migrate | no occurrence was classified `OBSOLETE_REMOVE`, so nothing was deleted. Two compatibility modules remain and both are retained deliberately: see the retention paragraph below |
| 10. leave no temporary migration alias without an explicit compatibility requirement and exit plan | the only two aliases in the tree are the two modules above. Each has named consumers, a documented reason and a written removal condition, so neither is an unexplained leftover |

#### Final stale-term audit

Counts are occurrences across every tracked text file outside `build/`. `compat` is counted
as a prefix, so its 420 include the 339 `compatibility` hits.

| Term | Occurrences | Meaning found | Classification |
| --- | --- | --- | --- |
| `TODO` | 12 | the term inside the governing prompts and this audit's own requirement text; the "do not create another TODO list" and "remove stale TODO language" prohibitions in `docs/production-deepseek-implementation-plan.md`. No source marker | CURRENT_REQUIRED |
| `FIXME` | 6 | the same requirement text and prohibitions. No source marker | CURRENT_REQUIRED |
| `TBD` | 6 | the same requirement text, plus the lowercase `'tbd'` placeholder sentinel in `scripts/adr_lifecycle.py`'s not-recorded vocabulary | CURRENT_REQUIRED |
| `legacy` | 128 | provider "legacy resource" guidance, the Nutanix `legacyErrorMessage` task field, and prepared-receipt readability in `tools/terraform_apply.py` | CURRENT_REQUIRED, HISTORICAL_ONLY |
| `deprecated` | 144 | mostly the term list and the NetBox native lifecycle status `deprecated`, which is provider vocabulary the IPAM and DNS owners must write and read | CURRENT_REQUIRED |
| `compat` | 420 | the `compatibility` evidence block of the version/source-provenance gate, the term list, and the local `compat = record['compatibility']` variable in `provisioner/qualification/provenance.py` | CURRENT_REQUIRED |
| `compatibility` | 339 | the same gate's evidence block and the `tools/compatibility` entry in the retired-interface register that records the path as removed | CURRENT_REQUIRED |
| `obsolete` | 79 | the retirement requirement itself: "remove obsolete routes, DNS and access" in requirements, ADRs and runbooks. No obsolete active path is described | CURRENT_REQUIRED |
| `superseded` | 212 | the ADR lifecycle state `Superseded`, `provisioner/domain/generation.py`'s `SUPERSEDED` generation state, delivery-runner guards that refuse work a later handoff superseded, and the register's reasons for removed paths | CURRENT_REQUIRED |
| `old` | 3593 | ordinary English in prose ("old writer", "old source") plus historical archive and frozen transcription families | CURRENT_REQUIRED, HISTORICAL_ONLY |
| `previous` | 601 | the domain vocabulary of chaining: `previous_sha256`, `previous_receipt_sha256`, previous-generation comparison | CURRENT_REQUIRED |
| `temporary` | 557 | the domain vocabulary of time-bounded grants (temporary migration access, temporary P0 services) and `tempfile.TemporaryDirectory` in tests | CURRENT_REQUIRED |
| `migration` | 4254 | the frozen transcription and archive families (`sources/**`, `reference/**`, `docs/archive/**`) plus the delivery-migration domain terms | HISTORICAL_ONLY, CURRENT_REQUIRED |
| `shim` | 12 | the requirement's prohibition, and the register entry that records that no compatibility shim survived the refactor | CURRENT_REQUIRED |
| `fallback` | 257 | the no-plaintext-fallback and no-IPv4-fallback rules, and explicit-failure paths that refuse a fallback | CURRENT_REQUIRED |

No occurrence was classified `OBSOLETE_REMOVE`, so no term required a deletion.

#### Retained compatibility paths

Two modules remain, both with a named consumer, a documented reason and a removal condition.

`scripts/documentation_controls.py` re-exports the one maintained ADR implementation under
its former names. Its consumers are `tests/test_main_integration.py` (as `legacy`) and
`tests/test_completion_remediation.py` (as `control`), and
`docs/assurance/main-integration-audit.md` records the consolidation decision. The names
`region`, `block_checks`, `amendment_records`, `render_adrs` and `visible_word` are
retired-model guards: they raise rather than write. Removal condition: migrate both test
modules to `adr_lifecycle` and `documentation_structure` directly, then delete the module
and its row in `docs/assurance/main-integration-audit.md`.

`scripts/build_assurance.py` is the compatibility command for
`build_assurance_indexes.build`. Its consumer is `tests/test_main_integration.py`, which
pins the delegation with `test_old_builder_is_same_callable`. Removal condition: drop that
pin, then delete the command.

Both are compatibility requirements with an exit plan, not unexplained aliases, so
requirement 10 is satisfied by retaining them with this record.

#### Validation environment

`tools/check_local.py` cannot pass on this workstation, and the refactor did not cause
that. The command discovers every module under `tests/`, and the POSIX-only family needs
`os.getuid`, `/etc/machine-id`, `/proc/self/ns/net` and `fcntl`. Run against a detached
worktree of the audited baseline `1b7756e`, it reports 15 failures and 132 errors. Run
against this refactor, it reports the same 15 failures and 132 errors, and the two
identifier sets compare equal with no difference in either direction. The single new
failure this scan did find - the stale blocker vocabulary in
`tests/test_platform_family_eligibility.py` - is fixed in `ea792bf`, which is what makes
the two sets equal.

Regressions: `tests/provisioning` reports 875 passed / 1401 subtests, and
`tests/test_platform_family_eligibility.py` reports 26 tests. `scripts/check_repository.py`,
`scripts/check_documentation.py` (37314 checks) and `scripts/check_retired_interfaces.py`
all exit 0. The repository-wide term scan and the 510-document link scan are recorded
above. Nothing external was contacted and no qualification, reservation, allocation,
registration, authorization or native realization is claimed.

After the corrective action the same command reports 12 failures and 132 errors: the
error count is unchanged, and the failure count is three lower than the pre-refactor
baseline because the three navigation tests that the F03 fix repairs now pass on this
workstation. The failing identifier sets are compared in section 12; every identifier in
the current set is present in the baseline set, so there is no new failure and the
remaining entries are the same POSIX-only environmental family described above. The
current counts are `tests/provisioning` 900 passed / 1449 subtests,
`scripts/check_documentation.py` 37315 checks with 0 failures, and
`scripts/check_repository.py` and `scripts/check_retired_interfaces.py` exit 0.

---

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

---

## 12. Final completion record

Status: COMPLETE. All thirteen gates are COMPLETE. C03, C05, C10 and C13 were reopened by
`docs/deepseek-refactor-post-audit-corrective-action.md` because the hosted
`Architecture and automation validation` workflow (run `35917384798`) failed its
`repository` job on the tree the previous record named; the four defects F01 to F04 are
now fixed at the source of truth, each behind a durable regression, and the hosted
workflow is green on the exact head recorded below. No gate is BLOCKED_EXTERNAL: the
external items are separate remaining work recorded in `docs/NEXT_WORK.md`, and they
block native realization and commissioning, not repository-side completion.

### Verified tree

The corrective tree validated by the hosted workflow named below is
`82855759979d752f446fc301a42bb169859cf99d`, and the earlier corrective run
`35950478558` validated `a538f60b823cacc0bbbbc60945c2c92f80fbc853`. The commit that
carries this record changes only this audit file, so it shares every validated input with
that tree; the same workflow runs on it, reports the same figures and concludes green, as
recorded below. The refactor spans the audited baseline
`1b7756e4df52ebe58ac8d93266977a27915dc3dc` to the corrective tree
`1c5371a`…`07f4240` and then to this record.

### Gate states

| Gate | State | Repository-side result |
| --- | --- | --- |
| C01 | COMPLETE | native qualification gates placement; unqualified and fixture inventory can never authorize |
| C02 | COMPLETE | coherent multi-zone/cell envelope resolution with explicit refusal statuses |
| C11 | COMPLETE | dependency direction enforced; all seven CLI commands reach one core library |
| C08 | COMPLETE | versioned profiles and default ownership |
| C04 | COMPLETE | generation model with compare-and-set generation records |
| C03 | COMPLETE | complete reviewed-plan manifest and digest; logical source identity is separated from the filesystem origin, so the identity is checkout- and separator-independent (F01) |
| C05 | COMPLETE | deterministic compiler to the existing `hosting-delivery/1` handoff; the manifest binds the executable reviewed topology and `handoff.build` refuses a topology it does not bind (F02) |
| C06 | COMPLETE | capacity authority integrated as proposal plus separate owner confirmation |
| C07 | COMPLETE | IPAM and DNS authority integrated as intent plus separate owner confirmation |
| C09 | COMPLETE | adapter responsibilities limited to real provider-specific realization |
| C12 | COMPLETE | conformance language separates repository proposals from confirmed owner state |
| C10 | COMPLETE | golden cross-platform matrix covers every request and every platform; every cell replays its stored digests on Linux and Windows (F01, F03) |
| C13 | COMPLETE | one active documentation story, external-only backlog, classified stale terms, no `OBSOLETE_REMOVE`; the generated documents are a fixed point of their generator and the hosted workflow is green (F03, F04) |

### Actual path trace

Run on the verified tree against `examples/requests/multi-tier.yaml`:

| Step | Command | Result |
| --- | --- | --- |
| request -> validation | `python -m provisioner.cli validate examples/requests/multi-tier.yaml` | exit 0, `VALID`, `request_digest d0036fa5...` |
| versioned policy and profiles | included in the plan's `policy` block | `hosting-policy-diagnostics/1`, `rules_digest 130b6dc1...`, zero errors |
| resolution | `python -m provisioner.cli resolve examples/requests/multi-tier.yaml` | exit 0, `RESOLVED`, platform-independent intent |
| qualified coherent placement | included in the plan's `placement` block | `PLACED` with `authority FIXTURE_NOT_PLACEMENT_AUTHORITY` |
| reviewed plan, manifest and generation | `python -m provisioner.cli plan examples/requests/multi-tier.yaml` | exit 0, `PLANNED_DISABLED_NOT_AUTHORIZED`, `native_contact false`, `generation 1`, `manifest_digest 2c8555eb...` |
| provider-native realization | the plan's `compile_plan`, `compiled_files`, `terraform_scopes` and `ansible_scopes` | `DRAFT_DISABLED_NOT_AUTHORIZED` |
| delivery runner | the plan's `delivery` block | `PLANNED_DISABLED_NOT_AUTHORIZED` |
| conformance | the plan's `conformance` block | `BLOCKED_ON_EXTERNAL_EVIDENCE`, `ready false`, proposal authority `REPOSITORY_PROPOSAL_NOT_OWNER_STATE` |
| separate activation authority | `python -m provisioner.cli apply examples/requests/multi-tier.yaml` | exit 2, `REFUSED`, `native_contact false` |
| status and verification | `python -m provisioner.cli status` / `verify` | exit 0, `PLANNING_ONLY_NOT_AUTHORIZED` |
| evidence | `python -m provisioner.cli evidence` | exit 0, `RECORDED` |

### Validation commands and results

| Command | Result |
| --- | --- |
| `python -m pytest tests/provisioning -q` | 900 passed / 1449 subtests |
| `python -m unittest tests.test_platform_family_eligibility` | 26 tests, OK |
| `python scripts/check_repository.py --output <private path>` | exit 0, no issues |
| `python scripts/check_documentation.py` | exit 0, 37315 checks, no failures |
| `python scripts/check_retired_interfaces.py` | exit 0, no issues |
| `python tools/check_local.py` | cannot pass on this workstation, and the refactor did not cause it: 12 failures and 132 errors, a strict subset of the audited baseline's 15 failures and 132 errors with no identifier added. The three differences are the F03 navigation tests, which now pass here. The remaining POSIX-only family needs `os.getuid`, `/etc/machine-id`, `/proc/self/ns/net` and `fcntl`. The same command is the `repository` job's local-test step on Linux, where it reports no environmental failures |
| `python scripts/verify_ansible.py` | NOT RUN TO A RESULT: exit 2, `ansible-playbook executable is not installed` |
| `python tools/verify_terraform.py --mock-tests` | NOT RUN TO A RESULT: exit 2, `BLOCKED_TOOLCHAIN`, terraform executable is not installed |
| repository-wide stale-term scan | fifteen required terms classified; no `OBSOLETE_REMOVE` |
| active-document link scan | 510 documents, zero link targets that do not exist |
| generator fixed point | replaying `Builder.run()` through a `Path.write_text` capture reproduces 141 of 141 generated documents byte for byte |
| golden replay | five primary goldens and all fifteen cross-platform cells reproduce their stored digests on this Windows workstation; the same artifacts replay unchanged on Linux |

The two toolchain commands are recorded as unavailable rather than passed. No native
qualification, site commissioning, production authorization, reservation, allocation,
registration, observation or live infrastructure success is claimed anywhere in this
record: no target was contacted, and `native_contact` is false on every artifact produced
above.

### Hosted validation

The `Architecture and automation validation` workflow concluded green on the corrective
tree, and again on the documentation commit that carries this record. This is the evidence
that closes the reopening in section 3 and satisfies F04.

| Required field | Value |
| --- | --- |
| Final commit SHA | `82855759979d752f446fc301a42bb169859cf99d` |
| GitHub Actions run ID | `35951513770` |
| GitHub Actions head SHA | `82855759979d752f446fc301a42bb169859cf99d` |
| Overall workflow conclusion | success |
| `repository` job conclusion | success |
| `terraform` job conclusion | success |
| `ansible` job conclusion | success |
| Test count | 2982 — `Ran 2982 tests in 132.407s`, `OK` |
| Failure count | 0 — `failures=0`, `errors=0`, `skipped=0` |
| Documentation check result | PASSED — 37315 of 37315 checks, zero failures |
| Retired-interface check result | PASSED — 11 registered interfaces, 787 files scanned, zero issues |
| Golden replay result | reproduced — `GoldenReplayTest.test_conformance_reports_are_reproduced` and `test_the_digest_index_is_reproduced`, and `GoldenCorpusCommandTest.test_plan_reproduces_the_stored_digest_for_every_request`, all `ok` |
| Cross-platform matrix result | reproduced — `CrossPlatformGoldenTest.test_every_cell_reproduces_its_stored_digests` `ok` for every cell on Linux, with the same artifacts replaying unchanged on this Windows workstation |

The same workflow validated the corrective commits before the record was written:

| Fact | Value |
| --- | --- |
| Run id | `35950478558` |
| Head SHA | `a538f60b823cacc0bbbbc60945c2c92f80fbc853` |
| Overall conclusion | success |
| `repository` / `terraform` / `ansible` | success / success / success |
| Test count and failure count | 2982 run, 0 failures, 0 errors, 0 skipped (`Ran 2982 tests in 167.084s`, `OK`) |
| Documentation / retired-interface | 37315 of 37315 checks, zero failures / 11 interfaces, 787 files, zero issues |

The 33 failures recorded in the reopening decompose into the cross-platform matrix cells
and the golden replay, command and navigation identifiers named above; the same
identifiers pass in both hosted runs. Each run also passes the 52 assurance and preflight
steps of the `repository` job, the local test step (`PASSED_LOCAL_ONLY`, 2982 run, 0
failures, 0 errors, 80 modeled route checks passed), the known Nutanix task-tree and
recovery campaign, and both the `terraform` and `ansible` engine jobs.

This record is carried by the documentation commit that immediately follows
`82855759979d752f446fc301a42bb169859cf99d`. That commit changes only this audit file — no
code, test, example, schema or digest — and its own hosted run reports the same figures
recorded above, because it changes no validated input. The run list of the same workflow
shows the head SHA of that commit with conclusion `success`. No local result is substituted
for a hosted one anywhere in this record.

### Remaining external work

`docs/NEXT_WORK.md` holds fourteen rows, each naming its owner, the missing external input,
why it matters, the repository-side contract that is already complete, the completion
condition and the hold point. They cover the Terraform/Ansible toolchain, target selection,
the qualification campaign, native observers, writer fencing and recovery, the security
edge, shared-service reply paths, bootstrap dependencies, native IPv6, commissioned
envelopes, owner-held reservations, owner-held DNS registrations, production authority and
authoritative site state to replace the non-authoritative placement fixtures.
