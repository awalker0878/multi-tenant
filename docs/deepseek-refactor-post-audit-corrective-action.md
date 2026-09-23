# DeepSeek Refactor Corrective Action — Post-Completion Re-Audit

> Status: **ACTIVE CORRECTIVE EXECUTION SPECIFICATION**
>
> Repository: `awalker0878/multi-tenant`
>
> Re-audited head: `469bbd82ac5c02f9f4786bb8c977b095b589b1a3`
>
> Governing specification: `docs/deepseek-master-refactor-provisioning-prompt.md`
>
> Prior completion audit: `docs/deepseek-refactor-completion-audit.md`
>
> Purpose: correct the repository-side defects discovered after the completion audit was marked complete, restore deterministic cross-platform artifacts, bind approval to the actual executable delivery topology, eliminate generated-document drift, and require a green full repository validation before completion is claimed again.

---

# 1. Executive finding

The portable provisioning refactor has made major progress and several previously identified defects are genuinely corrected.

In particular:

- native qualification is now a mandatory placement blocker;
- authoritative inventory cannot use a non-authoritative qualification declaration;
- multi-zone placement selects a coherent site/platform envelope;
- CLI dependency direction was repaired;
- versioned profiles exist;
- a WSD generation model exists;
- capacity/IPAM/DNS owner-boundary code exists;
- adapter contracts were substantially strengthened;
- conformance now distinguishes proposals from owner confirmations;
- the cross-platform golden matrix was expanded;
- Terraform CI passes;
- Ansible CI passes.

However, the refactor **must not currently be described as repository-side complete**.

The current head's GitHub Actions run:

    Architecture and automation validation
    run 269
    head 469bbd82ac5c02f9f4786bb8c977b095b589b1a3

fails in the `repository` job.

The same workflow run proves that:

    terraform job -> PASS
    ansible job   -> PASS
    repository    -> FAIL

The repository job ran:

    2954 tests

and failed:

    33 tests

Those failures are not merely missing local tools. They occur on GitHub's Ubuntu runner with repository dependencies installed.

The 33 failures reduce to three repository-side defects:

1. **30 deterministic/golden failures**
   - 15 full request × platform golden matrix digest failures;
   - 5 CLI plan-digest replay failures;
   - 5 conformance golden replay failures;
   - 5 primary digest-index replay failures.

2. **2 generated navigation mismatches**
   - `docs/engineering/README.md`;
   - `docs/implementation/README.md`.

3. **1 second navigation regression**
   - the task-tree integration check observes the same engineering navigation drift.

A separate architectural inspection also found a high-severity approval-integrity gap:

4. **The approved plan manifest does not bind the actual `hosting-delivery/1` executable topology.**

The manifest currently binds a digest produced by `provisioner.execution.delivery.graph_digest(...)`, while the actual runner topology is defined separately by `provisioner.execution.handoff.STEPS` and is constructed only after the approval digest is checked.

The completion claim must therefore be reopened.

---

# 2. Corrective gate status

Reopen the following prior completion gates:

| Gate | Corrective state | Reason |
| --- | --- | --- |
| C03 — complete reviewed-plan manifest/digest | **INVALID / REOPENED** | approved manifest does not bind the actual executable `hosting-delivery/1` topology |
| C05 — existing delivery-runner integration | **PARTIAL / REOPENED** | handoff exists, but the topology executed by the runner is not the topology bound by approval |
| C10 — cross-platform golden coverage | **INVALID / REOPENED** | all 15 compatible platform cells fail deterministic digest replay on Linux |
| C13 — final documentation/cleanup/validation | **INVALID / REOPENED** | current full repository workflow is red and generated navigation is stale |

Keep C01 and C02 complete unless their tests regress:

- C01 native qualification gating is materially implemented;
- C02 coherent multi-zone/site/platform envelope selection is materially implemented.

Do not reopen other gates merely to create work. Reopen them only if the corrective validation discovers an actual defect.

---

# 3. Defect F01 — Cross-platform plan identity is OS-dependent

Severity: **P0**

Affected prior gates:

- C03;
- C10;
- C13.

Affected master-prompt requirements include:

- deterministic generated output;
- immutable reviewed plan;
- golden contract tests;
- current cross-platform parity;
- final test audit;
- final repository audit.

## 3.1 Evidence

`provisioner/inventory/model.py` currently does:

```python
relative = str(path.resolve().relative_to(ROOT))
```

and then stores:

```python
origin=relative
```

The reviewed-plan manifest includes:

