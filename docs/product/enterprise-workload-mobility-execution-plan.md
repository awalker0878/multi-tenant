# Enterprise workload mobility: execution plan for all waves

**Current review:** 1 October 2026, `implementation/all-waves`, starting at
`9d4c6685b6fd0fcb6df211aebd47857562265456`, with discovery/profile corrections
`b993470` and `249d75f`, catalog/design alignment and the subsequent guided
initial application-draft creation continuation from `d663821ae9b594bd6b035755a0113218169ff40b`.
**Historical baseline:** `main` at `3cbc0c1e1e52a4bedd70972b05b04ccec48de699`.
**Status:** substantial Wave 0/1 foundations; B05 remains open, Wave 2 is partial,
and Waves 3–6 are not complete. No native qualification or operating acceptance added.

This is the active addendum to the [historical audit](enterprise-workload-mobility-audit-and-implementation-plan.md).
B01–B50 remain stable; earlier W01–W29 and C01–C13 ledgers have narrower scopes.
Chronological checkpoints have been consolidated into current status here. Their
original wording and evidence remain in Git history, not as competing active guidance.

## 1. Completion rules and current position

Track each B item through repository implementation, automated verification, native
qualification and operational acceptance. Each column uses `NOT_STARTED`, `IN_PROGRESS`,
`VERIFIED` or `NOT_APPLICABLE_REVIEWED`, with exact revision, test/campaign, scope,
result and limitations. Never infer one column from another. Prior CI or signed
acceptance at an old revision is not evidence for a changed artifact or installed tuple.
An API hold, fixture, native-operation name or authority gate is not its implementation.
Lack of native access does not prevent repository implementation and local testing.

| Area | Implemented repository boundary | Still open |
|---|---|---|
| Packaging (B05) | Package-owned resources, WSD compiler and qualification registry/native/provenance owners; retired entry points deleted without aliases. | Other real runtime imports, installed execution ownership and retained-state conversion. |
| B06–B13 | Authenticated control application, tenant state, approval/admission/outbox, workflow gating, worker identity, claims/intents and evidence primitives. | Complete admitted native effect composition and deployed authority/operating acceptance. |
| B14–B16 | Three signed, bounded native HTTPS collectors, independent read-material custody, original signatures, explicit publication and normalization. OpenStack selector 2 retains allocation and attachment facts. | Full hardware/driver/key/Glance/service facts, deployed custody, independent visibility and native profile qualification. |
| B17–B20 | Revisioned drafts, attributed assertions, signed assessment-only owner decisions, generation-pinned multi-member comparison, CLI, guided initial browser creation and saved-draft metadata editing. | Guided changes to saved membership/evidence, independent dependencies, owner-facing signing and complete administrator acceptance. |
| B21/B22 | Adoption proposal model; one-shot process-local batch limits, shared-outbox first-capture claims, scoped freshness CLI/API and retained on-demand history. | Actual ownership transfer, durable fleet/global budgets, periodic monitoring/alerts, resumability and measured estate qualification. |
| B23–B43 | Portable planning, native lifecycle/readback/fenced-power primitives, guest/service handoffs, transfer/integrity/consistency contracts and compatibility checks. | Native reserve/prepare/plan/approval/apply/observe/power/guest/service/activate chain; trusted transfer-worker/target-root bindings; source fencing, final sync/cutover, post-write recovery and route execution. |
| B44–B50 | Existing recovery/security/evidence foundations and defined release obligations. | Deployed HA/DR, alert delivery, final qualification, retained-state conversion, pilot and operating release. |

Profiles explicitly represent 97 capabilities and 28 semantic properties. All ten
families have typed requirement checks; selected capabilities/constraints/limitations
flow into resolution. Availability catalog 18 corrects security-zone/failure-domain
wording; it grants no HA. All installed tuples remain unselected/unqualified and
examples stay disabled. Immutable plans and observations require new digest-bound
review after change, not compatibility aliases or relabelled history.

