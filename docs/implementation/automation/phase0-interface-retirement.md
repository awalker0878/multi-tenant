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
| Implicit `lifecycle_stage='prepared'` in `tools/terraform_apply.py:verify_outputs` | Prepared plans and older Terraform output receipts can omit the stage. `tools/lifecycle_transition.py`, `tools/openstack_transition.py`, native modules and their tests also read or emit lifecycle stage; these must be audited together. Retained private operation bundles, inputs, output receipts and ledgers may be affected. | Versioned input/output and attempt receipt contract; an offline importer with a verified native-stage observation, or an explicit `UNRESOLVED` hold when the stage cannot be proven. | **Keep until retained-state conversion.** Enumerate records, validate digests and native IDs, freeze old writers, import and reconcile, then reject absent stage at runtime. Require prepared and bootstrap negative/positive tests plus mixed-old/new-ledger tests. No silent runtime default in the new contract. |
| `provisioner/repository.py:repository_module` and root `sys.path` mutation | `adapters/base.py`, `placement/eligibility.py`, `compiler/environment.py`, and repository validation wrappers import `tools.*` and `scripts.*`. `reviewed_source` and catalog paths assume a checkout root. | Installable runtime package with compiler, validators and reviewed catalog resources under package ownership; build scripts call the package. | Remove after installed CLI and service work outside the checkout, no runtime import of `scripts.*` remains, and reviewed source/catalog digests still match. Do not remove native adapter boundaries. |
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

Lifecycle default and checkout import bridge retirement are gated by the importer
and installed-package work, respectively. The remaining mutation-path retirements
depend on the durable execution service and native route tests. A future release
must update this ledger with the actual state inventory, conversion report and
deletion proof; an unchecked “no consumers” assertion is not a deletion gate.
