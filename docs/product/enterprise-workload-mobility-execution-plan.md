# Enterprise workload mobility: execution plan for all waves

**Current review:** 3 October 2026, continuing `implementation/all-waves` from
`32d0f77002a549302ed8149c575bcad64d3b71db`, through operator/readback ownership
`d2dfdc8d967543d8412ebd21a95db3cc96e3a124` and the saved-plan/lifecycle/source-binding
continuation documented below. Earlier continuation boundaries remain in Git history.
**Historical baseline:** `main` at `3cbc0c1e1e52a4bedd70972b05b04ccec48de699`.
**Status:** installed execution-owner closure, deployable Wave 2 services and the
selected application workflow are implemented increments. Waves 3–6 remain incomplete.
No native qualification, pilot acceptance or operating release is added.

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
| Packaging (B05) | Installed package owners, explicit wheel/source/interpreter closure, protected service composition, authenticated retained import and independent epoch-handover intake. Retired interfaces have no aliases. | Commission the installed service and retained originals; independently reconcile live old writers and accept the actual handover before retirement. |
| B06–B13 | Authenticated control application, tenant state, approval/admission/outbox, workflow gating, worker identity, claims/intents and evidence primitives. | Complete admitted native effect composition and deployed authority/operating acceptance. |
| B14–B16 | Three signed, bounded native HTTPS collectors, independent read-material custody, original signatures, explicit publication and normalization. OpenStack selector 4 retains allocation/attachment facts plus bounded VM-referenced Glance driver/security metadata. | Guest-installed driver/key/service evidence, deployed custody, independent visibility and native profile qualification. |
| B17–B20 | Revisioned drafts, attributed assertions, signed assessment-only owner decisions, generation-pinned multi-member comparison, CLI, guided initial and saved-revision browser membership/data/evidence editing, installed offline owner preparation/signing, exact-revision browser review inspection and installed custodian signed-artifact intake. | Independent dependencies, deployed owner/key onboarding, owner-to-custodian artifact transfer and complete enterprise/administrator acceptance. |
| B21/B22 | Original-only bounded publication/reconciliation, process-shared read budgets and database-backed multi-host fleet reservations; periodic freshness/alert services, signed HTTPS receipt intake and independently assigned on-call ownership. | Commission actual collector/native custody and receiving alert owners; verify omitted inventory/privilege-loss facts, estate scale and no-change ownership adoption. |
| B23–B29 | Atomic counted resource transactions, scoped planning credentials, current authorization for every remote guest command, enrolled IPAM/service intents and separately approved revoked-job cleanup over existing B10/B11 owners. A bounded Windows service purpose targets an existing guest. | Commission actual credentials, independent target/policy readback, image/profile and useful-service acceptance. Full Windows provisioning/migration and other unimplemented layouts remain blocked. |
| B30–B37 | Bounded per-dataset restic transfer; separate staging/cutover workflows; conditional retained-port management bootstrap with independent project/pinned guest reads; isolated systemd rehearsal, persistent source disk exclusion, final capture/restore, explicit target power/activation, pre-write source return and separately admitted retained-target post-write forward repair. | Commission management/bootstrap and qualify its datapath. Complete production policy/traffic realization and independent retained-detached-backing accounting; qualify actual guest isolation, source/late-writer exclusion, final consistency, traffic/write admission, data/service/recovery objectives and the first directed application route. General reverse-sync is not implemented. |
| B38–B43 | Powered-off VMware snapshot/NFC export, sandboxed disk conversion and private Glance image import as a lower capture purpose; selected PostgreSQL17 logical sync with atomic target journal and original credential closure; enterprise wave pools with global physical/risk budgets and cross-tenant turns. | Complete cold target boot/guest remediation, full Windows movement, warm-VM methods, same-family relocation and remaining AHV/VMware/OpenStack directions. Qualify database and concurrent native campaigns separately. |
| B44–B50 | Controlled operating HA/restore owners and observation-only restore interlock; health/ITSM receipts, authenticated original retained import/native epoch-handover intake, final-code native/pilot originals and commissioning dossier validators. | Actual failover/restore, frozen-old-writer reconciliation and operating/receiving-owner acceptance; final native campaigns, signed pilot acceptance and supported release. |

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

### Selected application continuation — implementation boundary

