# P00 scope and journey review

Prepared and desk-reviewed by Codex on 2026-10-04 for **P00.01 / G00.01**, R01 and R36. Accountable product, application, service and records reviewers have not yet been identified or recorded as accepting this baseline. This document is a reviewable scope proposal; delivery state remains in the [canonical register](delivery-register.yaml).

Inputs: [product scope](../product/scope.md), [product overview](../product/README.md), [Permit Desk walkthrough](../product/application-walkthrough.md), [requirements](requirements-and-qualification.md) and the [pinned historical source review](../reference/p00-historical-source-review.md). Current greenfield direction wins over historical implementation choices.

## Recommended baseline for owner review

Use **Permit Desk**, the existing synthetic Linux web-and-database application, as the first repeatable product journey. It exercises application state, attachments, two workload/security placements, tenant isolation, shared services and recovery without using live business data. Freeze its logical contents for design and fixture work; exact platform/guest selections and numerical acceptance targets remain P00.04/P00.05 decisions.

P07 provisions OpenStack through native APIs. P08 selects one explicitly qualified migration method from source and destination capability profiles. Generic whole-VM movement uses an isolated migration copy, `ExportVm`/NFC, verified transfer, any explicitly planned copy-only conversion and destination native APIs. Guest transformation occurs on the copy. Restarting production after a baseline requires a qualified application or file delta method; opaque workloads without one require cold migration. No method is an automatic fallback. Native provisioning and migration require separate Q05/Q06 and Q07 qualification.

| Scope element | Recommended baseline | Required before acceptance |
| --- | --- | --- |
| Product entrypoint | Governed Laravel/Inertia/Vue console calling owned context APIs; normal Laravel capability convention from ADR-024, with no Boost package | Confirm representative operator and application-owner task reviewers |
| Service boundary | Console composition plus Governance, Catalogue, Inventory, Planning, Lifecycle and Assurance; private context state and scoped site workers | P00.02 authority and invariant review |
| Application | One tenant-owned application with Linux web and relational-database workloads; database records plus attachment dataset in an explicit consistency group | Application reviewer approves membership, dependency and data checks |
| Provisioning route | New empty deployment on one commissioned OpenStack target, followed by hardening, policy/service checks, restore and retirement qualification | P00.04 selects exact target, guest, storage/network and service tuple |
| Migration route | Separate VMware deployment rebuilt on OpenStack from reviewed artifacts, with application-consistent capture/restore, source-writer fencing and controlled cutover | New feasibility result and explicit ADR-014 review; no inherited old code, guest tuple, test result or qualification |
| Isolation | Two tenants in negative fixtures; selected application spans presentation/data placements; explicit required and denied flows | P00.02 sharing rules and P00.05 security topology/inspection acceptance |
| Success | Correct application data, usable service and protection, authorized native scope, bounded outage and demonstrable recovery | Approved measurements and actual campaign evidence in later phases |
| Retained old product state | Applicability **unknown**; no actual operational-state inventory supplied | Records-owner inventory and ADR-021 archive/import/non-applicability decision |

The proposed application is a test subject, not a preselected production pilot or an assertion that its topology is already deployed. A different representative workload can replace it through a recorded scope change before test fixtures and public contracts are frozen.

## Persona, scope and observable outcome review

These roles are responsibilities to validate with real prospective users, not assigned people or implemented permissions. Action-level roles and separation of duties are delivered in P02.