```python
{
    "digest": inventory.document_digest,
    "status": inventory.status,
    "origin": inventory.origin,
    "authoritative": inventory.authoritative,
}
```

The capacity view also includes `inventory.origin`.

`str(Path(...))` is OS-specific:

- Windows repository-relative paths use `\`;
- Linux repository-relative paths use `/`.

The golden artifacts were generated on Windows.

GitHub Actions replays them on Linux.

Therefore the same reviewed inventory document produces different:

- manifest digest;
- plan digest;
- conformance digest;
- cross-platform golden digest;

depending on operating system.

This violates the deterministic artifact contract.

## 3.2 Required correction

Do **not** simply regenerate the golden artifacts on Linux.

Fix the identity model first.

The approval-critical identity of inventory must be independent of:

- host OS path separator;
- current working directory;
- checkout location;
- how the caller spelled the path.

Use a stable logical identity.

Preferred model:

```text
inventory document digest
+ inventory document's declared logical source identity
+ authoritative status
```

The filesystem location used to read the document is diagnostic provenance, not the semantic identity of the inventory.

### Required design

Refactor inventory provenance into two concepts:

```text
logical source identity
filesystem/read origin
```

For example:

```python
Inventory(
    source=document["source"],
    origin=<diagnostic normalized path>,
    document_digest=...
)
```

The manifest should bind:

```text
document_digest
document source
status
authoritative
```

It should **not** bind an invocation-specific absolute path.

If `origin` remains visible in artifacts:

- repository-relative paths must use POSIX `/`;
- external paths must not make the reviewed plan machine-specific;
- absolute temp/workspace paths must never enter approval identity.

A helper equivalent to `reviewed_source()` may be reused, but do not merely normalize an arbitrary absolute external path and then bind it into the manifest.

## 3.3 Required tests

Add explicit cross-platform normalization regressions.

At minimum:

### A. Repository-relative separator invariance

Construct semantically identical inventories whose diagnostic origins are:

```text
provisioner/inventory/fixtures/openstack-reference.json
```

and:

```text
provisioner\inventory\fixtures\openstack-reference.json
```

Assert:

```text
same inventory semantic identity
same capacity view identity
same manifest digest
same plan digest
same conformance digest
```

### B. Absolute-checkout invariance

Simulate the same reviewed inventory loaded from:

```text
C:\repo\multi-tenant\...
```

and:

```text
/home/runner/work/multi-tenant/...
```

The reviewed plan identity must remain unchanged.

### C. Request-path invariance

Preserve the already-added regression that relative, absolute and `..` spellings of the same request produce one plan identity.

### D. Linux/Windows golden replay

Add a focused test whose expected result cannot pass if backslashes enter the approval-critical manifest.

## 3.4 Golden regeneration rule

Only after the identity model is corrected:

1. replay all five reference requests;
2. replay all 15 request × platform cells;
3. regenerate deterministic golden artifacts once;
4. rerun them from a clean checkout;
5. rerun on GitHub Actions/Linux.

Do not accept a fix where regeneration is required on every operating system.

## 3.5 Suggested commits

```text
test(determinism): expose OS-specific inventory provenance
fix(inventory): separate logical identity from filesystem origin
test(manifest): prove checkout and separator invariance
test(golden): regenerate stable cross-platform digests
```

---

# 4. Defect F02 — Approval does not bind the executable delivery topology

Severity: **P0**

Affected prior gates:

- C03;
- C05.

Affected master-prompt requirements include:

- immutable reviewed plan;
- apply exact reviewed plan;
- delivery integration;
- existing runner reuse;
- generation/idempotence;
- no unreviewed execution changes.

## 4.1 Current architecture

Plan creation currently binds:

```python
delivery_plan.graph_digest(state, terraform_scopes)
```

into:

```text
manifest.delivery.graph
```

That digest comes from `provisioner/execution/delivery.py`.

It covers the owner-operation summary.

The actual persistent runner topology is defined elsewhere:

```python
provisioner/execution/handoff.py

STEPS = (
    ...
)
```

The actual `hosting-delivery/1` graph is built later:

```python
graph = handoff_module.build(plan, commit)
```

inside `hosting apply`.

The approved-plan digest is checked **before** that graph is built:

```text
if approved_plan != plan.digest:
    refuse