The implemented driver is **VMware → OpenStack, REBUILD_RESTORE,
linux-ubuntu-2404**. The immutable canonical plan optionally selects
`hosting-execution-selection/1`; older plans retain their original gate-only
workflow. The review shows the driver and artifact digest. Resource, dataset,
cutover, delivery, native qualification and minimum operating acceptance digests
are acyclic pre-plan descriptors under protected custody. Credentials and
runtime filenames never enter Temporal history.

`OpenStackApplicationMigration` is a distinct, pinned workflow. It rechecks the
original admitted payload, proceeds through resource and declared target stages,
joins bounded dataset children and requires isolated rehearsal before source
fencing/final-sync/cutover. Every effect activity has one attempt. Missing native
bindings, a lost result or an unimplemented native owner produces a visible hold;
an old approval gate or successful subprocess cannot become migration success.
Local original-receipt inspection remains possible under its separately named
observation gate. A typed continuation can exclude only its independently
revalidated original grant/intent from the new-write uncertainty check.

See [operating controls](../operations/control-application/1-operating-the-selected-slice.md),
[qualification, pilot and release](../operations/control-application/2-campaign-pilot-and-release.md),
[conversion rehearsal](../operations/retained-state-conversion-rehearsal.md),
[discovery scheduling](../engineering/discovery-service-scheduling.md) and
[monitor service](../engineering/discovery-monitor-service.md),
[application composition](../engineering/application-worker-composition.md) and
[migration owners](../engineering/application-migration-runtime.md).
Recorded local protocol/engine results are automated verification. Deployed
PostgreSQL/Temporal checks and native acceptance retain their own evidence columns.
Run affected engine/protocol campaigns again on final code after the old paths
are deleted. The earlier dated sections below preserve narrower increment context.

### Verification repair — B01/B05 continuation (2 October 2026)

The architecture run for `c5a579fa3a33a4c1bf0bceb33a18bee500872aba`
finished **FAILED**, not pending or passed: its repository regression report recorded
4,274 tests, two retirement assertions and 123 skips. The independent expected
retirement map omitted the already-deleted Terraform catalog module. This increment
adds that explicit eighteenth entry and extends package-owner import tests to the
execution package; rejection tests and the retirement register are not weakened.

The local regression evidence manifest now includes `provisioner/`,
`hosting_resources/`, `pyproject.toml`, `setup.py` and `MANIFEST.in` alongside its
existing source families. Moving code into an installed package must not remove it
from test-source attribution. Original reports are retained; the expanded manifest
is not a signed release or proof that every reported file was exercised.

See the [revision-specific verification repair](../engineering/ci-retirement-repair-2026-10-02.md).
The separately prepared source-integrity relocation is **not published** in this
increment: the existing verifier and all its callers remain intact. Only coherent
verification/evidence changes are delivered; B05 and the remaining waves stay open.

### Exported reservation evidence — parallel B05 continuation (2 October 2026)

From `73731f7e6432e5adc44e11a89c0b5ddd5f3578e9`, the actual reservation-record
reader now lives in `provisioner.allocations.reservation_evidence`. Every in-tree
consumer, current command and generated source link is migrated; the old script is
deleted with no alias. Bounded regular-file reads and exact contained source references
reject ambiguous inputs while preserving the existing record format, canonical digests,
expiry and uncertainty rules. Installed tests block legacy imports and working-directory
fallbacks; reused builds remove the retired script and bytecode. The independent
retirement expectation is updated together with the register.

See the [reservation-evidence runtime contract](../engineering/reservation-evidence-runtime.md).
The reader authenticates neither an external issuer nor live capacity. No record is
created, renewed, consumed or released; the authoritative reservation service, B23
transactional composition and remaining B05 owners/state conversion stay open.

### Guided drafts and owner preparation/signing — B17/B20 continuation

The existing portal now pins an authorized stored generation, pages VM identities
explicitly, collects proposed members/dataset groups/known or unknown dependencies,
and submits the existing first-revision contract without hand-authored JSON. Shared
proposal validation and the existing uncertain-save owner replace duplicated checks;
no alternate API, SQL migration, authority flag or compatibility shim is added.
First-save acknowledgement loss reconciles through exact revision-one history, never
an automatic retry. The same component now explicitly revises saved membership,
dataset groups and dependency assertions. It rechecks the saved generation/digest,
retains original ordering and precision in a working copy, and submits expected revision
N with exact N+1 acknowledgement or history reconciliation. No source rebase, old-review
reuse or overwrite of an earlier record occurs. Failed source/page reads hold both
structural and metadata editing; historical/superseded/unresolved records remain read only.