| Persona | Concrete task in the first journey | Permitted scope | Observable success / required rejection |
| --- | --- | --- | --- |
| Application owner | Publish Permit Desk workload, dataset, flow, dependency and acceptance intent; review a revision difference | Owned tenant/application and permitted environment; no native write authority from authorship | Complete immutable revision visible; stale edit conflicts and foreign-tenant workload membership are rejected |
| Tenant administrator | Grant and revoke the operator's application/environment actions | Delegable tenant permissions only; cannot enlarge platform or service authority | Effective grant/revocation is attributable; revoked actor cannot create a new privileged admission |
| Platform administrator | Commission source/target endpoints and review read-only inventory completeness | Approved endpoint/native scope and enrolled read identity | Complete fresh generation and missing privileges are visible; discovery changes no native resource or ownership |
| Planner/operator | Compare candidates and propose the exact provision or migration | Authorized application, tenant and candidate endpoints | Explain eligible, blocked and unknown findings from pinned facts; missing mandatory facts prevent operational admission |
| Approver | Review immutable plan, effects, outage, retention and recovery boundary | Assigned change/resource scope and required independent identity | Decision binds digest and window; modified plan, expired decision or disallowed self-approval cannot authorize execution |
| Execution operator | Start admitted job and investigate interruption | Exact approved job/resource scope and allowed recovery actions | Progress distinguishes attempted, observed and held effects; lost acknowledgement cannot trigger a blind repeat |
| Shared-service operator | Confirm IPAM/DNS, identity/time/trust, logs, monitoring and backup readiness | Individually owned service and allocation scope | Current receipts plus functional checks are linked; a generic successful stage cannot accept absent service integration |
| Assurance reviewer | Inspect exact tuple, artifact revision, negatives and recovery dossier | Authorized evidence and qualification decision scope; no native effect authority from review | Supported claim matches observed campaign scope; wrong tuple, simulation and stale evidence cannot qualify it |
| SRE / receiving operator | Install, observe, recover and upgrade the control plane; handle alerts and held jobs | Approved operating/support scope with attributable access | Restore begins safely, alerts reach a responsible receiver, and unresolved native outcomes stay held |
| Records owner | Decide retention of previous intent/state/evidence and source/target datasets | Assigned retention and disposition authority; no implied right to execute old work | Inventory-based decision preserves required originals; archive/import never manufactures current execution authority |

## Journey acceptance cases to carry into implementation

These are desk-reviewed acceptance designs. They have not been exercised in a running application. The walkthrough supplies connected example IDs and detailed effect order; this table defines the observable outcome that must survive implementation.

| Case | User-visible result | Negative or recovery case | Delivery / requirements |
| --- | --- | --- | --- |
| S01 — Define and revise | Owner sees complete workload/data/dependency/security intent and its immutable history | Changed payload with reused idempotency key conflicts; stale ETag cannot overwrite the current revision | P02/P03; R03–R06, R33 |
| S02 — Observe and compare | Operator sees fresh/complete observations and requirement-level explanation across candidates | Partial paging, unknown boot/key fact, wrong tenant, absent qualification or stale observation remains blocked/unknown | P04/P05; R08–R13 |
| S03 — Plan and authorize | Reviewed plan identifies exact objects, allocations, effects, window and recovery decisions | Material intent/input/plan change requires new review; revoked or mismatched approval is denied | P05/P06; R14–R17 |
| S04 — Simulate interruption | Operator sees a stable job and explicit uncertain effect with permitted reconciliation action | Duplicate delivery, restart or lost reply does not create a second native effect; simulation stays visibly synthetic | P06; R15–R17, R29–R30 |
| S05 — Provision useful service | Selected OpenStack deployment supports authorized login/read/write and approved service paths | Unapproved tier/tenant traffic denied; failed restore or missing service readiness prevents acceptance/activation as applicable | P07; R18–R21, R25 |
| S06 — Rebuild and restore all selected data | Reproduced target application preserves approved records, attachments, identities/metadata and application consistency within selected outage/data objectives | Unreproducible configuration, incompatible database/restore version, missing dataset/key, unfenced source writer or failed final validation holds the method/cutover | P08; R19, R22–R23 |
| S07 — Recover across write boundary | Before target writes, prove safe source return; after a target write, preserve accepted changes through the chosen recovery strategy | Never restart stale source as an implicit rollback after accepted target changes; keep unresolved recovery visible | P06/P08; R23–R24, R29 |
| S08 — Operate and retire | Receiving team can investigate evidence, recover the service and carry out separately authorized cleanup | Expired evidence cannot sustain support; source deletion/data disposal need their own retention and authority checks | P10/P11; R25, R29–R35 |

Data acceptance must compare an exact reproducible fixture inventory: permit identities and ownership, row counts, attachment digests, consistency-group membership and selected metadata. After activation, perform a new permitted write and read it back. Check application authorization and required/denied network flows. VM boot, ping or a successful backup job alone is insufficient.

Outage starts and ends at application-observable boundaries chosen by the application owner. Data-loss allowance, service response targets, dataset size/change rate and retained-source period have no accepted numerical values yet. [Operating targets](../product/operating-targets.md) contains candidate control-plane values; those do not become application promises.

For this method, “offline” means the final application quiesce and consistent capture/restore/cutover window. It does not mean copying or converting the complete guest disks. The target can be prepared in quarantine beforehand only through approved, journaled work; target preparation does not authorize production writers or remove the need for final consistency and fencing.

