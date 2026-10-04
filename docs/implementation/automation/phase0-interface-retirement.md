# Phase 0 interface retirement and retained-state plan

Baseline: audited `main` commit `e5347986cb736df525c1fc3ace100af26d2d4f27`.
This is the B04 inventory for the enterprise workload mobility program. It records
the known callers and persisted contracts before changing the execution architecture.
The repository tree has 1,778 files; the source scan covered every
`provisioner/` file and used repository code search for paths absent from the
working checkout. A release scan over a complete checkout and deployed entry
points remains required before retiring an executable or persisted contract.

## Consumer and deletion register

| Current interface | Known consumers and retained state | Replacement | Removal check and disposition |
| --- | --- | --- | --- |
| `Adapter.placement_shape()`, `network_shape()`, and `to_dict()` | Adapter tests and `docs/provisioning/adapter-contract.md`; no runtime call found in `provisioner/`. Repository code search found no other source consumer. No adapter JSON record is written by this interface. | `placement_contract()`, `readback_contract()`, and `realization_contract()` | **Removed in Phase 0.** The adapter tests now consume canonical surfaces and explicitly assert the old methods are absent. The separate `hosting-platform-adapter/2` marker remains because `provisioner/execution/manifest.py` binds it into approved plan digests; changing that marker would invalidate plan identity and is a separate versioned migration. |
| Implicit `lifecycle_stage='prepared'` in `provisioner/execution/terraform_apply.py:verify_outputs` | Prepared plans and older Terraform output receipts can omit the stage. `provisioner/execution/lifecycle_transition.py`, `provisioner/execution/openstack_transition.py`, native modules and their tests also read or emit lifecycle stage; these must be audited together. Retained private operation bundles, inputs, output receipts and ledgers may be affected. | Versioned input/output and attempt receipt contract; an offline importer with a verified native-stage observation, or an explicit `UNRESOLVED` hold when the stage cannot be proven. | **Keep until retained-state conversion.** Enumerate records, validate digests and native IDs, freeze old writers, import and reconcile, then reject absent stage at runtime. Require prepared and bootstrap negative/positive tests plus mixed-old/new-ledger tests. No silent runtime default in the new contract. |
| Dynamic `repository_module` loader and root `sys.path` mutation | The dynamic loader was used by `adapters/base.py`, `placement/eligibility.py`, `compiler/environment.py`, repository validation wrappers and tests. Owner modules still live in installed top-level `tools.*` and `scripts.*` packages; some owner CLIs still mutate `sys.path` for direct script invocation. `reviewed_source` and catalog paths retain checkout semantics. | Typed repository operations with explicit lazy owner imports, followed by package-owned compiler, validators and reviewed catalog resources; build scripts call the package. | **Dynamic loader removed.** The package boundary still imports top-level owners and some scripts mutate the import path. Relocate those owners, remove the path mutations and verify installed CLI and service outside the checkout before closing B05. Preserve native adapter boundaries and reviewed source/catalog digests. |
| Refusal-only `hosting apply` and `hosting mobility-apply` | `provisioner/cli/main.py` dispatches to `cli/apply.py` and `cli/mobility_apply.py`; tests and operator docs consume handoff payloads. Existing approved plan digests are not authority for a new executor without revalidation. | One application service submits an approved, scoped, idempotent durable job to the execution authority used by both CLI and UI. | Remove handoff-as-success projection only when approved jobs run end to end and refusal cases remain enforced. Reject old request/output formats at mutation entry; retain historical handoffs for read-only audit. |
| Target-only `provisioner/portability/handoff.py` graph | `cli/mobility_apply.py` and migration plan emit a `hosting-mobility-delivery-topology/1` graph; `dataset-restore` exists without source capture/fence activities. Old runner packets and journals can contain the graph. | Directed source and target workflow with native operation IDs, verified source snapshot/export, data transfer, target import/restore, cutover and bounded rollback. | Drain/reconcile old graphs before replacement. Native task and ownership reconciliation must pass for each supported source→target route. No replacement graph may rely on a target-only packet to claim migration. |
| Independent local delivery runner | `tools/delivery_*.py` and owner packets/journals supply existing stage execution and recovery; CLI handoff advertises it. Private journals and uncertain started attempts are durable facts. | Durable workflow plus transactional native-operation intents and site-local workers, one authority per resource/scope. | Freeze old submissions; drain or reconcile every in-flight operation, map journals to immutable audit evidence and acquire new ownership epochs before enabling writes. Prove a crashed worker cannot duplicate mutation. |
| Restic restore scoped to target | `provisioner/portability/data.py` emits `delivery_kind=restic` and restore, consumed by mobility handoff and `tools/restic_*.py`; existing owner packets bind a single execution scope. | Explicit source repository → transfer → destination relationship, with source and target tenant/WSD authorization and snapshot provenance. | Same-scope restore and authorized cross-scope restore pass; foreign source/target scope refuses; encrypted snapshot digest, native destination and dataset completeness are verified. Retire single-scope packet format only after record inventory/import. |
| Caller-supplied generation | `cli/main.py` defaults `--generation` to 1; plan, status, apply, evidence and mobility handoff bind the caller claim. Historical plan identities contain the generation. | Server-held immutable workload/WSD revision with compare-and-swap and separate idempotency key. | Stale revision cannot reserve, approve, submit or resume. Import prior generation identity into history without assigning it current authority. |
| Synthetic CLI status | `cli/status.py` recomputes planning stages from a fresh plan and reports later stages held. CLI and tests consume `hosting-status-result/1`. | Read authoritative job/event projection keyed by organization, workload, operation and revision. | Restart worker/API and verify CLI/UI agree with persisted execution events, including unknown outcomes and native reconciliation; reject old status projection as live job state. |
| Fixture defaults in executable paths | `cli/main.py` defaults inventory to reference fixture; `provisioner/inventory/fixtures/` contains mock IDs. Tests/examples depend on explicit samples. | Explicit production site inventory, observed capability evidence and commissioned endpoints; offline examples select fixtures explicitly. | A production execution request with absent endpoint/inventory fails before job admission. Fixture IDs never reach a native packet. Preserve fixtures for isolated tests. |
| Superseded completion narratives and old aliases | `README.md`, active docs and `provisioner/retired_interfaces.json`/checker carry current and retired names. Old documents can be retained as historical records. | One capability ledger and route/release matrix stating observed evidence and supported execution directions. | Documentation checker confirms advertised status matches tests/native evidence. Old invocation/schema is rejected by mutation API; audit viewer may still render immutable old evidence. |

