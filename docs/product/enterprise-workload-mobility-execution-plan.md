# Enterprise workload mobility: execution plan for all waves

**Baseline:** `main` at `3cbc0c1e1e52a4bedd70972b05b04ccec48de699`, reviewed 28 September 2026.
**Purpose:** complete the repository implementation, then qualify and release the declared platform and migration matrix.
**Status:** Waves 0 and 1 delivered substantial foundations; B05 remains open, Wave 2 is partial, and Waves 3–6 require implementation.

This is the current execution addendum to the [historical audit and implementation plan](enterprise-workload-mobility-audit-and-implementation-plan.md).
Preserve that audit's revision, findings and evidence. Its September 26 baseline must not be presented as the current code.
The B01–B50 identifiers remain stable. This addendum refines their sequence and completion evidence rather than replacing them with a second backlog.
The older W01–W29 automation ledger and C01–C13 interface-refactor gates describe earlier scopes; neither closes this product programme.

## 1. Completion rules and current position

Track each B item through four distinct columns in the delivery ledger: repository implementation, automated verification, native qualification and operational acceptance.
For every completed column retain the source/artifact revision, test or campaign reference, scope, result and unresolved limitations.
Use `NOT_STARTED`, `IN_PROGRESS`, `VERIFIED` or `NOT_APPLICABLE_REVIEWED` for each column; never infer one column from another.
An unchanged historical acceptance result is not evidence for a later implementation revision or installed product tuple.

At this baseline, merged PR #51 records the product/schema/package foundation, #52 the control application and worker foundation, and #53 partial discovery/comparison.
Their recorded CI results support their stated implementation boundaries. Required CI must run again for changed delivery revisions.
No route has been qualified by this review, and no native platform, credential, workload or production data has been contacted.
An API returning a hold, a model accepting a fixture, or a handoff naming a native operation does not implement that operation.
Conversely, absent native access does not prevent writing, integrating and testing the missing repository components.

The supported product remains one authenticated control application with tenant-scoped state, durable workflows and narrowly scoped site workers.
Terraform, native APIs, Ansible and service owners are execution mechanisms behind that authority.
Keep exact native identity, approved immutable plans, one writer per owned resource, uncertainty holds and independently verified postconditions.
Do not remove these controls as “shims.” Remove obsolete representations and competing mutation entry points after verified consumer and state migration.

### Implementation checkpoint after the baseline

The B01–B50 table below remains a historical snapshot of `3cbc0c1e`; these
subsequent changes refine the remaining work without changing that baseline.
Required checks and native qualification must still bind the final delivery revision.

- B05 now packages reviewed planning/compiler/catalogue assets privately through
  `hosting_resources`, with one selected resource root and installed wheel/sdist
  checks against checkout fallback and stale build layouts. Generic `tools` and
  `scripts` runtime owners and source-bound execution still keep B05 open.
  The actual WSD compiler and component declarations are now package-owned; its
  old executable was deleted, callers migrated, and isolated compiler imports
  reject legacy owner dependencies. Generated native inputs and resources retain
  their existing identities. This relocation does not close retained-state work.
- Wave 2 now has a separate signed campaign/result mTLS listener, independent
  native credential witnesses, original signature custody before publication,
  and isolated ingest SQL roles. Durable signed installed-tuple, directed-route
  and control inputs feed generation-pinned normalization and the scoped compare
  API, portal and CLI. Tests cover signature/revocation negatives, actual local
  TLS, real PostgreSQL role/RLS and publication, API access and stale UI state.
  Conflicting VM/NIC/quota facts remain unknown; duplicate native scopes cannot
  pad destination counts, and superseded generation pins cannot retain current
  eligibility. Native collector/profile and
  credential wiring, complete fact coverage, persisted owner/dependency review,
  scheduling and estate qualification still keep Wave 2 partial.
- B24's lower-level delivery path now includes bootstrap prepare/plan/apply and
  native readback, with typed native lifecycle dispatch and per-VM fenced power
  handling. The admitted Temporal workflow does not yet drive the complete
  native provisioning, guest, service and activation chain.
- B30/B31 now guard cross-scope source/destination authority, retain original
  source receipts, and enforce exact canonical dataset coverage and complete
  consistency-group joins. Mutation-worker composition remains missing: an
  independently observed target dataset/root binding, a trusted adapter from
  mTLS worker identity to transfer authority, qualified dynamic repository
  credentials, and independent filesystem observation/old-writer exclusion for
  native intent reconciliation. A `targetRef` is neither a native ID nor a path.
  Persisted transfer identity must remain separate from expiring attempt grants.
- Source fencing, final sync/cutover, post-write recovery, route expansion and
  most Waves 4–6 implementation and release acceptance remain open. No local
  fixture, synthetic benchmark or passing CI result establishes native support.

### Capability/profile and architecture alignment — 28 September 2026

This review used `implementation/all-waves` at
`e40489cf9177d1689a8c49dec5d427ff4ab36431` as the implementation source, against the
unchanged B01–B50 baseline above. It does not promote the baseline table into a
claim that all work is now complete.