...
graph = handoff_module.build(plan, commit)
```

Therefore the external approval proves:

```text
reviewed owner-operation summary
```

but does not necessarily prove:

```text
exact ordered executable runner topology
```

A change to:

```text
STEPS
step IDs
step kinds
dependencies
operation -> step mapping
reviewed step parameters
```

can alter execution semantics without necessarily altering the approved plan digest.

That violates the exact-plan requirement.

## 4.2 Required correction

Create one canonical **reviewed delivery topology intent**.

There must not be:

```text
one delivery identity in manifest.py
and
another executable topology in handoff.py
```

Use a single canonical topology source.

Recommended shape:

```yaml
format: hosting-delivery-topology-intent/1

steps:
  - id: admission
    kind: acceptance
    needs: []

  - id: capacity-reservation
    kind: capacity
    needs:
      - admission

operationBindings:
  capacity-reservation: capacity-reservation
  address-allocation: address-allocation
  ...

reviewedParameters:
  admission:
    purpose: admission
  capacity-reservation:
    action: reserve
  ...
```

The canonical object should include every approval-relevant delivery fact that is known before execution.

It must include at least:

```text
ordered steps
step IDs
step kinds
dependencies
operation-to-step mapping
reviewed parameter values
compiled catalog IDs/input identities when known and approval-relevant
```

It must exclude values that are inherently derived after plan identity:

```text
plan digest
operation_id if derived from plan digest
predecessor receipt digests
private file paths
secrets
live owner receipts
```

## 4.3 Required construction order

The dependency must become:

```text
portable plan facts
-> canonical delivery topology intent
-> topology digest
-> reviewed manifest
-> plan digest
-> operation_id
-> execution-time hosting-delivery/1 graph
```

Then the execution-time graph must be a deterministic projection of the already-approved topology.

For example:

```text
approved topology
+ generation
+ operation_id
+ exact source commit
= hosting-delivery/1
```

The execution-time builder must verify:

```text
digest(actual reviewed topology projection)
==
manifest-bound topology digest
```

before producing the handoff.

## 4.4 Source commit rule

Do not create a self-referential Git history loop.

A committed golden plan cannot safely bind `HEAD` if committing that golden plan changes `HEAD`.

The existing delivery runner may continue to bind:

```text
exact clean source_commit
```

at execution time.

The approval model must separately bind the **semantic execution topology/code contract**.

If a separate source-code acceptance record is required, model it as a distinct external authority record rather than making committed golden plan identities recursively depend on the commit containing themselves.

Do not weaken the existing clean-checkout guard.

## 4.5 Required tests

Add regressions proving:

### A. Step dependency changes approval identity

Change:

```text
workload-plan.needs
```

and prove:

```text
manifest digest changes
plan digest changes
```

### B. Step kind changes approval identity

Change:

```text
capacity-reservation: capacity
```

to another declared kind in a controlled test.

The approved digest must change.

### C. Operation mapping changes approval identity

Changing:

```text
native-qualification -> pre-activation-campaign
```

must change the plan identity.

### D. Reviewed step parameter changes approval identity

Changing:

```text
edge-policy.mode
```

or:

```text
capacity-reservation.action
```

must change the plan identity.

### E. Execution graph matches approved topology

For every reference request:

```text
approved topology projection
==
handoff topology projection
```

### F. Stale approval after topology change

An approval produced before a topology mutation must be refused.

## 4.6 Required cleanup

After this change:

- `delivery.graph_digest()` must not remain a parallel topology identity;
- either remove it or redefine it as the digest of the canonical handoff topology intent;
- update `tests/provisioning/unit/test_plan_manifest.py` so `_graph()` uses the canonical topology source;
- update `docs/provisioning/plan-manifest-model.md`;
- update `docs/provisioning/delivery-handoff-model.md`;
- update `docs/provisioning/plan-workflow.md`.

## 4.7 Suggested commits

```text
test(manifest): expose unbound executable topology
refactor(delivery): define canonical reviewed topology intent
feat(manifest): bind executable topology digest
test(apply): refuse topology drift after approval
chore(cleanup): remove parallel delivery graph identity
docs(delivery): document one reviewed topology
```

---

# 5. Defect F03 — Generated navigation source and generated files have drifted

Severity: **P1**

Affected prior gate:

- C13.

## 5.1 Current failures

GitHub Actions currently fails:

```text
test_generated_engineering_navigation_preserves_ipv6
test_generated_implementation_navigation_matches
test_task_and_commissioning_navigation_match_generator
```

The tests compare:

```text
scripts.check_documentation.Builder.navigation()
```

against:

```text
docs/engineering/README.md
docs/implementation/README.md
```

The active README files were manually extended with portable-provisioning links, but the navigation generator was not updated to generate those same bytes.

This violates the repository's generated-document consistency rule.

## 5.2 Required correction

Determine the actual source of truth for these two navigation documents.

If `Builder.navigation()` is authoritative:

1. add the portable-provisioning links to the builder/source data;
2. regenerate the README files from the builder;
3. do not hand-maintain content that the builder will erase.

If the README files are now supposed to be authoritative:

1. explicitly change the architecture;
2. remove generation of those documents;
3. update every regression that treats them as generated output.

Do **not** merely weaken or delete the equality tests.

The likely correct fix is to update the generator because the current repository explicitly treats these files as generated navigation.

## 5.3 Required tests

The following must pass exactly:

```text
tests/test_commissioning_pack.py::
  test_generated_implementation_navigation_matches