These are distinct migrations. An adapter that translates a portable intent into
a provider's native identifiers is a required boundary. A strict safety hold for an
unobserved native task is likewise required; neither should be deleted as a “shim.”

## Retained-state inventory and conversion

Before any format or execution-authority cutover, take an immutable inventory per
organization, tenant, WSD/workload, environment, platform and owner scope:

1. Enumerate private `bundle.json`, `inputs.json`, `outputs.json`,
   `transition.json`, approval and result files, Terraform state identifiers,
   `*.started.json`, `*.result.json` and `head.json` under each ledger scope.
   Include delivery journals, reservations, IPAM/DNS records, backup snapshot IDs,
   native task IDs and source/target migration packets. Record file digest, schema
   marker, generation, native identity, owner and observed completion status.
2. Freeze old write entry points and establish a reconciliation boundary. Every
   started operation without a complete outcome is `UNKNOWN`, not failed or safe
   to retry. Query the native platform and authoritative owner before assignment.
3. Create a one-time importer that accepts only explicitly enumerated old schemas.
   Validate signatures/digests and exact scope; preserve original bytes as historical
   evidence. Map records into the new database and workflow history with a
   source-record digest. Require native confirmation before deriving missing
   `lifecycle_stage`; hold unresolved records for manual reconciliation.
4. Report per-scope source/import counts, digest and native-ID matches, duplicate
   IDs, reservations, backed-up data objects and unsettled jobs. A mismatch blocks
   new mutation for that scope. Re-importing the same source digest must be
   idempotent.
5. Start the new service in observation mode; compare state and ownership epochs.
   Enable writes only after scope-by-scope acceptance. Remove old readers and write
   routes in the same release. Historical records remain immutable and read-only.

## Phase 0 validation and next gates

The adapter projection removal is covered by
`python -m unittest tests.provisioning.adapters.test_adapter_contract tests.provisioning.adapters.test_adapters`.
An integration scan on the full checkout must also search method references in
`provisioner/`, `tools/`, `scripts/`, `tests/`, web/API clients, generated
contracts and documentation. The manifest term's format and digest remain stable.