The platform registry now explicitly covers 97 dimensions across compute, storage,
network, security, guest, discovery, migration, services and operations. A single
package-owned vocabulary and digest replace duplicated network-only lists. Registry
format 2 rejects omitted rows and the older incomplete format. Newly enumerated
features remain unassessed; all installed tuples remain unselected and all native
claims remain unqualified until independently demonstrated.

Compute/storage/recovery/service profile requirements now participate in placement.
Every selected profile's limitations survive resolution. Strict catalogue parsing
rejects duplicate properties, malformed identities/requirements and unknown
capabilities. Updated catalogue/profile versions and regenerated five-request,
three-platform examples remain disabled, non-authoritative fixtures. Existing
approved plans require reassessment, not reinterpretation under the new digest.

Registry and native-dossier validators now live in `provisioner.qualification`.
Their former script files were deleted, their consumers migrated and their absence
covered by retirement/installed-distribution checks; no compatibility wrappers were
left. Other runtime owners and retained execution-state conversion keep B05 open.

The maintained RAD, TAD, internal/public solution, interface and transition records
are revised together, with explicit control-application, discovery, authority,
profile, transfer and recovery boundaries. Obsolete increment-only current-scope
and next-work narratives are replaced by the B01–B50 scope. Frozen source
transcriptions and signed historical evidence are preserved as history.

This slice does not complete admitted provisioning, transfer-worker composition,
source fencing, final sync/cutover, post-write recovery or the native route/release
campaigns. Their implementation and qualification requirements remain open below.

## 2. Corrected dependencies and delivery order

| Correction | Required sequence and reason |
|---|---|
| B05 is not a completed prerequisite | Continue B05 in parallel with Wave 2. Finish package-owned runtime/import and reviewed-resource handling before calling the installed execution service complete; do not undo the working installed planning/API foundation. |
| Discovery needs its own authority | B14–B16 require campaign admission, enrolled collector identity, current issuer/revocation state, independently witnessed read credentials and authenticated ingestion. B10's job-bound owned-object grant is not brownfield enumeration authority. |
| Environment selectors are not evidence | Admit an installed tuple only from verified provenance. Do not construct tuple or capacity qualification from `EnvironmentRegistration`, a platform family, fixture IDs or an operator-supplied success flag. |
| Comparison needs durable inputs | Finish trusted inventory publication and generation-pinned normalization before B19/B20 production comparisons; persist route claims and control findings before assembling trusted engine inputs. |
| Planning and execution qualification differ | B18 comparison claims never grant mutation. B23/B24 need current action qualification, commissioned capacity and approved ownership/authority for the exact installed destination tuple. |
| B23 protects all native creation | Reserve capacity, IPAM, staging, snapshots and retained-source footprint before the relevant B24/B31/B38 effect; confirm observed resources before speculative leases can expire or release. |
| Native effects require immediate rechecks | Recheck grants, approval/revision, worker epoch, fencing and qualification immediately before each new effect; an earlier successful workflow gate is insufficient. Reconcile accepted work after revocation. |
| Provisioning has explicit postconditions | Prepare → saved plan → review/approve → apply → observe → power/readiness → guest → service checks → controlled activation. A transition draft or Terraform exit code cannot satisfy later state. |
| B37 uses a bounded vertical slice | Implement selected VMware-source/OpenStack-target/Linux application portions of B25–B35 first. Broader AHV/Windows/appliance obligations remain explicit and cannot delay that first complete slice unnecessarily. |
| Minimum operation safety precedes pilot writes | Deliver the required B44 recovery, B45 observability and B46 privilege/evidence controls for the selected slice before B37 native mutation; complete enterprise breadth later. |
| Retirement has separate authority | Target activation does not authorize source deletion, IP release or data disposal. B29/B35/B48 require retained-data decisions, observed cleanup and reconciliation. |
| Route expansion is directional | B38–B42 require independent method, guest, source-exit, target-operate, policy, data and recovery evidence. Never infer reverse or same-family support. |
| Final qualification must cover final code | Design/import conversion early. Rehearse B48 before final B47 release campaigns; rerun affected qualification after deleting old paths. B49 follows that final state, and B50 follows pilot acceptance. |

## 3. B01–B50 baseline and remaining deliverables

“Delivered” below identifies repository evidence at the baseline, not production acceptance. “Partial” includes useful earlier tools that are not integrated into the new product path.
Each row names the remaining repository work separately from external or native acceptance. None of the latter may be fabricated to make a wave appear complete.

### Wave 0 — Product mandate, contracts and packaging