## Release exclusions and visible expansion

| Excluded from the first qualified slice | Treatment |
| --- | --- |
| AHV execution, other directed routes and same-family relocation topologies | Keep represented in the support matrix and P09; qualify each selected combination independently |
| Whole-VM capture/export, conversion and import | P08 native migration copy, explicit method and transformation plan; never an automatic fallback |
| Windows, appliances, GPUs/passthrough, shared disks, unselected encryption/vTPM and other special device profiles | Return explicit unsupported/unknown findings until a selected implementation and qualification campaign exists |
| Warm/live migration, RAM transfer, zero-downtime guarantee and automatic reverse migration | No inferred support from a successful application restore or forward route |
| General brownfield ownership adoption | Read-only discovery and ownership-collision safeguards are early scope; mutation requires separately reviewed transfer and P09 adoption work |
| Automatic migration of old product records, running jobs or approvals | Await inventory/applicability and explicit import design; old records never become new authority merely by conversion |
| A full billing system, general ITSM suite or identity directory | Integrate the required owner contracts without enlarging the product scope |
| Production release from document, local test or simulator success | Native qualification, pilot and receiving-owner acceptance remain separate gates |

## Retained-state decision prepared for the records owner

The previous branch contains archive/rehearsal designs and implementation statements. It does not establish that any organization has deployed that runtime, that operational records exist, or that every previous writer has stopped. Repository examples, synthetic tests and source history are not an operational-state inventory.

The review must inventory old product identities/revisions, approvals/audit history, evidence, workflow/operation journals, allocation/service receipts, native resource custody and native bindings where any exist. Identify custody, tenant/scope, counts, format/version, retention/access duties and active or queued writers. Keep originals and operational secrets in their approved systems; Git stores only the sanitized decision and immutable references.

| Inventory outcome | Required disposition |
| --- | --- |
| No deployed operational state exists | Record the surveyed systems/scopes and signed records-owner finding; only then may R36 receive reviewed non-applicability |
| Historical evidence exists without live execution state | Approve archive/read access, retention and provenance; no executable import is implied |
| Live intent, native bindings, service allocations or uncertain operations exist | Define explicit one-time mapping/reconciliation and observation-only handover; freeze/exclude old writers before any new mutation owner is enabled |
| Inventory incomplete or writer status unknown | Keep applicability unresolved and affected handover scope held; continue unrelated greenfield design/build work |

No outcome in this table has been selected by this desk review. The current recommendation is to preserve the uncertainty and obtain the actual inventory rather than presume an importer or claim there is nothing to retain.

## Finite inputs needed to accept G00.01

| Input | Required answer | Responsible role to identify | Blocking point |
| --- | --- | --- | --- |
| Scope reviewers | Named product/application/service reviewers, the responsibilities each accepts and the independent gate reviewer | Product lead | G00.01 acceptance |
| Representative workload | Confirm Permit Desk or provide replacement membership, datasets, dependencies and correctness checks; identify representative task reviewers | Application owner / product lead | Fixture/public-contract baseline and G00.01 |
| Data and time objectives | Allowed outage/data loss, success measurements, retained-source/target-write recovery constraints and selected workload/load tier | Application owner with SRE and service owners | P00.04/P00.05 acceptance |
| Method and environment | Exact source/target/image/application/database/security/service candidate, reproducible build/configuration and bounded consistent capture/restore feasibility results | Platform / qualification leads | G00.04 and first native planning |
| Retained-state applicability | Inventory-backed archive/import/non-applicability decision with custody and old-writer disposition | Records owner with lifecycle/security owners | G00.01/G00.05 and any state handover |

Role labels are not assignments. No person has been entered as accepting these responsibilities by this document. The current user instruction authorizes implementation work; it does not supply the missing operating identities, site authorization or records inventory.

## What this review establishes

The existing scope and walkthrough form a coherent candidate: the personas have scoped tasks; the first provision/migration paths and exclusions are explicit; data correctness, useful service, tenant isolation and both recovery boundaries have concrete acceptance designs. Historical material strengthens those checks without replacing the new stack, service boundaries or Laravel convention.

G00.01 remains open until the accountable reviewers accept the scope and roster and retained-state applicability is decided or explicitly recorded as an unresolved input under the gate procedure. Update the relevant ADRs and canonical register with the actual review, evidence and remaining dependencies; do not mark P00.01 complete from this desk review alone.