Lifecycle default and remaining checkout import retirement are gated by the importer
and package-owned runtime work, respectively. The remaining mutation-path retirements
depend on the durable execution service and native route tests. A future release
must update this ledger with the actual state inventory, conversion report and
deletion proof; an unchecked “no consumers” assertion is not a deletion gate.

## Package-owner retirement checkpoint — 28 September 2026

Capability-registry and native-qualification validation now live in
`provisioner/qualification/registry.py` and `provisioner/qualification/native.py`.
Their former script files were deleted, not replaced by imports, redirects or
wrappers. Runtime imports, CI commands, task metadata, source references and
documentation now use the package owners; the retired-interface register forbids
restoring the old files. Installed-distribution checks verify that the old imports
are absent and the new owners execute from the installed package.

This closes the relocation of these two owners, **not all of B05**. Other compiler,
execution and evidence owners still reside in top-level packages. The conversion
and independent reconciliation conditions above still apply before removing a
runner with retained state or a potentially active native task.

### Complete qualification dependency closure

The installed qualification package also owns version/source provenance, native
target selection and campaign evidence. Its five modules (`registry`, `native`,
`provenance`, `target_selection`, `campaign`) contain the implementations, not
forwarding wrappers. Every in-tree caller and CLI was migrated; the five old
script paths are prohibited by the retirement register. Architecture tests reject
any package qualification import back into `scripts` or `tools`, and the installed
wheel check requires all five owners to resolve outside the source checkout.
Other execution owners and retained-state conversion remain separate B05 work.

### Package-owned WSD compilation

The implementation formerly at `provisioner/compiler/wsd.py` now lives at
`provisioner/compiler/wsd.py`; its native component map lives at
`provisioner/compiler/components.py`. All in-tree imports, current commands,
architecture links, packaging requirements and tests were migrated. The old file
is deleted and prohibited by the retirement register, not retained as a wrapper.
The build-only composition renderer consumes the same package declaration. The
compiler no longer imports `tools`, `scripts`, a networking observer or a path
bootstrap. Its private JSON-file boundary rejects duplicate keys, non-finite
constants and inputs exceeding 4 MiB before creating output.

Native input shapes, disabled Terraform inputs, state keys and generated resource
bytes are unchanged by relocation. Installed-wheel checks block all `tools` and
`scripts` imports while importing the compiler and loading native declarations
for all three platforms and both phases. Existing compiled plans remain disabled;
this code ownership change does not migrate retained execution state, reauthorize
old plans or close the rest of B05.


### Package-owned Terraform catalog — 1 October 2026

The implementation formerly at `provisioner/execution/terraform_catalog.py` now lives at
`provisioner/execution/terraform_catalog.py`. Preparation, engine verification,
repository validation and all in-tree imports use that owner directly. The old
module is deleted and registered as retired, not replaced by a forwarding alias.
The installed reader resolves only package-owned assets and runs with legacy
`tools`/`scripts` imports blocked. Catalog/configuration bytes, ordering, provider
locks, profiles and golden plans are unchanged. Invalid or ambiguous source inputs
now fail before selection; see the [catalog runtime contract](../../engineering/terraform-catalog-runtime.md).

Incremental builds reconstruct the existing Python package trees, removing deleted
owners and orphaned bytecode from reused staging. Source-overlapping destinations
are refused before cleanup. This is not an in-place deployment, state conversion,
source-approval renewal or completion of the rest of B05/B48. Other real runtime
owners remain in the top-level packages; their active consumers and retained state
must be migrated before deletion.

### Package-owned reservation evidence — 2 October 2026

The implementation formerly at `provisioner/allocations/reservation_evidence.py` is now
`provisioner/allocations/reservation_evidence.py`. All in-tree imports, CI commands,
metadata, generator links and tests use the new owner; the old path is prohibited
without a wrapper. The independent retirement test includes this path explicitly alongside the other retired owners.
Installed tests reject legacy imports and stale bytecode while preserving the existing
export schema, canonical digests and reconciliation requirements. See the
[read-only evidence boundary](../../engineering/reservation-evidence-runtime.md).