| ID | Baseline | Repository completion deliverable | Native/external gate |
|---|---|---|---|
| B01 | Delivered | Preserve format rejection regression and required CI; bind every new result to its tested revision. | No native qualification claimed by CI. |
| B02 | Delivered | Maintain adopted product, workload/WSD and state/authority ADRs; keep active claims aligned with this ledger. | Service owners adopt their operating scope before release. |
| B03 | Delivered foundation | Extend canonical workload/application, observation, plan, transfer and activity contracts as actual execution needs arise; retain strict versioning and unknown facts. | Native identities and observations must be independently verified. |
| B04 | Delivered register/design | Maintain named consumers, replacement, conversion and deletion tests for every retained legacy path. | Obtain actual retained-record inventory before conversion. |
| B05 | Partial | Move runtime owners out of top-level `tools`/`scripts`, remove runtime path mutation and checkout assumptions, package reviewed resources; run installed service/worker outside checkout. | Qualify signed/offline artifact supply and installed custody at selected sites. |

Wave 0 closes when B05 passes installed-runtime acceptance and active documentation no longer calls the foundation a complete executable product.

### Wave 1 — Control application and durable worker foundation

| ID | Baseline | Repository completion deliverable | Native/external gate |
|---|---|---|---|
| B06 | Delivered foundation | Retain PostgreSQL tenant RLS, ownership, immutable audit, migration/concurrency and restore regressions; extend schemas through new immutable migrations. | Deploy and qualify actual role separation, HA, backups and restore custody. |
| B07 | Delivered foundation | Preserve pinned OIDC, signed IAM provenance, distinct approvals, scope/revision binding, step-up and revocation; reuse for later product commands. | Enterprise IdP/IAM, issuers, grants and revocation behavior qualified. |
| B08 | Delivered foundation | Preserve selected self-hosted Temporal, crash/replay and build-version routing; add real provisioning/migration histories to replay tests. | Selected deployment's mTLS, network, HA, retention, upgrades and DR accepted. |
| B09 | Delivered foundation | Extend transactional outbox, immutable workflow/run binding and job projections to new workflow stages without alternate submitters. | Prove deployed recovery does not lose accepted intent. |
| B10 | Delivered foundation | Extend enrolled workers and credential broker with separate discovery campaigns and explicit platform-action allowlists. | Qualify PKI/CRL, Vault roles, native privileges and credential lifetime. |
| B11 | Delivered foundation | Extend resource/operation leases, uncertainty registry and containment to planned resources and each new native side effect. | Independently demonstrate writer exclusion and operation visibility on selected tuples. |
| B12 | Delivered foundation | Extend the same portal and thin CLI with comparison, provisioning, migration and explicit recovery actions. | Sysadmin pilot verifies scope, usability and actual job visibility. |
| B13 | Delivered foundation | Preserve signed audit checkpoints, Object Lock/Vault adapters, redaction and startup/write holds; add transfer/image artifacts and evidence retention. | Actual signing custody, retention enforcement and independent recovery verified. |

Wave 1's existing repository boundary is verified in PR #52. Later native workflows extend it; they must not reinterpret its initial gate-only workflow as completed provisioning.

### Wave 2 — Trusted discovery and useful destination comparison

| ID | Baseline | Repository completion deliverable | Native/external gate |
|---|---|---|---|
| B14 | Partial | Wire authorized VMware collector transport to campaign ingestion; normalize VM/device/network/storage facts; preserve scope, pagination and identity history. | Reconcile with independent enumeration; qualify folder/privilege coverage and visible-list limits. |
| B15 | Partial | Wire pinned AHV/Prism read profile, complete VM/disk/NIC/network and selected capacity facts, and authenticated publication. | Qualify installed API/profile, paging/count semantics and least-privilege coverage. |
| B16 | Partial | Wire project-scoped Nova/Cinder/Neutron/image/quota reads; correlate IDs, reject cross-project results and publish verified generations. | Qualify actual catalog endpoints, versions, read roles and service visibility. |
| B17 | Partial grouping model | Persist attributed enrichments, reviewed application membership, owner/dependency and consistency-group decisions with unknowns visible. | Application owner confirms dependencies and useful-service acceptance criteria. |
| B18 | Partial pure catalogue | Persist independently verified installed tuples, directed route/action claims, evidence digests, expiry, supersession and revocation. | Source-exit and destination-operation campaigns independently qualify advertised scope. |
| B19 | Partial pure engine | Build trusted generation-pinned inputs from storage, perform scoped reads, retain assessments and expose reasons/remediation/confidence through service APIs. | Reviewed policy, security, recovery and target-capacity evidence for positive candidates. |
| B20 | Partial inventory UI | Add workload details, application grouping and comparison of at least two authorized destinations to portal and CLI; handle stale selections/results. | Sysadmins complete comparison without hand-authoring JSON. |
| B21 | Partial proposal model | Persist no-change import proposals, ownership collisions, review state and links to exact observations; execution stays separately approved. | Native no-change/state reconciliation before ownership transfer. |
| B22 | Partial budgets/paging | Implement bounded scheduling, per-endpoint rate/concurrency limits, resumable generations, freshness monitoring and a reproducible estate benchmark. | Independent omission/privilege-loss reconciliation and agreed estate-scale measurements. |