One authenticated control application remains the product. Terraform, native APIs,
Ansible and service owners are mechanisms behind tenant-scoped authority. Preserve
one writer, immutable approval, uncertainty holds and independent postconditions.
Delete competing/obsolete entry points only after verified consumer/state migration;
these safety controls are not shims.

### Guided initial draft creation — B17/B20 continuation

The existing portal now pins an authorized stored generation, pages VM identities
explicitly, collects proposed members/dataset groups/known or unknown dependencies,
and submits the existing first-revision contract without hand-authored JSON. Shared
proposal validation and the existing uncertain-save owner replace duplicated checks;
no alternate API, SQL migration, authority flag or compatibility shim is added.
First-save acknowledgement loss reconciles through exact revision-one history, never
an automatic retry. Saved membership/evidence still requires the operator/API path.

The [current browser contract](../engineering/application-draft-browser.md) records
bounds, remaining guided editing/review obligations and synthetic verification.
Initial authoring is not independently verified dependency evidence, owner signing,
installed-platform qualification or operational acceptance. B05 and Wave 2 remain
open; this continuation does not start or close the native provisioning/migration waves.

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

## 3. B01–B50 completion obligations

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
| B13 | Delivered foundation | Extend signed audit checkpoints, Object Lock/Vault adapters, redaction and startup/write holds; add transfer/image artifacts and evidence retention. | Actual signing custody, retention enforcement and independent recovery verified. |

Wave 1's existing repository boundary is verified in PR #52. Later native workflows extend it; they must not reinterpret its initial gate-only workflow as completed provisioning.

### Wave 2 — Trusted discovery and useful destination comparison

| ID | Baseline | Repository completion deliverable | Native/external gate |
|---|---|---|---|
| B14 | Partial signed native path | Complete remaining VMware hardware/policy/visibility coverage over the implemented signed HTTPS collector and publication; preserve exact folder/native identities and original generations. | Reconcile with independent enumeration; qualify folder/privilege coverage and visible-list limits. |
| B15 | Partial signed native path | Complete AHV hardware/network/capacity facts over the implemented pinned VMM read and authenticated publication; retain typed boot/device evidence. | Qualify installed API/profile, paging/count semantics and least-privilege coverage. |
| B16 | Partial signed native path | Complete Glance/guest/boot/key/driver and independent coverage over implemented exact-project Nova/Cinder/Neutron/quota reads, allocation and attachment facts. | Qualify actual catalog endpoints, versions, read roles and service visibility. |
| B17 | Persisted drafts and signed assessment decisions | Finish independent enrichment/dependency verification and owner-facing signing/review workflows; exact observed membership and consistency decisions remain revision-bound. | Application owner confirms dependencies and useful-service acceptance criteria. |
| B18 | Durable signed tuple/route/control inputs | Complete deployed qualification import, expiry/supersession/revocation and release-ledger integration without converting operator assertions into evidence. | Source-exit and destination-operation campaigns independently qualify advertised scope. |
| B19 | Persisted generation-pinned comparison | Complete coverage and acceptance for single-VM and reviewed multi-member comparisons, exact pool/profile bindings and explicit reasons/remediation. | Reviewed policy, security, recovery and target-capacity evidence for positive candidates. |
| B20 | Initial browser creation, saved-draft metadata editing and application comparison | Finish guided changes to saved membership/dependency evidence, owner-facing signing and complete administrator workflows; preserve stale-response and uncertain-save defenses. | Sysadmins complete comparison without hand-authoring JSON. |
| B21 | Partial proposal model | Persist no-change import proposals, ownership collisions, review state and links to exact observations; execution stays separately approved. | Native no-change/state reconciliation before ownership transfer. |
| B22 | Bounded batch, custody claims and freshness/history | Complete durable fleet/global endpoint budgets, resumable estate work, periodic monitoring/alerts and measured benchmark beyond existing one-shot/process-local/on-demand paths. | Independent omission/privilege-loss reconciliation and agreed estate-scale measurements. |

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
Continue the latest verified `implementation/all-waves` revision in small non-force commits. Recheck the branch before each update; do not reset it to an older baseline or silently overwrite concurrent work.

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