This move does not import private reservation state, grant ownership, reauthorize
old plans or complete the remaining direct execution owners and retained-state conversion.


### Package-owned IPAM allocation evidence — 2 October 2026

The implementation formerly at `provisioner/allocations/ipam_evidence.py` is now
`provisioner/allocations/ipam_evidence.py`. Reservation/IPAM preflight, DNS evidence,
repository adapters, CI commands and tests use the package owner directly. The old path
is deleted and prohibited without a wrapper. Installed checks require the package module,
refuse working-directory fallback and remove stale script/bytecode from reused builds.
The allocation-index format, confirmation digest and release/quarantine semantics remain
unchanged. See the [IPAM evidence contract](../../engineering/ipam-evidence-runtime.md).

This is read-only exported evidence. It does not import private IPAM state, reveal or
assign address values, write DNS, release capacity or close B23/B48.

### Package-owned source-integrity verification — 2 October 2026

The active clean-source verifier now lives at `provisioner/execution/source_integrity.py`.
All executable callers use that owner directly; `provisioner/execution/source_integrity.py` is deleted and
registered as retired without a forwarding module. Checkout verification pins one Git
HEAD, rejects changed tracked/untracked/staged bytes, disables ambient Git replacement,
fsmonitor and configuration overrides, and rechecks HEAD after bounded reads. Exported
source trees use only an explicitly supplied SHA-256 manifest; there is no historical-
manifest or working-directory fallback. Installed execution without an explicit checkout
fails closed. This establishes source-byte consistency only, not signer trust, approval,
native qualification or retained-state conversion. Other B05 runtime owners remain.

### Package-owned implementation input review — 3 October 2026

The implementation formerly in `provisioner/execution/input_review.py` now lives at
`provisioner/execution/input_review.py`. Route-record review, tests, installed-package
checks and active documentation migrated to the package owner. The old path is deleted
and prohibited without a forwarding module. This is read-only input validation; it
converts no retained state and grants no target, address-allocation or execution
authority.

### Package-owned operator files and readback primitives — 3 October 2026

The actual `readback_core`, exact-ID `neutron_observe`, private `run_files` and
`route_record_review` implementations now live under `provisioner.execution`.
Every active import, command, source link and validation consumer migrated; the
four old tool paths are deleted and independently registered as retired. Installed
checks block legacy imports and require all owners in the wheel; reused staging
cannot retain their old source or bytecode. The route reviewer has no standalone
import fallback.

Scope, digest, file/ledger formats, transport allowlists, explicit target-contact
opt-in and uncertainty rules remain unchanged. This is implementation ownership,
not a retained-state importer, distributed fence or native acceptance. B05 remains
open for the dependent execution owners, installed service composition and retained
state conversion. See the [runtime owner contract](../../engineering/operator-readback-runtime.md).

### Package-owned saved-plan and lifecycle chain — 3 October 2026

Seven actual implementations now live under `provisioner.execution`: `plan_review`,
`flow_policy`, `openstack_transition`, `lifecycle_transition`, `terraform_run`,
`terraform_apply` and `wsd_handoff`. Imports, current commands, source links,
qualification/recovery/delivery consumers and sealed guest snapshots migrated
together. Their former tool paths are deleted and independently prohibited; no
forwarding modules, standalone import fallback or `sys.path` mutation remain.

Installed preparation/apply require an explicit `--source-root` and refuse absent
checkout selection before private inputs or target effects. Source development
uses only the marked source root. Package-owned Python/data and bundled execution
resources must match that selected checkout, including exact code/resource sets,
bounded no-follow reads and referenced evidence documents. A clean unrelated
checkout cannot be attributed to a different running package. This is byte
consistency under trusted custody, not signer trust or hostile-writer exclusion.

Existing plan, transition, approval, output, attempt, ledger and handoff formats,
digests, implicit retained-stage behaviour and uncertainty rules are unchanged.
Prepared/bootstrap default retirement still requires B48 retained-state conversion.
The saved-plan operator remains the existing authorized owner; relocation does not
compose the admitted control-plane workflow or qualify a native route. B05 remains
open for guest/transfer/native-operation and other execution owners, deployed
service composition and actual retained-state conversion. See the
[saved-plan runtime contract](../../engineering/saved-plan-runtime.md).