Wave 2 exits with a deployed-capable read-only slice from campaign admission to scoped comparisons. Unknown evidence produces a usable `UNKNOWN` result, never invented eligibility.
Native B14–B16 acceptance and positive qualified destination claims remain separate from local service integration tests.

### Wave 3 — Complete provisioning and usable services

| ID | Baseline | Repository completion deliverable | Native/external gate |
|---|---|---|---|
| B23 | Earlier owner tools | Integrate transactional reserve/renew/confirm/release with product jobs, commissioned envelope digests, IPAM and per-site/staging budgets. | Authoritative owner receipts, actual capacity and observed cleanup before release. |
| B24 | Earlier engine/runner tools | Implement typed durable prepare/plan/approval/apply/observe/power stages with sealed inputs, ownership and interrupted-effect reconciliation. | Real prepared destination reaches observed guest readiness on selected tuple. |
| B25 | Partial platform contracts | Realize explicit multi-VM/disk/NIC mappings, storage placement, boot mode and addressing; reject unsupported layouts before mutation. | Native disk/NIC/order/IP/boot observations match approved intent. |
| B26 | Bounded Ubuntu tooling | Implement selected Linux profiles, Windows and explicit no-guest-mutation appliance profiles; bind image, driver, identity and readiness checks. | Qualify each advertised OS/image/profile and supported mutation boundary. |
| B27 | Policy contracts/tools | Capture required source controls, compile policy IR and platform realization, retain equivalence findings and block unimplemented mandatory controls. | Independent positive app-flow and negative isolation/bypass tests. |
| B28 | Earlier service tools | Integrate DNS, identity, time, trust, logging, monitoring, backup and activation with actual owner receipts and failed-exposure containment. | Useful-service acceptance, reply paths and application-consistent restore pass. |
| B29 | Earlier lifecycle/retirement tools | Expose managed resize, power, recovery and retirement through the same durable authority; reserve growth and track retained data/cleanup. | Test native changes, failure holds, disposal and capacity/address release. |

Wave 3 exits when an approved product job provisions and commissions a useful service and safely reconciles interruption. Hidden manual scripts cannot complete an otherwise successful job.

### Wave 4 — First application migration

| ID | Baseline | Repository completion deliverable | Native/external gate |
|---|---|---|---|
| B30 | Contract foundation; integration gap | Repair restic cross-scope execution with explicit source repository/snapshot, dataset, target and transfer authorization; preserve original source receipt. | Real authorized foreign-target restore with wrong-scope/dataset/key negatives. |
| B31 | Not integrated | Execute one child per dataset with immutable mapping, integrity/metadata validation, consistency joins, checkpoints and enforced bandwidth/IOPS/staging limits. | Verify every declared dataset and measured transfer behavior. |
| B32 | Not integrated | Provision isolated rehearsal topology, suppress production writers/business side effects and retain cleanup evidence. | Demonstrate isolation against actual identity, routing and application integrations. |
| B33 | Not integrated | Add route-specific quiesce/fencing owners, current independent exclusion readback and fail-closed restart/reconnect handling. | Native source/other-writer exclusion survives selected failure scenarios. |
| B34 | Not integrated | Orchestrate final sync, data acceptance, DNS/LB/traffic switch, target activation and useful-service checks with measured timestamps. | Meet approved outage/data objectives with one accepted writer. |
| B35 | Not integrated | Separate pre-target-write rollback from post-write reverse-sync/restore/forward repair; account for committed target data and source retention. | Rehearse both failure classes and useful source-return recovery. |
| B36 | Not integrated | Add saved-plan/rehearsal/cutover views, precise holds and only currently authorized recovery actions to portal/CLI. | Sysadmin performs selected migration without inventing authority packets. |
| B37 | Not started | Deliver reproducible native campaign harness for discovered VMware Linux application → OpenStack rebuild/restore, including interrupted execution. | Actual application/data, policy, backup, measured cutover and source-return accepted. |

Wave 4 closes only after B37's actual selected-route campaign. Repository integration may finish earlier with the route still unavailable for execution.

### Wave 5 — Whole-VM movement and initial route breadth

| ID | Baseline | Repository completion deliverable | Native/external gate |
|---|---|---|---|
| B38 | Not integrated | Implement cold capture/export, disk-chain manifest, isolated conversion, guest remediation and target import; reject unknown devices/encryption/boot dependencies. | Selected Linux and Windows VMware → OpenStack guests boot and pass app/data/recovery tests. |
| B39 | Not integrated | Implement qualified same-family environment/site relocation methods; distinguish another endpoint from a same-resource no-op. | Independent topology-specific move, exclusion and recovery campaign. |
| B40 | Not integrated | Implement VMware → AHV and AHV → VMware application rebuild/restore; keep whole-VM extensions separate and unavailable until implemented. | Independent evidence for every advertised direction/method/profile. |
| B41 | Not integrated | Implement OpenStack → AHV, AHV → OpenStack and OpenStack → VMware application rebuild/restore; separate whole-VM extensions. | No reverse/format-based inference; verify all application data and recovery. |
| B42 | Not integrated | Implement selected application-native database synchronization with lag/consistency/final-sync/divergence handling; document warm-VM extension contracts separately. | Real selected database campaign; do not advertise unqualified warm-VM support. |
| B43 | Not integrated | Schedule enterprise waves by dependency DAG, windows, tenant fairness, concurrency, shared risk and existing resource/transfer budgets. | Concurrent native campaigns demonstrate bounded impact and stop behavior. |