The [current browser contract](../engineering/application-draft-browser.md) records
bounds, remaining independent-evidence/review obligations and synthetic verification.
The [installed owner command](../engineering/application-owner-signing.md) now prepares
an exact-record-bound decision, requires explicit confirmation of its digest and signs
under the existing root-enrolled owner role. Canonical input/output, private create-only
files and pre/post-sign live trust checks are implemented. The shared retained-record
parser and enrollment selector avoid a second representation or approval authority.
Signing performs no database/network action: a valid signature is not ingested evidence,
current inventory, accepted dependencies or native permission. Existing ingest rechecks
actual retained content, currency, roles, evidence revision and original signatures.

The existing draft browser now reads the exact saved revision through the existing
review GET. One shared browser validator owns the standalone review and comparison
contracts; the duplicate comparison-local validator is removed without an alias.
Immutable pins, owner/editor separation, UTC microseconds, status precedence and false
authority flags are checked. Edits, identity/selection changes and hidden tabs clear
the display; bounded clearance timers are not revocation monitoring or approval leases.
Superseded source/draft reports make the loaded view read only until explicit reload.
No browser signing, evidence delivery or extra API/SQL authority is added. See the
[browser review contract](../engineering/application-review-browser.md).

The [installed custodian intake](../engineering/application-review-intake.md) now
consumes one canonical owner-signed artifact and explicit submission digest under a
protected exact environment/scope. It authenticates to the existing assessment SQL
writer with pinned TLS/SCRAM settings, checks the actual append-only login and forced
RLS, and rechecks inputs/live trust before commit. A create-only local receipt means
recorded assessment evidence, not current review or execution authority. Lost commit
acknowledgements and postcommit receipt failures are distinguished without automatic
retry. Shared private-file code replaces the signer's local helpers without aliases.

Independent dependency verification, actual owner/key onboarding, owner-to-custodian
artifact transfer and enterprise/administrator acceptance remain open. B05 and Wave 2 remain
open; this continuation does not start or close the native provisioning/migration waves.

### Package-owned implementation input review — parallel B05 continuation (3 October 2026)

The read-only Terraform-root input validator now lives in
`provisioner.execution.input_review`. Its former tool path is retired without an alias;
route-record review, tests and active documentation use the package owner directly.
Required/extra field, primitive type, placeholder, documentation-address, restricted-
build and gateway checks are unchanged. See the
[input-review runtime contract](../engineering/input-review-runtime.md).

This is offline validation only: no credential, IPAM, target, Terraform or production
authority is introduced. Remaining mutation/orchestration owners, installed service
composition and retained-state conversion keep B05 open.

### Package-owned source integrity — parallel B05 continuation (2 October 2026)

The active clean-source verifier now lives in `provisioner.execution.source_integrity`;
every live caller and CI command migrated and the old tools module is retired without an
alias. Checkout verification pins one HEAD/tree, removes ambient Git overrides/replacement
objects/fsmonitor, performs bounded no-follow tracked-byte reads and rejects untracked,
staged, missing or changed sources. Explicit exports require their own bounded SHA-256
manifest and never fall back to historical release manifests or an adjacent checkout.
Installed execution without an explicit checkout is held. See the
[source-integrity contract](../engineering/source-integrity-runtime.md).

This is byte consistency, not signer trust, approval, native qualification or a B48
state conversion. Other B05 owner migrations remain open.

### Package-owned IPAM allocation evidence — parallel B05 continuation (2 October 2026)

The exported allocation reader now lives in `provisioner.allocations.ipam_evidence`;
reservation/IPAM preflight and DNS consumers use that owner directly and the former
script is retired without an alias. The index format, lifecycle rules, stable confirmed-
allocation digest and deliberate absence of allocation values are unchanged. Bounded
regular-file reads, no-link source references and duplicate/non-finite JSON refusal make
installed evidence selection explicit. See the
[IPAM evidence contract](../engineering/ipam-evidence-runtime.md).

This does not implement IPAM mutation, address assignment, DNS writing, B23 live
reservation/IPAM transactions, retained-state conversion or native qualification.

### Package-owned Terraform catalog — parallel B05 continuation