Native HTTPS transport, signed material readers, installed collector composition,
original publication, persisted application/owner review and API/CLI/browser comparison
now exist. Remaining native-side work is complete field coverage, exact deployed
custody and least-privilege qualification, independent enumeration reconciliation,
guided owner workflows, durable fleet scheduling and estate measurement. Campaign
signatures and aggregate digests do not prove completeness. Scheduling cannot issue
campaigns, credentials or mutation rights. On-demand freshness/history does not close
periodic monitoring or alert delivery.

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

The [current primary-source review](../engineering/platform-capability-review-2026-10-01.md)
and [earlier semantic research](../engineering/platform-migration-research.md) refine
this programme, not a replacement numbering scheme. Approximate paths, unsupported
blanket vendor claims, arbitrary completion dates and deletion of active owners are
not accepted requirements. Vendor documentation is not installed qualification.

OpenStack selector 2 retains strict allocation/image/volume/attachment facts from
already selected APIs; nominal disk sizes, deletion booleans and device labels never
become total storage, fencing or mutation authority. The retired selector has no alias.
The typed profile field owner removes a parallel table; standalone assurance recovery
now shares the existing full-pipeline rule. Minimum workload counts and recovery-zone
composition are enforced; independent-site recovery stays unsupported. Catalog 18
and regenerated examples correct security-zone semantics without changing support.

Resolution 3, normalizer 2 and policy capsule/realization 2 retain exact interpretation
digests. Unknown/contradictory hardware, driver, key, policy and convergence evidence
cannot become eligibility through a positive route/control flag. These remain tested
comparison prerequisites, not native provisioning, conversion or transfer execution.

### Existing wave owners and expanded closure tests

| Existing wave / B items | Required implementation and acceptance expansion | Current boundary and closure evidence |
|---|---|---|
| Wave 0 — B03/B04/B05 | Keep canonical property types and bounded parsers; reject old interpretation rather than shim it. Migrate every real consumer before deleting a legacy path. | Property contract and version rejection implemented. Package qualification owners are active, not deletion targets. B05 retained runtime/state migration remains open; installed-wheel and retirement tests are required. |
| Wave 1 — B06–B13 | Bind requirements, observations, approvals, immutable revisions, reviewer authority and worker credentials; per-effect rechecks cannot use an earlier comparison as permission. | Existing signature/RLS/outbox/lease controls retained. Old-normalizer review rejection added. Native claim import must retain original sources, timestamps, tuple, publisher and independent evidence custody. |
| Wave 2 — B14/B15/B16 | Collect per-VM firmware/architecture, controllers/disks/NIC order, boot/security/key state, shared/passthrough devices and optional service/driver/extension facts. Bind exact API/driver/tool versions, project/scope and completeness. | OpenStack attribute capture and malformed/missing-field tests implemented. VMware REST campaign/VM-info and AHV typed boot/device mapping are implemented in the native read contracts. Full fact coverage, deployed credential custody and independent reconciliation remain open; signed native transports and installed collector composition exist. Never infer safe boot or encryption absence from a friendly profile name. |
| Wave 2 — B17/B18 | Attribute source policy and dependency/consistency decisions; version the complete source/destination/guest/tool/backend tuple. Keep six directed inter-family routes distinct and distinguish each method. | Current tuple/route authority retained. Property schema and explicit observed/source capability sets enforced. Exact released support matrices, entitlement, expiration and native claims still need qualified owner evidence. |
| Wave 2 — B19/B20/B22 | Compare scoped property values, all source requirements and measured transfer assumptions; expose stable blocker/unknown reasons and remediation without hiding other destinations. | Typed comparison and relocation error isolation implemented; old signed reviews invalidated. Revisioned drafts, guided initial authoring, signed owner decisions, operator comparisons and on-demand freshness/history exist; verified dependencies, guided owner workflows, durable scheduling, periodic monitoring and estate benchmark remain open. |
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