Initial release matrix: directed application rebuild/restore across VMware, AHV and OpenStack; VMware → OpenStack cold whole-VM movement for selected Linux/Windows profiles; explicit qualified or blocked same-family topologies.
The wider estate's additional whole-VM, appliance, GPU/passthrough, shared-disk, encrypted/vTPM or other requirements need their own implementation and qualification; a rebuild option does not satisfy an opaque VM requirement.

### Wave 6 — Operations, conversion and supported release

| ID | Baseline | Repository completion deliverable | Native/external gate |
|---|---|---|---|
| B44 | Recovery foundation | Complete deployable HA/DR and backup/restore tooling for control DB, evidence, workflow and state; restore read-only and reconcile epochs/high-water marks before writes. | Independent isolated restore and deployed failure/upgrade campaigns. |
| B45 | Earlier review/alert tools | Implement scheduled health/drift/freshness/stuck-job signals, actual alert dispatch, acknowledgements, ITSM/CMDB integration and operator runbooks. | On-call exercises held/unknown/contained incidents and handover. |
| B46 | Security foundation | Expand threat/negative tests, least privilege, transfer/conversion sandbox, dependency/artifact signing, secret scanning and release provenance. | Independent security review and actual site enforcement/custody tests. |
| B47 | Not completed | Automate exact-version route/action/profile campaign selection, expiry/revocation and release eligibility; retain measured results and unsupported rows. | Complete final advertised native performance, failure and recovery matrix. |
| B48 | Register; limited projections removed | Implement one-time retained-state importer with immutable originals, count/digest/native-ID reconciliation and observation-only start; drain/freeze old writers, then delete superseded runtime paths. | Actual retained-state reconciliation and owner handover; rerun affected B47 campaigns on final code. |
| B49 | Not started | Provide pilot deployment, guided scenarios, support artifacts and acceptance capture from the final qualified revision. | Real sysadmins, production change authority, first production wave and receiving-team acceptance. |
| B50 | Not completed | Publish signed release, generated support/capability ledger, installation/upgrade/rollback instructions and explicit expansion backlog. | B49 accepted; all advertised claims backed by current final-revision evidence. |

## 4. Small-commit execution sequence

Each numbered row is a bounded implementation series. Split it into behavior-sized commits with tests and the relevant documentation; do not combine unrelated platform drivers or migrations in one commit.
Use a current-main branch. The old `implementation/mobility-integrity-closure` branch is 127 commits behind this baseline and is not the product starting point.

| Order | Commit series | Completion evidence |
|---|---|---|
| 1 | Add this execution ledger and correct active next-work links/status; retain the historical audit. | B01–B50 coverage and links reviewed; no changed production capability claims. |
| 2 | Add discovery signed-authority/collector-attestation verification and explicit revocation/freshness dependencies behind `DiscoveryIngestVerifier`. | Valid signatures accepted; forged, stale, revoked, wrong-scope/collector/digest inputs rejected. |
| 3 | Persist campaign issuer/epoch/profile/credential witness metadata through a new migration; record admission and publication in the audit transaction. | Real PostgreSQL role/RLS tests; replay is idempotent and changed content conflicts. |
| 4 | Wire enrolled mTLS discovery ingress and constrained read-credential retrieval to the verifier/repository; add installed service configuration. | End-to-end local issuer/worker/ingest/DB tests; revoked or unenrolled collector cannot publish. |
| 5 | Complete collector fact normalization and qualified installed-profile persistence, one platform per series. | Contract fixtures plus missing privilege, partial pagination, version and identity-reuse negatives. |
| 6 | Persist directed route/control evidence and reviewed application dependencies; expose scoped assessment API, then CLI and portal. | Two authorized destinations, pinned generations, expiry/revocation, foreign-scope denial and UI stale-response tests. |
| 7 | Add discovery scheduling/freshness and estate benchmark; finish B05 owner packaging in parallel by dependency group. | Reproducible measured benchmark; installed runtime works outside checkout. |
| 8 | Integrate capacity/IPAM/staging budgets and native-operation ownership with planned resources. | Concurrency, confirmation/release and crash-boundary integration tests. |
| 9 | Build the OpenStack provisioning vertical workflow and required VMware source reads; integrate native/guest/service postconditions. | Durable workflow integration with real local engines; native gate remains explicit. |
| 10 | Repair cross-scope restic and add dataset children, integrity joins and rate controls. | Positive cross-scope restore plus negative source/target/dataset/replay/partial-result cases. |
| 11 | Add rehearsal, source fence, final sync, traffic switch and split recovery workflows; expose operator actions. | Failure injection around every effect and target-first-write boundary. |
| 12 | Complete minimum deployed recovery/observability/security controls and run B37 when authorized site inputs exist. | Real campaign evidence or a precise external hold; no synthetic successful migration. |
| 13 | Extend platform/guest provisioning, cold VM conversion and each directed application route in independent series. | Per-route integration then native qualification, with unsupported rows retained. |
| 14 | Add application-native sync and dependency/window scheduling over established budgets. | Lag/divergence and concurrent wave failure tests. |
| 15 | Complete operational HA/DR, alert delivery, sandbox and supply chain; rehearse retained-state conversion and old-writer shutdown. | Upgrade/replay/restore/import reconciliation and deletion proof. |
| 16 | Run final qualification on the post-conversion code, conduct accepted pilot and publish supported release. | B47–B50 evidence at final artifact revision; no unverified completion flags. |