The actual reader now lives in `provisioner.execution.terraform_catalog`; all preparation,
verification and test consumers migrated and the old tools module is deleted without
an alias. Bounded catalog/configuration reads, exact local owned-source checks and
complete registered-directory checks refuse ambiguous input. The existing catalog,
Terraform source, provider locks, profiles and golden plans remain unchanged. Installed
checks block legacy imports and require the retired module to be absent. Reused build
staging cannot retain deleted Python owners or bytecode; source-overlapping build
outputs are refused before cleanup. See the [runtime contract](../engineering/terraform-catalog-runtime.md).

This closes the IPAM evidence owner but not B05 or the native workflow. The dependent
capacity/eligibility/reservation/IPAM/DNS planning owners are now package-owned as
described below; direct execution owners, actual retained-state conversion, installed
site custody and later wave obligations remain open. No native API or production dataset
is contacted by these ownership changes.

### Package-owned capacity and allocation planning chain — B05 continuation (2 October 2026)

The remaining capacity evidence, site eligibility, reservation preflight, IPAM preflight
and DNS preflight implementations now live under `provisioner.allocations`. All runtime,
CI, test and documentation consumers migrated and their old script paths are retired
without aliases. `provisioner.repository` no longer imports any top-level `scripts` or
`tools`; package code is self-contained at that import boundary. See the
[allocation runtime owner contract](../engineering/allocation-runtime-owners.md).

Existing formats, status/digest/operation identities and external-owner boundaries are
unchanged. These evaluators do not reserve capacity, allocate addresses, write DNS or
contact a native platform. B23 live transactional composition, direct operator/execution
owners and B48 retained-state conversion remain open.

### Checkpointed collection scheduling — B22 continuation (2 October 2026)

The existing batch dispatcher now has opt-in local durable progress and a bounded
waiting mode. `batch-stage --state-directory` selects due unstarted work;
`batch-run` additionally waits for already-enrolled future tasks without resetting
its endpoint gates. A create-only start precedes stage, and restarted unresolved
work is never automatically retried. `batch-inspect` reads history and explicit
`batch-reconcile` invokes only the original signed-outbox inspector. Changed inputs,
invalid history, revoked original custody and uncertain completion remain held.
The journal issues no campaign, token, publication or migration authority; any new
observation still comes only from the existing independently authorized collector.

This is one private local journal, not a distributed scheduler or global endpoint
budget. Pending and unknown counts remain visible; saved outcomes are historical,
not current reviews. The unchanged human-only freshness API is not repurposed for
unattended service identities. See the [checkpointed scheduling contract](../engineering/discovery-checkpointed-scheduling.md).
Deterministic periodic freshness evaluation and digest-bound alert-intent projection are
implemented separately without native collection or notification delivery. Deployed service
scheduling, alert delivery/acknowledgement, fleet-wide admission, estate measurements and the
rest of B22 remain open. See the [periodic monitor contract](../engineering/discovery-freshness-monitor.md). The earlier blocked reservation/source-integrity refactors are not
included in this continuation; their original live callers remain unchanged.
The related process tests now use a bounded readiness/activation handshake so slow
interpreter startup does not consume the active exclusion window. Existing operation
deadlines, exit-code/signature/request-count assertions and production checks are
preserved. This is a B01 test-fixture correction, not a runtime authorization change;
failed baseline/development runs remain evidence alongside later exact-tree results.

### OpenStack referenced-image driver/security evidence — B16 continuation (2 October 2026)

Selector 4 extends the already bounded Glance read for VM-referenced images with five
Nova-consumed custom properties: VIF model, SCSI model, QEMU guest-agent declaration,
virtio-net multiqueue declaration and Secure Boot policy. Glance v2 additional image
properties are strings, so the collector preserves those values as strings rather than
coercing local booleans. Documented closed vocabularies fail closed; absent properties
remain UNKNOWN. No additional endpoint, route or privilege is introduced.

This narrows B16's driver/security evidence gap but does not prove installed guest
drivers, compute-host support, key custody, firmware state or service readiness. New
selector identity requires fresh signed campaign/credential/witness material and a new
generation; selector 3 evidence is not relabelled. Native qualification remains open.

### Package-owned fixed guest probe — B05 continuation (3 October 2026)

The fixed guest traffic/health probe now lives at `provisioner.execution.guest_probe`; the target-qualification campaign reads that exact installed file and the former tools module is retired without an alias. Existing machine-ID binding, source-address binding, socket/TLS deadlines, CA/name validation, body digest and bounded status behavior are unchanged. Installed-wheel tests require the package owner and absence of the retired path. See the [runtime contract](../engineering/guest-probe-runtime.md).