tests/test_commissioning_pack.py::
  test_generated_engineering_navigation_preserves_ipv6

tests/test_task_tree_integration.py::
  test_task_and_commissioning_navigation_match_generator
```

Also prove that regeneration preserves:

```text
portable provisioning links
platform capability registry links
native qualification links
pre-placement links
routed IPv6 links
native-reference work package links
```

## 5.4 Suggested commits

```text
test(docs): pin portable provisioning navigation
fix(docs): generate provisioning links from navigation source
chore(docs): regenerate engineering and implementation indexes
```

---

# 6. Defect F04 — Final completion record is contradicted by current HEAD

Severity: **P0 governance/integrity**

Affected prior gate:

- C13.

## 6.1 Current contradiction

The completion audit says:

```text
Status: every repository-side gate C01-C13 is COMPLETE
```

and records:

```text
tests/provisioning -> 875 passed / 1401 subtests
```

But current-head GitHub Actions proves:

```text
repository job -> failure
2954 tests run
33 failures
```

The current completion record is therefore no longer a valid statement about `HEAD`.

The audit may describe an earlier local test subset, but it must not be presented as current full-repository completion.

## 6.2 Required correction

Immediately reopen the completion record.

Change the final completion section to something equivalent to:

```text
Repository-side completion claim suspended by post-completion re-audit.

Reopened:
- C03
- C05
- C10
- C13