## 5. Discovery provenance slice and remaining integration

The first slice now has a concrete `DiscoveryIngestVerifier`, signed authority
and enrollment, independently signed read-credential witnesses, a pinned mTLS
listener and original evidence retention before dedicated-role publication.
Real PostgreSQL tests exercise valid admission/publication, exact retries,
changed-content conflicts and role isolation; signature, scope, freshness,
revocation and TLS negatives are also covered. See the
[ingest contract](../discovery-ingest.md) and
[comparison architecture](wave2-discovery-architecture.md).

Complete the native side next: admitted collector transport and credential
retrieval, installed API/profile and field-set binding, full per-platform facts,
page evidence and independently reconciled coverage. Campaign signatures and an
aggregate result digest do not themselves prove native completeness. Preserve
separate issuer/collector/witness authority, exact scope, bounded budgets and
live revocation checks as these pieces are integrated. Scheduling may select
work; it cannot issue campaign or credential authority.

The implementation sequence above remains the complete ordered programme;
several series have begun but none of these changes grants provisioning or
migration authority or closes native site qualification.

## 6. External inputs and final release holds

Request concrete site inputs as each native slice becomes ready: selected source/target installed tuples, enrolled endpoints, constrained credentials, read/mutation test scope, native observers and fencing method, guest images and network/service mappings.
Obtain application dataset/dependency ownership, acceptance checks, downtime/data objectives, retained-source policy and post-write recovery decisions before migration qualification.
Enterprise owners supply IdP/IAM/PKI/Vault/evidence custody, commissioned capacity/IPAM/DNS and security-edge/shared-service acceptance; JSON declarations cannot replace those authorities.
Record target contact, stop, change and cleanup authority separately from implementation approval. Do not contact an unspecified native site to fill an evidence gap.
Continue repository work when a native campaign is blocked, and report exactly which campaign and owner input remain outstanding.
Final completion means the declared support matrix works through the supported product interfaces, passes recovery and security acceptance, and has an accepted operating owner on the final released revision.

## 7. Baseline evidence