This is code ownership only: it does not install guest software, change network policy, qualify a route or authorize native contact. Target campaign authority, direct observer/orchestrator ownership, execution journals, installed service composition and B48 retained-state conversion remain open.

### Package-owned offline route audit — B05 continuation (3 October 2026)

The offline IPv4/IPv6 routed-topology model now lives at `provisioner.execution.route_audit`; active planning/input-review/local-test callers migrated and the former tools path is retired without an alias. Existing strict fixture parsing, unique address/segment ownership, directly connected next-hop, tenant/path and stateful-flow checks are unchanged. See the [runtime contract](../engineering/route-audit-runtime.md).

This model still simulates only the documented reference routing semantics. It does not contact infrastructure, configure routes/firewalls, prove vendor datapath behavior or issue production approval. Direct execution/observer owners, installed service composition and retained-state conversion remain open.

### Retired redundant repository-gate wrapper — B05 continuation (3 October 2026)

`scripts/check_repository.py` was only a subprocess forwarding wrapper to `scripts/check_repository.py` and had no live Python consumer. It is deleted rather than moved or retained as a compatibility shim; the retirement register prevents reintroduction. Historical source-transcription documentation that records the old command remains provenance, while current testing guidance already names the actual repository gate.

This deletion changes no repository-check logic, native interface, source format, authority or retained execution state. The remaining direct operator/execution owners and B48 conversion work keep B05 open.


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
state conversion. See the [runtime owner contract](../engineering/operator-readback-runtime.md).


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
[saved-plan runtime contract](../engineering/saved-plan-runtime.md).

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
| B16 | Partial signed native path with referenced-image driver/security evidence | Complete guest-installed driver/key/service and independent coverage over exact-project Nova/Cinder/Neutron/quota reads plus VM-referenced Glance metadata; do not infer compatibility from image properties. | Qualify actual catalog endpoints, versions, read roles, image visibility and service coverage. |
| B17 | Persisted drafts, signed assessment decisions, offline owner signer and custodian intake | Finish independent enrichment/dependency verification, deployed owner/key onboarding, owner-to-custodian artifact transfer and review workflows; exact observed membership and consistency decisions remain revision-bound. | Application owner confirms dependencies and useful-service acceptance criteria. |
| B18 | Durable signed tuple/route/control inputs | Complete deployed qualification import, expiry/supersession/revocation and release-ledger integration without converting operator assertions into evidence. | Source-exit and destination-operation campaigns independently qualify advertised scope. |
| B19 | Persisted generation-pinned comparison | Complete coverage and acceptance for single-VM and reviewed multi-member comparisons, exact pool/profile bindings and explicit reasons/remediation. | Reviewed policy, security, recovery and target-capacity evidence for positive candidates. |
| B20 | Initial/saved-revision authoring, exact-draft browser review and application comparison | Finish enterprise owner/review integration, owner-to-custodian artifact transfer, independent dependency verification and complete administrator acceptance; preserve stale-response and uncertain-save defenses. | Sysadmins complete comparison without hand-authoring JSON. |
| B21 | Partial proposal model | Persist no-change import proposals, ownership collisions, review state and links to exact observations; execution stays separately approved. | Native no-change/state reconciliation before ownership transfer. |
| B22 | Bounded batch, checkpointed local scheduling, custody claims, freshness/history and periodic alert-intent projection | Complete deployed service scheduling, durable fleet/global endpoint budgets, resumable estate publication, actual alert delivery/acknowledgement and measured benchmark. | Independent omission/privilege-loss reconciliation and agreed estate-scale measurements. |

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

The baseline column above records the programme starting point. The opening
implemented-boundary table records the current repository position; an implemented
owner does not close its separate native/external gate. Additional directed
drivers and full cold/Windows migration remain repository work.

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

OpenStack selector 4 retains strict allocation/image/volume/attachment and bounded driver/security facts from
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
| Wave 2 — B19/B20/B22 | Compare scoped property values, all source requirements and measured transfer assumptions; expose stable blocker/unknown reasons and remediation without hiding other destinations. | Typed comparison and relocation error isolation implemented; old signed reviews invalidated. Revisioned drafts, guided initial authoring, signed owner decisions, operator comparisons, checkpointed collection scheduling and deterministic periodic freshness/alert-intent projection exist; verified dependencies, deployed monitor scheduling/alert delivery, fleet-global admission and estate benchmark remain open. |
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