Current GitHub Actions full repository validation is failing.
```

Do not mark complete again until the current commit being declared complete has a successful full validation.

The audit should distinguish:

```text
focused provisioning tests
full repository tests
Terraform CI
Ansible CI
documentation/static validation
GitHub Actions overall result
```

Do not substitute one for another.

---

# 7. Required corrective execution order

Execute exactly in this order unless a failing test proves another prerequisite.

## Phase A — Reopen the audit honestly

1. update `docs/deepseek-refactor-completion-audit.md`;
2. mark C03/C05/C10/C13 reopened;
3. record current failed workflow/run evidence;
4. make no false completion claim.

Commit:

```text
docs(audit): reopen gates after post-completion validation
```

## Phase B — Fix OS-independent plan identity

1. add failing deterministic provenance tests;
2. fix inventory logical identity;
3. keep filesystem origin diagnostic-only;
4. rerun focused manifest/golden tests;
5. regenerate goldens only after the model is stable.

Commits:

```text
test(determinism): expose cross-platform inventory origin drift
fix(inventory): make reviewed provenance OS-independent
test(golden): regenerate stable portable digests
```

## Phase C — Bind approval to actual delivery topology

1. add failing topology-binding tests;
2. introduce canonical reviewed topology intent;
3. bind it into manifest;
4. derive actual handoff from it;
5. remove parallel graph identity;
6. update apply verification.

Commits:

```text
test(manifest): expose unbound delivery topology
refactor(delivery): define canonical topology intent
feat(manifest): bind executable delivery topology
test(apply): reject topology drift after approval
chore(cleanup): remove parallel delivery identity
```

## Phase D — Repair generated navigation

1. update navigation source/generator;
2. regenerate files;
3. run exact-equality tests.

Commits:

```text
fix(docs): generate portable provisioning navigation
chore(docs): regenerate active indexes
```

## Phase E — Full validation

Run focused tests first:

```bash
python -m pytest tests/provisioning/unit/test_plan_manifest.py -q
python -m pytest tests/provisioning/unit/test_delivery_handoff.py -q
python -m pytest tests/provisioning/end_to_end/test_golden.py -q
python -m unittest tests.test_commissioning_pack tests.test_task_tree_integration
```

Then:

```bash
python -m pytest tests/provisioning -q
python -m unittest tests.test_platform_family_eligibility
python scripts/check_repository.py
python scripts/check_documentation.py
python scripts/check_retired_interfaces.py
```

Then the full canonical repository test:

```bash
python tools/check_local.py
```

On a suitable Linux environment it must pass.

Also preserve:

```bash
python scripts/verify_ansible.py
python tools/verify_terraform.py --mock-tests
```

The current GitHub Actions run already demonstrates Terraform and Ansible can pass on the hosted runner. Do not regress them.

---

# 8. GitHub Actions is now a required final gate

The refactor must not be marked complete based only on local results.

After pushing the final corrective code:

1. identify the GitHub Actions run whose `head_sha` equals the proposed final commit;
2. require:

```text
Architecture and automation validation -> success
```

3. require all jobs in that run to succeed unless the workflow explicitly contains an accepted non-blocking job;
4. inspect failed logs if anything is red;
5. fix repository-side failures and repeat.

Current reference failure:

```text
workflow: Architecture and automation validation
run: 269
head: 469bbd82ac5c02f9f4786bb8c977b095b589b1a3
repository: failure
terraform: success
ansible: success
```

The refactor cannot return to COMPLETE while the equivalent workflow for the final head is failing.

If the `gh` CLI is available:

```bash
gh run list --workflow validate.yml --branch main --limit 5
gh run view <run-id> --json headSha,status,conclusion,jobs
gh run view <run-id> --log-failed
```

If it is not available, record the exact GitHub run manually after push.

---

# 9. Required deterministic golden acceptance

After F01 is fixed, all of these must pass from a clean Linux checkout:

## Primary reference requests

```text
internal-development
internal-production
multi-tier
recovery-enabled
storage-heavy
```

For each:

```text
request digest
resolution digest
placement digest
desired-state digest
environment digest
manifest digest
plan digest
conformance digest
```

must reproduce exactly.

## Cross-platform matrix

All 15 compatible cells:

```text
5 requests
×
3 platforms
```

must reproduce exactly:

```text
Nutanix
VMware/NSX
OpenStack
```

The six intentionally mismatched declared-platform/fixture combinations per request must continue to produce the recorded explicit refusals.

No cell may claim:

```text
native contact
placement authority from fixture data
production authorization
native qualification
```

---

# 10. Required approval-topology acceptance

After F02 is fixed, prove this invariant:

```text
the delivery topology that an operator can hand to tools/delivery_run.py
is exactly the topology whose semantic digest is bound into the approved manifest
```

The actual runtime graph may additionally contain:

```text
source_commit
operation_id
generation
scope
```

but its approval-relevant topology must be identical.

Required assertion conceptually:

```python
approved = plan.manifest["delivery"]["topology_digest"]

runtime = handoff.build(plan, source_commit)

assert digest(handoff.approval_projection(runtime)) == approved
```

Do not compare only counts or kinds.

Compare the complete approval-relevant topology.

---

# 11. Do not "fix" these issues by weakening tests

Forbidden responses include:

- deleting golden digest assertions;
- excluding `inventory.origin` from tests while leaving plan identity machine-dependent;
- regenerating goldens separately for Windows and Linux;
- removing generated-navigation equality tests;
- marking the GitHub workflow non-blocking;
- changing `tools/check_local.py` to skip provisioning golden tests;
- changing the completion audit to ignore the full workflow;
- claiming the executable handoff is approved merely because every owner operation has a mapping;
- creating a second manifest just for apply;
- creating another delivery runner;
- fabricating native evidence.

Fix the architecture and source-of-truth problems.

---

# 12. Regression protection for the discovered bugs

Add durable tests with names that make the historical defect obvious.

Recommended tests:

```text
test_inventory_semantic_identity_is_path_separator_independent
test_plan_digest_is_identical_across_checkout_locations
test_capacity_view_digest_is_path_independent
test_golden_plan_identity_is_cross_platform

test_manifest_binds_ordered_handoff_steps
test_manifest_binds_handoff_dependencies
test_manifest_binds_operation_step_mapping
test_manifest_binds_reviewed_step_parameters
test_apply_refuses_when_runtime_topology_differs_from_approved_topology