- Merged [Phase 0 PR #51](https://github.com/awalker0878/multi-tenant/pull/51), [Wave 1 PR #52](https://github.com/awalker0878/multi-tenant/pull/52) and [partial Wave 2 PR #53](https://github.com/awalker0878/multi-tenant/pull/53) record their implementation and verification boundaries.
- [Interface retirement register](../implementation/automation/phase0-interface-retirement.md) identifies B05's remaining runtime imports and the retained-state/deletion gates.
- [Discovery architecture](wave2-discovery-architecture.md) and [operator guide](wave2-operator-guide.md) distinguish declared selectors, trusted ingestion, stored observations and comparison-only artifacts.
- `provisioner/controlplane/discovery/model.py`, `persistence.py`, `routes.py` and `assessment.py` implement bounded models, verifier-required publication and pure comparison; their existence does not supply production trust or native qualification.
- [Control-plane operator guide](control-plane-operator.md) describes the authenticated foundation and explicitly excludes later native provisioning and workload migration activities.


## 8. Research-driven acceptance and implementation delta

The 28 September 2026 [verified research decisions](../engineering/platform-migration-research.md)
are integrated here, not adopted as a new four-wave or B01–B15 roadmap. Preserve
B01–B50 identifiers, baseline rows, authority boundaries and dependencies. The
research's approximate paths, active-owner deletion advice, unsupported blanket
feature claims and illustrative completion dates are rejected.

### Implemented repository increment

Typed semantic properties beneath the existing 97 capability IDs now flow from
strict profile catalogues through resolution, scoped cluster placement and portable
policy translation. Profile resolution format 3 and policy capsule/realization
format 2 bind the property interpretation digest and reject weaker/old inputs.
The existing security/compute profiles impose explicit routing, enforcement,
NIC-coverage and architecture requirements; deferred encryption stays deferred.

Discovery normalizer 2 and comparison check exact source requirements against the
selected target's observed capabilities/properties. Whole-VM hardware/driver/key/
writer requirements and warm-transfer convergence are checked before eligibility;
positive route/control evidence cannot fill missing native facts. Old-normalizer
signed control evidence is rejected. Mixed same-platform-relocation comparisons
retain all authorized destination rows and block cross-hypervisor ones.
OpenStack collection now observes bounded port-security/binding/group/QoS/address
and volume-encryption/multiattach/type fields without inventing qualification.
All updated examples remain non-authoritative and disabled.

This increment has local regression tests, not native acceptance. Do not mark an
entire B item VERIFIED from this subsection. Store exact final-revision CI results
in the PR/delivery record; qualification and operations remain separate columns.

### Existing wave owners and expanded closure tests

| Existing wave / B items | Required implementation and acceptance expansion | Current boundary and closure evidence |
|---|---|---|
| Wave 0 — B03/B04/B05 | Keep canonical property types and bounded parsers; reject old interpretation rather than shim it. Migrate every real consumer before deleting a legacy path. | Property contract and version rejection implemented. Package qualification owners are active, not deletion targets. B05 retained runtime/state migration remains open; installed-wheel and retirement tests are required. |
| Wave 1 — B06–B13 | Bind requirements, observations, approvals, immutable revisions, reviewer authority and worker credentials; per-effect rechecks cannot use an earlier comparison as permission. | Existing signature/RLS/outbox/lease controls retained. Old-normalizer review rejection added. Native claim import must retain original sources, timestamps, tuple, publisher and independent evidence custody. |
| Wave 2 — B14/B15/B16 | Collect per-VM firmware/architecture, controllers/disks/NIC order, boot/security/key state, shared/passthrough devices and optional service/driver/extension facts. Bind exact API/driver/tool versions, project/scope and completeness. | OpenStack attribute capture and malformed/missing-field tests implemented. VMware REST campaign/VM-info and AHV typed boot/device mapping are implemented in the follow-up below. Full fact coverage, installed profiles, credential transports and independent reconciliation remain open. Never infer safe boot or encryption absence from a friendly profile name. |
| Wave 2 — B17/B18 | Attribute source policy and dependency/consistency decisions; version the complete source/destination/guest/tool/backend tuple. Keep six directed inter-family routes distinct and distinguish each method. | Current tuple/route authority retained. Property schema and explicit observed/source capability sets enforced. Exact released support matrices, entitlement, expiration and native claims still need qualified owner evidence. |
| Wave 2 — B19/B20/B22 | Compare scoped property values, all source requirements and measured transfer assumptions; expose stable blocker/unknown reasons and remediation without hiding other destinations. | Typed comparison and relocation error isolation implemented; old signed reviews invalidated. Persisted owner enrichment, complete UI review flow, scheduling, freshness and estate benchmark still required. |
| Wave 3 — B23/B25/B26 | Reserve real VM/storage/transfer/retention capacity; map firmware, disks, NICs, keys, drivers, shared devices and huge pages. Distinguish QoS minimum guarantees from ceilings and encryption layers from each other. | Planning/placement and comparison prerequisites implemented. Actual native realization, resource reservations, driver preparation, encryption transition and observation-bound postconditions remain open. Test unknown versus false and malformed integers as well as happy paths. |
| Wave 3 — B24/B27/B28/B29 | Realize policy outcomes with exact ordered/additive semantics, all-NIC enforcement, routing/VRF and datapath constraints. Qualify LB/VPN/service insertion as separately installed services; do not assume Neutron core or Flow networking supplies them. | Property conflicts, NSX VRF HA, DPDK prerequisites and SR-IOV bypass checks implemented. Native rule compilation/readback, positive app flows, negative isolation/bypass, MTU/reply paths, HA and service-owner acceptance still required. |
| Wave 4 — B30–B37 | Retain per-dataset consistency and metadata, isolate rehearsal, independently exclude old writers, final-sync, switch traffic and admit target writes. Split pre-write return from post-write reverse-sync/restore/forward repair. | Existing safe cutover contract retained; the research's unconditional source restart is rejected. Transfer-worker composition, native effect graph and actual first application campaign remain open. Inject failure before/after every effect and first-write boundary. |
| Wave 5 — B38/B39/B40/B41/B42/B43 | Qualify each directed source/target method independently; pin converter/Move/guest/backend versions. Cold/warm disks do not imply RAM migration, same-family does not imply topology support, common disk format does not imply boot or key portability. | Whole-VM hardware/key/driver checks, warm convergence and cross-family relocation blocking implemented in comparison only. Native capture/conversion/transport, application-native sync, device handling and dependency-wave execution remain open. No reversed-route or vTPM recreation shortcut. |
| Wave 6 — B44–B50 | Qualify HA/DR, retained source and restore/key custody, supply chain, privileged isolation, final native support matrix, conversion, pilot and operating owner on final code. | No new native or production completion. Each campaign must cover declared guest/device/network/storage controls, permitted/denied flows, one-writer recovery, measured objectives and final artifact digest. |

Use the existing small-commit sequence: property contracts and profile/placement
integration, comparison and signed-input revision, one native collector at a time,
then native realization/workflow increments with their actual tests. This change
adds no competing sequence or fictitious lab access. A missing capability fact
remains UNKNOWN; an explicit incompatible observation is BLOCKED. Neither can be
turned into an execution grant by an operator-supplied success flag.


### Native hardware collection follow-up — 28 September 2026

B14/B15 now retain more native facts without manufacturing capability claims.
AHV's VMM v4.0 collector records the explicit boot union, returned Secure Boot and
vTPM booleans, native live-migration hint, disk bus/index and NIC model/MAC/link
state. A tagged volume-group attachment cannot masquerade as a VmDisk or supply
its disk-image capacity. Duplicate addresses, malformed types and oversized facts
remain unknown; missing SDK response fields never acquire request defaults.

The VMware REST collector now retains VM-info CPU, memory, firmware, disk layout,
NIC model/MAC/link and native network bindings, with instance UUID and reviewed
folder identity/digest. Summary/detail disagreements hold the scan. Its new
`collect_vmware_vms` path emits the common campaign pages and rechecks campaign
lifetime around each native GET. Those pages are always `PARTIAL` for visible-only
REST inventory, even when the result is empty. Native read failures emit `UNKNOWN`
without publishing a truncated scan as complete; expiry cannot produce late evidence.
The emitted cursors partition the captured observations, not a native paging API.

Collector identities are `nutanix-ahv-v4.0-hardware-2` and
`vcenter-rest-vm-info-8.0.3.0-visible-only-2`. Re-admit campaigns and reissue the
matching worker/credential witnesses; old collector identities are rejected rather
than aliased. Raw hardware and folder-evidence changes affect snapshot digests.
The normalizer remains version 2: its interpretation is unchanged, and the changed
raw snapshots require new signed review bindings. No existing approval is restamped.

This is bounded read-only mapping and campaign integration, not completion of
B14/B15 or Wave 2. Site transport/credential wiring and independent visibility
reconciliation remain open, as do full controller/boot-order/opaque-network,
ISA, encryption/key, shared-disk and passthrough mapping and attributed application
requirements. REST VM-info does not supply SOAP ConfigInfo security fields.
The native live-migration hint is not directed route or entitlement qualification.
No native system or guest was contacted; no execution or qualification gate changed.

### B10/B14/B16 continuation — signed native reads

The [VMware HTTPS transport](../engineering/vmware-discovery-https.md) now invokes
the current collector using independently signed exact-campaign session material.
Scope/folder selection, API release, URL, pinned IP, CA and token bytes are bound;
the live enrolled credential and independent read-only witness are rechecked
before connection, before sending credentials, after response and at collection
return. Native issuance, original result-signature publication, deployed PKI/Vault
composition and independent visibility reconciliation still require integration.

The transport restricts requests to reviewed folder lists and VM IDs actually
returned by those lists. Real loopback TLS tests cover wrong identities, revoked
credentials, rotation/replay, response tampering/framing, deadlines and bounds.
OpenStack now rejects expired/future campaigns before their first read and checks
UTC monotonicity and validity around every page/quota read, including error paths.
The regression previously reproduced a native GET after campaign expiry.

These are repository/automated-verification increments, not native acceptance of
B10/B14/B16 or completion of Wave 2. OpenStack HTTPS credential client, native
visibility reconciliation and B17 persisted application/dependency review remain
open. No collector identity, normalizer or qualification claim is silently upgraded;
no compatibility shim, mutation endpoint, login fallback or production grant is
introduced. Existing later-wave dependencies and completion columns still apply.


### B10/B15 continuation — signed AHV reads and shared HTTPS

The AHV VMM v4.0 collector now has `adapters/ahv_https.py` and an independently
signed API-key source in `adapters/ahv_credentials.py`. Only the admitted cluster's
consecutive bounded VM-list pages can be requested. Native service-account keys,
TLS origin/IP/CA, scope, API profile, credential enrollment and current independent
read-only witnesses are checked before connection, after TLS, after decoding and
before returning pages. Mid-read revocation or rotation cannot become publishable
observations. Errors consume the request budget and latch the client closed.

The actual HTTPS mechanism is extracted into provider-neutral `native_https.py`;
VMware callers and deadline tests use it directly. No adapter forwards to another
vendor, no old-path alias or native login/mutation fallback was added. Both native
credential readers now reject embedded origin controls/whitespace. Successful AHV
collections remain `PARTIAL`/`VISIBLE_INVENTORY_ONLY`, including empty responses;
API totals alone cannot establish independent native visibility.

See [AHV HTTPS custody and qualification boundaries](../engineering/ahv-discovery-https.md).
Local real-TLS/signature tests and installed-package guards cover these owners.
Collector/normalizer/policy formats are unchanged; updated observations require new
digest-bound review. This advances B10/B15 without closing them: deployed site
composition, service-account issuance/revocation, Vault publication, persistent
revision floors, original result signing/ingest and independent visibility remain
open. OpenStack native HTTPS, B17 persistence and later migration effects also
remain open. No native environment or production dataset was contacted.