test_generated_engineering_navigation_matches_source
test_generated_implementation_navigation_matches_source
```

Do not rely on indirect coverage only.

---

# 13. Completion audit update requirements

Once all corrective changes pass:

Update `docs/deepseek-refactor-completion-audit.md`.

For reopened gates include exact evidence.

## C03 may return to COMPLETE only when

- manifest is OS-independent;
- all approval-relevant plan facts are deterministic;
- actual executable topology is bound;
- stale approval after topology mutation is refused.

## C05 may return to COMPLETE only when

- one canonical topology owns the execution sequence;
- the actual `hosting-delivery/1` graph derives from that topology;
- existing runner remains the only executor;
- approval covers the topology.

## C10 may return to COMPLETE only when

- all five primary goldens replay on Linux;
- all 15 request × platform cells replay;
- Windows-generated artifacts replay unchanged on Linux or vice versa;
- no OS-specific path is approval-critical.

## C13 may return to COMPLETE only when

- generated navigation matches its generator;
- repository/documentation/retired-interface checks pass;
- full repository tests pass;
- Terraform job passes;
- Ansible job passes;
- current-head `Architecture and automation validation` GitHub Actions workflow is green.

---

# 14. Final validation record

The final completion record must include:

```text
final commit SHA
GitHub Actions run ID
GitHub Actions head SHA
overall workflow conclusion
repository job conclusion
terraform job conclusion
ansible job conclusion
test count
failure count
documentation check result
retired-interface check result
golden replay result
cross-platform matrix result
```

Do not record:

```text
"passed locally"
```

as a substitute for a red hosted workflow.

---

# 15. Small-commit discipline

Keep the corrective history reviewable.

Recommended sequence:

```text
docs(audit): reopen gates after post-completion validation

test(determinism): expose cross-platform inventory origin drift
fix(inventory): make reviewed provenance OS-independent
test(manifest): prove checkout-invariant plan identity
test(golden): regenerate stable portable digests

test(manifest): expose unbound delivery topology
refactor(delivery): define canonical reviewed topology
feat(manifest): bind executable delivery topology
test(apply): reject runtime topology drift
chore(cleanup): remove parallel graph identity

fix(docs): generate provisioning navigation
chore(docs): regenerate engineering and implementation indexes

test(refactor): run final completion regressions
docs(audit): record verified repository-side completion
```

Do not squash all corrective work into one giant commit while executing.

---

# 16. Final stop conditions

Do not stop while any of the following is true:

```text
GitHub Actions Architecture and automation validation is red
any golden digest differs on Linux
inventory path spelling changes plan identity
actual handoff topology can change without plan digest changing
generated navigation differs from Builder.navigation()
C03 is reopened
C05 is reopened
C10 is reopened
C13 is reopened
```

Do not stop at:

```text
analysis
planning
a regenerated golden file
a documentation-only completion statement
focused tests only
```

Continue until the current final HEAD is green.

---

# 17. External boundaries remain unchanged

This corrective work does not authorize live infrastructure.

Continue to distinguish:

```text
repository implementation
repository tests
provider/tool execution tests
native qualification
site commissioning
authoritative reservation
authoritative IPAM/DNS
native observation
production authorization
```

Do not contact or mutate production infrastructure.

Do not invent:

```text
product tuple qualification
capacity confirmation
IPAM confirmation
DNS confirmation
activation authority
recovery evidence
```

The existing external blockers in `docs/NEXT_WORK.md` remain external unless repository-side work is actually missing.

---

# 18. Final instruction to DeepSeek

Read this document completely.

Then read:

```text
docs/deepseek-master-refactor-provisioning-prompt.md
docs/deepseek-refactor-completion-audit.md
docs/provisioning/README.md
docs/provisioning/plan-manifest-model.md
docs/provisioning/delivery-handoff-model.md
docs/provisioning/plan-workflow.md
```

Begin by reopening the incorrect completion claim.

Then execute:

```text
F01 -> F02 -> F03 -> F04 -> full validation
```

Do not merely regenerate outputs.

Do not weaken tests.

Do not create parallel execution mechanisms.

Use:

```text
reproduce
-> fix source of truth
-> test
-> migrate
-> delete superseded identity/path
-> document
-> commit
-> continue
```

When the final code is ready:

```text
push
-> inspect GitHub Actions for that exact head SHA
-> fix every repository-side failure
-> rerun
-> only then mark C03/C05/C10/C13 complete again
```

The final repository must have one coherent truth:

```text
portable intent
-> deterministic reviewed identity
-> qualified coherent placement
-> versioned desired state
-> exact approved execution topology
-> existing delivery runner
-> authoritative owner handoffs
-> independent observation/reconciliation
-> conformance
-> separate activation authority
```

No red workflow may be called complete.
