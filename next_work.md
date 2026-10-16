## Planning consumer remediation — 2026-10-16

Resumed from `cd61437b`; hosted run
[38824590501](https://github.com/awalker0878/multi-tenant/actions/runs/38824590501)
passed all implementation, SQL/browser and nine built-binding jobs. Its strict
assurance gate remains FAIL: 388/1,073 claims, 21/271 consumer boundaries,
3/166 HTTP operations, 5/75 canonical releases; 201 boundaries lack evidence.

The Console Planning client now resolves the exact method/path and successful
response schema/status from its installed active release. Plan and assessment
reads bind record, tenant, application and environment; plan bindings also bind
plan identity, site and nested content scope. Creation receipts bind
kind and returned plan scope. Thirteen foreign-record/scope regressions and a
migration success-status regression are added. No canonical is changed.

The P05 live witness exercises the shipped client on all six core Planning
operations, over actual Governance delegation and verified TLS to Planning.
Thirty-six response substitutions must be rejected. Evidence admission checks
the exact loader, installed release, witness, campaign/proxy sources, current
run/attempt and full operation-specific negative controls. Hosted acceptance of
this correction is still required; no receipt is earned by implementation alone.
Deployment-owned Planning enrollment, native E3/E4 and other missing internal
consumer/security/event evidence remain open. Keep PR #64 draft.

The first follow-up CI passes Console quality but exposes an overstrict new
comparison between the stored-record digest and approval digest. Those are
different identities; the equality check is removed and two positive receipt
regressions preserve their meaning. The corrected witness has 36 substitutions.
A further live probe covers wrong-scope and cross-tenant requests for each of
the six operations, with valid positive controls and unchanged snapshots across
every Planning-owned relation. Its 12 security claims still require hosted CI.

## Exact Console success-status enforcement — 2026-10-15

The next correction also binds simulation success status to the requested
operation: GET requires 200; admission/commands require 202. The previous
shared 200/202 allowlist could accept a schema-valid response with the other
operation's status. Three additional Laravel regressions and live TLS status
substitutions extend the real Console witness from nine to twelve negative
controls. The evidence reader requires all twelve controls; earlier nine-case
receipts cannot qualify the new source. No active contract bytes are changed.
Current-source hosted acceptance is required.

The retained exact APK repair already passes hosted Console, Catalogue,
Assurance and Governance image builds on `b8a29397` (run 38823577600). P06
Chromium, Firefox and WebKit pass there, resolving the prior Chromium bootstrap
fault for that source. All implementation checks and all nine built image/wheel
bindings pass; the broader measured assurance gate remains separately open.
Local verification for the status correction: **237 contract tests pass**,
with PHP syntax, Pint, source-bound inventory and documentation checks passing. The last completed measured gate remains
**388/1,073 claims**, **3/166 operations**, **5/75 releases**, with **201**
boundaries still missing evidence. Native E3/E4 and Planning enrollment are
not supplied by these source/fixture checks. Keep PR #64 draft.

## Locked APK availability repair and live acceptance — 2026-10-15

On head `24079d0c44dcb22fa6411958fa21d1a319242a47`,
[run 38822505865](https://github.com/awalker0878/multi-tenant/actions/runs/38822505865)
passes Contract Integrity, Console quality (including seven new request-binding
cases), P06 PostgreSQL, P06 Firefox/WebKit, and all three P02 browser jobs.
The two passing P06 campaigns execute both independent fresh-grant epoch
fences, current-authority/cross-tenant denial controls, the real Console client,
and all nine substituted-response rejections. Chromium's Temporal namespace
setup process segfaulted; it did not reach those controls. Do not call that job
passed or claim complete browser acceptance. Overall assurance remains open.

Its measured gate now verifies **388/1,073 claims**, **21/271 consumer
boundaries**, **3/166 HTTP operations** and **5/75 canonical releases**.
This is the first fully evidenced HTTP set, not complete platform or native
qualification. The remaining 201 boundaries have explicit missing evidence.

The package availability defect now has a source repair: each isolated PHP
build context retains the previously retrieved **exact locked zlib APK**.
All copies match the existing length/hash; no version, lock, source URL, image
base or signature trust changes. Strict build-context validation covers the
cache, and the real downloader rejects same-length tampering. Offline APK
signature verification remains mandatory. **91 P01 tests pass**, including six Alpine input tests; all
four exact context inventories include the retained bytes; actual PHP transport
accepts the original and rejects a corrupted copy without network access.
Current-source image builds must verify this repair before claiming resolution.
The external Planning registry and real native E3/E4 commissioning remain
unavailable, and missing internal evidence is still separate unfinished work.

## P02 broker startup correction — 2026-10-15

The retained P02 Firefox/WebKit failure artifacts from run 38821391028 show
`/var/lib/rabbitmq/.erlang.cookie: eacces`, not a generic readiness timeout.
P02's root health check could create a root-owned private cookie while the
image entrypoint was switching to the RabbitMQ account. Both P02 fixtures now
run health diagnostics as `rabbitmq`, matching the existing P03/P04 correction;
post-start diagnostics also select that user. TLS, signatures, readiness
requirements and the 90-second bound remain enforced. Current-source CI is
required. The new epoch PostgreSQL/ASGI callback-chain case already passes on
head `33c45188`; final live fencing/Console witness acceptance is pending.

Additional local verification at `5b0ee831`: **390 Lifecycle tests pass**, with
**86 PostgreSQL cases skipped** locally; complete Lifecycle Ruff, formatting
and strict mypy pass. The independent protected Planning registry remains
absent and its actual loader returns `None`. Three official Alpine mirrors
also return 404 for the unchanged locked zlib artifact. Missing internal
assurance evidence remains open independently of these external dependencies.

## Current Console binding correction — 2026-10-15

The actual Console `JobsClient` now binds simulation reads to the requested job,
admissions to their plan ID/digest/approval, and command receipts to job, command
key and action. Valid schema and tenant scope alone did not enforce these
bindings. Seven focused Laravel regressions and a live TLS witness challenge
nine schema-valid or uncontracted substitutions against the real client and
owner. Only current-source successful campaigns may contribute the three
executed Console consumer receipts; source, loader, installed release, artifact,
run attempt and negative-control identities are checked independently.

Run [38821391028](https://github.com/awalker0878/multi-tenant/actions/runs/38821391028)
for `33c451881329c217004b318f521c71c1763e3633` is not accepted: the new
wrong-scope probe revealed Governance's 401 delegation denial propagating as
workload reauthentication after Lifecycle had authenticated the caller. The
Lifecycle actor boundary now maps that specific upstream 401 to forbidden 403;
403/404/503 remain unchanged and no authority is granted. Four focused Python
regressions, Ruff and strict mypy pass. **237 contract tests pass** locally;
the newly added Laravel and final live controls require CI.

An independent image build failure on that run is an upstream 404 for locked
`zlib-1.3.2-r0.apk`. Direct retrieval (including a cache-bypass query) also
returns 404; the previously retrieved 56,195-byte artifact matches the existing
SHA-256 `b636306cbf8a0c15493b38de608ba11605fd8f11ade631f5ece6f7fdf5a1e09e`.
Do not relax the byte lock, silently upgrade the package or claim a final
built-image binding without a successful source-pinned build. Other missing
contract evidence remains internal work; this availability issue does not
reclassify it as externally complete. Keep PR #64 draft and do not merge main.

## Resume checkpoint — isolated fencing and authenticated denials (2026-10-15)

Exact branch head `e7cde0aa25471d7f83064c2583d8f9e85d254cc8` completed
[CI run 38786986460](https://github.com/awalker0878/multi-tenant/actions/runs/38786986460).
All service quality, PostgreSQL, live P02–P06 browser journeys and nine
built-contract binding jobs pass. The run tests PR merge revision
`fdb5d0e1a731fdec69273c8e1cbf8980c58b2c9e`; this is not a deployment result.
Contract assurance remains red: **379/1,073 claims**, **18/271 consumer
boundaries**, **0/166 qualified operations**, **4/75 qualified releases**.
Missing internal consumer/security/producer evidence remains engineering work.

Current changes add two independent live epoch controls using one fresh durable
grant: effect-owner epoch mismatch, then journal-owner epoch mismatch, then
acceptance and duplicate suppression with the exact same grant. Both denials
must occur before expiry and leave the effect count unchanged. This isolated
fault injection precedes the restore exercise and cannot re-enable a restored
journal. Authenticated wrong-scope and cross-tenant probes now cover Lifecycle
admission, job reads and commands; each requires a positive control, independently
validated requests/responses, no protected identifier disclosure and unchanged
snapshots across eight Lifecycle tables and the independent effect ledger.

Local verification: **235 contract tests pass**; canonical integrity, publication/retirement,
quality-policy cutover, source-bound inventory and documentation checks pass.
The new PostgreSQL/ASGI case and live journeys require hosted CI.

Source/attempt/artifact-bound security evidence ingestion remains fail closed
on stale sources, malformed probes, missing positive controls, state changes,
disclosure or failed campaigns. These new live/SQL controls need current-source
CI before acceptance. Protected Planning enrollment, independently commissioned
providers and E3/E4 native evidence remain external dependencies. PR #64 stays
draft. Do not merge main or infer production/native authority.

## Fencing probe transport correction — 2026-10-15

On head `3c58fa74379c093eaa213448c75b28488d43809d`, P06 Chromium, Firefox and WebKit
and the PostgreSQL callback-chain suite pass. Direct fencing probes now send the
required canonical replay key; a separate regression proves these headers
reach the actual strict worker endpoint and that a key bound to another
attempt is rejected. The seal probe requires an unexpired grant. The restored
old-grant test is explicitly limited to continued denial, with fresh-grant
live epoch isolation still open. Current-source CI remains required for this
probe correction; no complete security or release qualification is claimed.

## Current callback correction — 2026-10-15

On head `648daafa3e9bbe09785c8b18e888dfe7363b9b9b`, the P06 PostgreSQL
suite including the new acquired-grant/worker-HTTP test passes, while live
execution still holds at migration reserve. Lifecycle's redemption HTTP
handler contains a second hard-coded worker name. It now passes the canonical
worker UUID from the request into the existing journal/campaign checks, after
authenticating the simulator audience. A UUID does not bypass journal, grant,
campaign, expiry, custody or single-use checks. Regression coverage now includes
the real Lifecycle redemption ASGI callback as part of the PostgreSQL-to-worker
HTTP chain, plus local valid/invalid route argument checks. No passing live
P06 result or complete assurance is claimed before current-source CI.

## Current CI finding — typed simulation worker identity (2026-10-15)

Run 38782109274 on head `dbbcb1196f3dd32efb82fdae4685c3edd041f8b8`
passes P05 live journeys in Chromium, Firefox and WebKit, all nine image
bindings, database authority and current contract checks. P06 reaches actual
simulation effect execution, where the producer's hard-coded `sim-worker`
identity violates the unchanged UUID effect contract. The poller/witness now
use an explicitly configured and campaign-enrolled UUID; grant acquisition
and redemption reject invalid identities before durable access. Crash witness
payloads also remove the local `completed` flag before effect-owner transport.
The stricter worker schema remains unchanged. A real PostgreSQL-to-worker-ASGI
contract regression is added; local PostgreSQL startup is blocked by the
execution environment's UID mapping (`chown` returns EINVAL), so that new
case must execute in CI. Local Lifecycle units: 384 passed, 86 database cases
skipped; Ruff and strict mypy pass.

The live producer-evidence ingestion now works in CI: **372/1,073 claims
verified**, **0/166 qualified HTTP operations**, **4/75 qualified canonical
releases**. Missing consumer/security evidence remains repository-owned work;
protected Planning enrollment and actual native E3/E4 evidence remain separate
external dependencies. No completion, merge or production qualification claim.

## Contract remediation resume — 2026-10-15

Current source repairs preserve exact runtime proof matching and fail-closed
qualification. Planning rereads Inventory once when an independently verified
Assurance receipt identifies a newer runtime proof; changed native scope or
installed identity is rejected and a continuing mismatch remains held. Plan
input digests exclude only observation freshness at known measurement paths;
policy, scope, sequence, readback and recovery event times remain pinned, and
all current freshness/expiry checks still execute.

P06 now enrolls independently signed E2 fixture dossiers and scope-bound keys
for each new campaign, publishing current runtime proofs before the registry
entry. Fixture renewal includes nested network and isolation observations.
P05 browser revocation waits for the explained authority hold, and failed
initial assessments are retained for diagnosis.

Local Planning verification: **609 passed, 22 PostgreSQL cases skipped**;
Ruff and strict mypy pass. The full contract suite passes **226 tests**,
including the actual PHP verifier with signed snapshot renewal and negative
controls. Follow-up source fixes correct random workload/pool ordering and
rebuild campaign observations at enrollment time; stale initial observations
remain rejected. Successful current-run journey wire measurements are now
consumed as producer proof only, with separate consumer/security/image gates. These repairs are **not accepted** until the current-source live
CI journeys pass. The broader contract assurance gate and external protected
Planning enrollment/native E3/E4 evidence remain open. PR #64 stays draft.

## Contract framework: Phase 4 and Phase 5 closeout (2026-10-12)

**Phase 4 — executable capability qualification:** E2 implementation strengthened.
The worker's published 5-method × 6-mode matrix must be present in executed,
non-skipped JUnit evidence. The native data-method registry must match exactly
the declared handlers; every implemented method/stage must run the full 3×3
platform-direction matrix, complete negative fault matrix, independent dataset
readback, source capture and revocation tests. Duplicate JUnit cases, skipped
tests, inaccurate suites and missing dispatch evidence fail closed. The
software result remains E2; **no installed E3 or independent E4 reviewer/site
qualification or native-write authorization is inferred from unit tests.**

**Phase 5 — framework consolidation and governance:** Contract integrity is
partitioned into schema, event, canonical-registry and HTTP/authority invariants
with a small orchestrator, and tests import their actual invariants rather
than a compatibility shim. Removed the three-sample byte-parity check and
regex-only route checker: full installed-copy inventory and executable route
conformance remain authoritative. An independent retirement report and optional
strict workflow gate cover every current historical retirement.

**Unclosed external dependencies:** all 53 pre-enforcement canonical retirements
remain `not-independently-verified`. The external client inventory, contractual
disposition, independent approvals and proof of supported version removal cannot
be created by this repository. Obtain actual reviews before claiming Phase 5
governance closure. A recent commit has no published completed required check
results; P08, Capability Assurance and Contract Integrity must pass at the exact
final SHA before changing PR #64 from draft. E2 tests are not an E3/E4 substitute.

See [contract implementation and qualification assessment](docs/contracts/phase4-phase5-review.md).

# Current next work — Capability runtime assurance (PR #64)

> **Authoritative queue for this branch.** Other handoffs below are archived
> background and must not override this queue. Update this section whenever
> a task is completed, blocked, or newly discovered. Branch:
> `codex/capability-runtime-assurance-audit-fixes`; review:
> [PR #64](https://github.com/awalker0878/multi-tenant/pull/64); base `main`.
> Keep the PR **draft**; no automatic merge or native production activation.

**Source baseline:** `09a5285cdb74808d927a9be3720ac636451f07a6` at this queue's
creation (2026-10-08). Follow-on commits supersede this SHA. All statuses
below mean **engineering implemented / unverified** unless an exact-source
CI result or independent native evidence is linked. E2 fixture success is
not E3 native proof; E3 native proof is not E4 receiving acceptance.
Check the updated `git rev-parse HEAD` and the
[PR checks](https://github.com/awalker0878/multi-tenant/pull/64/checks)
at every checkpoint.

## CT-API-AUTH — Service authority-boundary contract coverage (2026-10-11)

**Implemented, unverified.** The unversioned Assurance `planning-qualification` alias is removed in favour of the active `planning-qualification-v2` operation; the controller no longer rewrites its response to v1, and a negative route test guards retirement. The broader M0–M6 coverage plan is in progress. No exact-head green CI URL has been recorded; do not claim it verified or increase E2 evidence to E3/E4. This queue entry is updated before the contract ledger.

- 2026-10-11 contract boundary checkpoint: four new authority OpenAPI releases, two-direction Laravel route conformance, six Inventory PlanningInputApp paths, hard-coded owner canaries, immutable historical UUID allowance and shared error schema implemented on this branch, still **unverified** (no exact-head successful CI URL). Error and command retry decisions are in `docs/contracts/adr-service-authority-errors-idempotency-2026-10-11.md`. Full producer-status execution and remaining ASGI reverse-route enumeration are still outstanding; E2 is not E3/E4.

**Living execution plan:** [Authority-boundary contract coverage](docs/implementation/authority-boundary-contract-coverage-execplan.md). **Status: Implemented, unverified**. Native status coverage and exhaustive Python reverse route mapping remain open; no exact-head green CI run recorded. The unversioned Assurance alias was intentionally removed at the user's request.

- 2026-10-11 additional boundary closeout: Governance collection/native approval status releases are now v1.1 (historical v1 retained), with explicit status canaries. Inventory discovery has a negative undocumented-route test. This remains **Implemented, unverified** without an exact-head green CI run or comprehensive per-status Laravel tests.

- 2026-10-11 CI diagnostic: an earlier head's three Laravel route-conformance jobs passed, but integrity failed because Catalogue's embedded `#/$defs/Intent` reference was not rebased under OpenAPI components. The reference was relocated and an exact schema projection canary added. The corrected exact head is **unverified** pending a new CI run.

### 2026-10-11 follow-up: fix contract audit and retire compatibility shims

**Engineering changes committed / CI unverified.** The audit's historical UUID digest-object comparator and its 101-file legacy compatibility SHA allowlist are completely retired; current authority releases enforce canonical lowercase UUID directly, with a source-backed v4 migration payload exception. The nonfunctional Inventory internal Planning-input UUID-as-integer read alias was removed, and the active v1.3 OpenAPI plus producer conformance reflect that removal. The active Inventory worker contract covers all four collection endpoints with reverse conformance, HTTP status/shape probes, and explicit `native_write_authorized=false` receipt limits.

Required `X-Actor-Delegation`/`X-Planning-Action` headers and actual Governance 409 bound-plan digest conflict are contracted and regression checked. Canonical owner response schemas are regenerated to separate candidate output and checked against immutable active releases in CI, with one shared Inventory migration v4 component replacing its duplicated 200-response copies. The composed Planning router now dispatches workload-readiness and internal placement reads. Planning and Lifecycle runtimes now fail closed for unregistered `/v1/`/`/internal/` routes and their explicit full HTTP-operation manifests are compared against separately published active contracts. Previously uncovered Planning native/invalidation and Lifecycle internal placement/simulation authority paths now have active registered releases. The obsolete P00 synthetic compatibility runner, fixtures and workflow were removed while historic published releases remain immutable.

**Still open:** exact-head real CI green; independent producer/status/body validation for every Laravel operation and all Planning/Lifecycle owner status branches, not only owner-specific route and representative error probes; real E3/E4 native qualification (explicitly out of scope). Until a successful real CI run is recorded, PR #64 remains draft and **no native-write authority is granted**.

## CT-R01 — Resolved migration-readiness contract (2026-10-09 checkpoint)

**Current branch work committed, not yet end-to-end verified.** See
[resolved migration-readiness commissioning ledger](docs/implementation/resolved-migration-readiness-rollout.md)
and the closed contract at `contracts/schemas/planning/migration-readiness-v2.2.json`.
This work deliberately preserves Catalogue desired intent, Inventory native facts,
Assurance qualification/receiving decisions, Planning composition and Lifecycle
native authority. **Do not merge or promote PR #64 on these changes alone.**

| Phase | Engineering result | Required exit evidence / remaining work |
| --- | --- | --- |
| 0. Native reads | Inventory OpenStack profile completion counts independently retrieved Neutron security groups; AHV workload reads select namespace-specific configured v4.2/v4.3 | Manifest-derived read ledger and safe SG-heavy budget handling; versioned readback and negative native probes |
| 1. Catalogue↔Inventory source | Pure `source_intent_reconciliation.reconcile` compares owner-confirmed logical/native IDs, generation, CPU/RAM, disk/NIC, firmware, Secure Boot, dataset map, dependencies | Authenticated current Catalogue+Inventory owner ports, immutable confirmed links, persisted diff and Planning/Lifecycle effect wiring |
| 2. Collection field coverage | Pure Inventory `migration_collection_coverage.evaluate` evaluates all scoped manifest rows, freshness, applicability and external owner receipts | Durable raw/field observation ledger, worker binding to native requests, service-only Inventory projection, UI holds and native effect recheck |
| 3. Installed API/version | Planning per-operation Assurance evidence required; selects lowest qualified installed version; AHV source VMM/Prism/ClusterMgmt API calls no longer hard-code all v4.3 | Native operation-to-adapter code manifest for **all** routes; runtime endpoint/entitlement probes and every version/method negative case, E3 reviewer/E4 receiving records |
| 4. Single resolved contract | Planning `MigrationSupport.read/require` resolves route readiness; protected Planning execution-plan includes same fresh receipt; Console displays status/holds; Lifecycle verifies scope/digest/route/version/method/E3/E4/API on each current owner read | Bind per-workload reconciliation and field collection into exact service-only receipt; cross-service TLS/revocation/failure matrix, complete CI |
| 5. Qualification/rollout | Added Inventory/Planning/Lifecycle unit regressions and a closed JSON schema | **NOT complete**: required head CI queued; foundation package/bootstrap workflows early failure; independent real E3/E4 trials and authorization absent |

The v1 contract is **route-level only**, explicitly `workload_admission_authorized=false`
and `native_write_authorized=false`. It must not be cited as proof a specific
workload meets Catalogue intent or that all manifest fields were collected.
Actual deployment requires separate live workload admission and installed
operation evidence, with independent Assurance decisions. Existing native
custody, Governance and confirmed Inventory checks remain mandatory.

## Follow-up capacity correctness (current branch)

Five additional source-bound corrections were committed after the original PR #64
audit remediation. They remain **E2 code/tests, pending exact-head CI**:

- `5beb911`: Planning counts each NIC's observed address families rather than
  counting each NIC once; dual-stack now requests two addresses.
- `c6d0386`: Lifecycle permits a physical pool to advertise additional
  unused class limits without raising an indexing exception.
- `7ca2c29`: Lifecycle rejects contradictory storage-class and
  network/address-family subtotals in a requested placement vector.
- `0c99268`: When a commissioned pool enforces class-specific capacity, a
  positive allocation must identify the classes being consumed.
- `7f0253a`: Reconcile class-specific subtotals again after all workload
  allocations are aggregated, so a partially unclassified multi-VM request
  cannot evade the physical resource limits.

Associated Planning and Lifecycle regressions are committed. **Do not mark
CT-N01, CT-N08 or A04/A05 accepted** until hosted Python/PostgreSQL checks
complete on the exact head and real exclusive capacity-owner evidence is
independently accepted. No change grants native write authority.

## Active, prioritized work queue

| ID | Priority | Owner / boundary | Status | Required next action and completion evidence |
| --- | --- | --- | --- | --- |
| CT-N01 | P0 | Engineering / CI | **BLOCKED: queued/early workflow failures** | Obtain a finished result for **every required check** on the exact PR head, including Assurance PostgreSQL, P05 Planning, Lifecycle, Inventory and capability assurance. Fix the actual failures, rerun, attach exact run/job URLs, no skipped or unrun mandatory checks. All 39 checks on head `7a17079c396dcb1d39b7c038fdf3cddf1a56f667` were queued when last inspected. |
| CT-N02 | P0 | Assurance + Planning / PostgreSQL | **Implemented, unverified** | Run disposable PostgreSQL migrations `services/assurance/database/migrations/002_qualification_authority.sql` and `services/planning/migrations/003_qualification_invalidations.sql` from scratch; confirm least-privilege role grants, append-only history, epoch triggers, outbox/inbox commit-before-ack, atomic failure and rollback. Retain tests and full execution logs. |
| CT-N03 | P0 | Planning / P05 CI | **Implemented, unverified** | Prove `scripts/p05/qualify.py` and P05 live jobs exercise the new qualification inbox, read-boundary guards, concurrent plan-save/revocation and tenant isolation; run Ruff format/lint, mypy and the database tests. Capture source-bound pytest/JUnit artifacts and fix failures. |
| CT-N04 | P0 | Assurance → Planning / E2 composed delivery | **PARTIAL: real Planning DB/ASGI replay test committed** | Provision **disposable** HTTPS/TLS peers and independent tokens; publish a real Assurance SQL event, relay, persist Planning inbox, return exact durable receipt, and deny/hold affected execution. Test lost response, same-event replay, stale/out-of-order epochs, conflicting identity, tenant isolation, TLS failure, sink outage and restart. No accepted E2 cross-service result yet. |
| CT-N05 | P0 | Security / receiving trust | **OPEN** | Commission TLS certificate/SAN/CA, distinct caller secret custody, network-only ingress authorization, bounded retries, audit logs, receiver ownership and replay/quarantine policy. Verify no reviewer/observer/owner token reuse. The private endpoint is **code only**. |
| CT-N06 | P0 | Planning/Lifecycle / fail-closed authority | **E2 boundary tests added; live revocation OPEN** | Test every approval, execution, native effect, placement, and retry boundary against **current** Assurance authority, not only a cached hint. Ensure delayed/missing invalidations and unknown scope always hold. Add cross-service revocation between preflight and effect and revoked approval replay. |
| CT-N07 | P1 | Assurance + Planning / contract | **E2 strict receipt/vectors coded; CI OPEN** | Prove byte-for-byte PHP/Python canonical scope hash and wire schema compatibility for representative Unicode/slashes, installed tuple, tenant, action/method, null decisions, and epochs. Reject unrecognized/changed event contracts; preserve append-only event IDs. |
| CT-N08 | P1 | Capacity owners / P07 | **E2 current vector/class readback coded; native owner OPEN** | Replace proposed/synthetic capacity with operated owner-backed **exclusive** reservations per physical CPU, memory, storage and address source; check source generations and native readback; verify collision, expiration and multi-owner compensation. No fabricated physical capacity receipt. |
| CT-N09 | P1 | Native VMware → OpenStack / E3 | **NOT RUN** | Enroll installed-source tuple, export/export lease, guest OS/driver/UEFI, disk conversion/import, native target and independent observer receipts; run selected `VM_COLD_EXPORT` positive, refusal, resume and rollback cases under approved authorization. Do not infer native support from test fixtures. |
| CT-N10 | P1 | Native network/isolation/recovery / E3 | **NOT RUN** | Qualify real IPv4/IPv6 flows, VRF/VPC tenancy, return paths, ingress/egress, RBAC, keys and storage, topology/fault domains, failure-trigger RTO/RPO, application/dependency recovery and source/target fences with independent observations. |
| CT-N11 | P1 | Assurance reviewer + receiving owner / E3/E4 | **NOT REVIEWED** | Obtain evidence-bound independent E3 reviewer decisions and E4 receiver sign-off on actual native recovery, service ownership, accepted residual risks, monitoring and operating runbooks. Missing credentials/decision authority cannot be replaced by mock acceptance. |
| CT-N12 | P1 | Platform governance / shadow adoption | **E2 read-only comparator coded; native shadow OPEN** | Read-only shadow comparison of qualification decisions, profile/adapter behaviour and native outcome changes; reconcile false confidence, stale qualification and method catalogue differences. Record rollout/rollback gates, versioned replay and promotion authority before any cutover. |
| CT-N13 | P1 | Verification / A01–A16 | **PARTIAL: E2 tests mapped, source CI/native OPEN** | Build and run the complete source-bound acceptance matrix with positive, negative, timeout/retry, cross-tenant, authority-revocation and native-effect cases. Map each A01–A16 to code, test and evidence in the implementation ledger; do not close an A-ID with a mere fixture. |
| CT-N14 | P0 | Planning + Assurance + Inventory + Console / vendor API compatibility | **PARTIAL: version-aware E2 path and on-screen alerts committed** | Extend exact route `api_usage` coverage to every actual migration method/callsite; live-discover and pin per-site API versions/entitlements; qualify negative+positive probes, E4-approved optional omissions with effect suppression, and end-to-end version/failover readback. Detailed CT-API tasks below. |

## CT-N18 — Source-gated destination fields and native API-backed selections

**E2 code and tests committed; independent/native E3/E4 OPEN.**
[Design, source observation and security requirements](docs/implementation/source-gated-destination-selection.md).

- The Console's **feature-level destination view** now filters to
  source-observed relevant attributes, while separately reporting missing
  mandatory source facts as blockers. Absent source data never creates
  a selectable destination candidate.
- Destination selectors appear only when the source has the relevant
  property: source observed NICs -> network mapping, source AHV
  categories -> optional category options, source guest identity ->
  host-scoped VMware guest/hardware dropdown, source Neutron security
  groups -> destination policy/security-group mapping. Missing source
  firmware is **unknown**, not silently BIOS.
- Destination options come from the current API-owned target profile.
  OpenStack Neutron `GET /security-groups` is collected project-scoped
  with rule IDs, rule checksum and a normalized flow-semantics SHA.
  Source OpenStack ports supply source SG IDs; source SGs are individually
  reread from their scoped native API. The Console only offers target SGs
  with identical source/target normalized security rule semantics.
  The backend rejects forged/foreign/duplicate/missing/unequal mappings.
- AHV policy/category/subnet options use the existing Prism v4 native
  resource inventory; only observed ENFORCE policies are selectable.
  Source policy unknown => no policy picker or synthetic mapping.
  Cross-provider AHV/Neutron security equivalence is not inferred
  from labels or ENFORCE state: the review can be saved **as draft**
  but cannot be confirmed until native E3/E4 is available.
- VMware host compatibility now comes from pinning the native
  `HostSystem.parent -> ComputeResource.environmentBrowser ->
  EnvironmentBrowser.QueryConfigOption(host)` read-only VI/JSON
  sequence, with per-host guest IDs and observed vmx version.
  The backend rejects invented guest/hardware/host values.
  Source v1 VMware does **not** collect full NSX/firewall flows.
  VMware destinations do **not** yet supply a full policy-rule
  catalogue; critical required flows are held from confirmation.
- Inventory `WorkloadProfiles.review` adds explicit holds for missing
  source security discovery and cross-provider unsupported/unevaluated
  policy translations; `migration_confirm` and Planning reject held
  reviews. Operator evidence references are not substitutes for
  native source/target network observations.
- Domain/worker tests added for source-only filtering, forced
  dropdown selection, Neutron semantics and VMware guest options.
  Exact-head hosted CI, E3 and E4 are NOT asserted as passed.

**Follow-on work:** Commission source-effective AHV microseg policy
discovery and VMware NSX/ACL source + destination APIs, qualified
Neutron-to-Prism/NSX semantic translation, source/target native
readback and allow/deny traffic probes; provide a separately
authorized missing-feature waiver only for nonfunctional E4
suppressed effects. Review constraints **immediately before native
effects**. Resolve the paused/queued hosted CI and end-to-end UI
tests before declaring release eligibility.

## CT-N17 — Feature-wise portability, mandatory owner inputs and Console validation

**Declarative feature policy and Console review guidance committed (E2 only):**
[feature policy](contracts/capabilities/migration-feature-policy-v1.json),
[JSON Schema](contracts/schemas/capabilities/migration-feature-policy-v1.json),
and [operator/feature responsibility table](docs/implementation/migration-feature-portability-and-console-requirements.md).

- **30 feature areas** from all 116 field crosswalk groups; **28 critical**
  at feature-level (worst-case group severity), **2 conditional optional**
  (nonfunctional metadata and nonessential QoS); **27 owner/independent
  evidence requirements** bound to existing review and operator-readiness
  identifiers, with source applicability and maximum ages retained.
  Critical conditional attributes remain required when applicable and
  cannot be made optional by a missing API or operator opinion.
- All **nine directions** produce candidate mappings only: numeric
  normalization with readback, qualified native adapter, operator plus
  independent validation, or no direct field requiring a qualified
  alternative. No route is auto-qualified from field equivalence.
- `apps/console/resources/js/pages/inventory/Migration.vue`
  shows per-direction feature treatment and a mandatory owner/
  independent evidence checklist. It **never claims the entries
  are verified**; missing review inputs disable save and confirmation.
  It links to existing operator-readiness fields for service, scope,
  security, RTO/RPO, reservation, backup, policy and recovery.
- `services/inventory/tests/test_workload_profiles.py` now tests
  the existing authoritative Inventory review validation for all
  eight owner references, the conditional delta, disk dataset
  coverage and accepted objectives.
- `scripts/assurance/test_migration_feature_policy.py` validates
  complete crosswalk groups, nine-direction bindings, operator
  Console field names, criticality/age, impossible affirmative
  qualifications, and byte-identical Console projection. Included
  in `capability-assurance.yml`. Browser test covers the warnings.
  Hosted **CI remains unverified at the exact head**.

**Still required for completion (do not declare 30 features qualified):**

1. Make the authoritative Inventory read expose per-feature current
   native/owner evidence with version, expiry, condition applicability
   and exact source profile/site/tenant/application binding.
2. Join per-VM review values with operator-readiness evidence and
   Assurance independent E3/E4 receipts at the **server**. The
   separate operator-readiness screen currently records references;
   it does not yet prove per-VM completion or enforce those references
   at native-effect admission. Do not use Vue completeness as authority.
3. Add operator selection/acceptance of actual optional omissions
   with source/target impact and signed E4 effect-suppressed witness,
   including post-approval drift/revocation handling.
4. Execute all 30 feature transformations against real versioned
   VMware/Prism/OpenStack APIs and native effect/rollback/readback
   tests; qualify approved target substitutions, security allow/deny
   and application/service outcomes for each of nine directions.
5. Reconcile latest PHP/Python/Vue/browser CI, independent E3 labs
   and E4 receiving sign-off. Keep PR draft until gates pass.

## CT-N16 — Versioned VMware, AHV, OpenStack field crosswalk

**Complete field-level data mapping; native translation OPEN.**
The [machine-readable crosswalk](contracts/capabilities/migration-field-crosswalk-v1.json)
and [full readable 116-row matrix](docs/implementation/migration-field-crosswalk.md)
reconcile **all 278** current manifest attributes (VMware 86, AHV 89,
OpenStack 103) into **116** canonical source/target/owner groups.
Every original attribute is referenced **exactly once**. The crosswalk
preserves exact API field/source, role, collection method, criticality,
minimum observation TTL, conditional applicability, and missing platform
equivalents. No row claims installed support or a qualified adapter.

- 59 groups have source-field entries for all three platforms, of which
  27 are separately attested common owner/independent obligations;
  57 groups lack at least one platform field; 45 are explicitly
  platform-specific. Null means **no mapped field / unknown**, not
  an automatic assertion that the destination is unsupported.
- Only power state, total CPU, memory and MAC have explicitly described
  proposed field normalizations. Storage backing/disk sharing, export and
  import, incarnation, boot/guest drivers, network security and policy,
  quotas and entitlements remain semantic qualification boundaries.
- `contracts/schemas/capabilities/migration-field-crosswalk-v1.json`
  supplies the closed data schema. `scripts/assurance/validate_migration_field_crosswalk.py`
  rejects any lost/duplicated manifest entry, forged API field, scope
  drift, criticality downgrade, too-generous freshness or inferred
  native support. Eight negative/positive regressions live in
  `scripts/assurance/test_migration_field_crosswalk.py`. The
  `capability-assurance.yml` E2 lane runs both explicitly. **Hosted CI
  source verification and native E3/E4 remain OPEN.**

**Outstanding integration:** resolve the crosswalk against installed,
version-qualified source and destination observations; implement executable
typed normalization and conversion/adapters; compute nine directed migration
reports with per-VM critical blockers and optional-E4 omission alerts;
include readback, backend-specific device/storage/network/rule semantics and
version/entitlement revocation at each Lifecycle effect. Reconcile exact-head
CI and signed independent E3/E4 evidence. A crosswalk is not an execution
license or an automated migration method.

## CT-N15 — Per-VM API collection manifest and freshness obligations

**Requirements/data committed**, not a completed installed discovery,
qualified API operation or runtime integration. The source of truth is
[the collection manifest](contracts/capabilities/migration-collection-manifest-v1.json)
and its [closed JSON Schema](contracts/schemas/capabilities/migration-collection-manifest-v1.json).
It identifies every currently documented source/destination attribute,
API field or owner-evidence input, collection method, maximum acceptable
age, criticality, applicable conditions and source collector module.
[Policy and source coverage](docs/implementation/migration-collection-manifest.md).

| Platform | Source VM | Destination | Owner/independent | Total |
| --- | ---: | ---: | ---: | ---: |
| VMware | 44 | 15 | 27 | 86 |
| AHV | 41 | 21 | 27 | 89 |
| OpenStack | 48 | 28 | 27 | 103 |
| **Total** | **133** | **64** | **81** | **278** |

Test `scripts/assurance/test_migration_collection_manifest.py` checks
native AHV/OpenStack source contract field names, mandatory disks, network
and recovery evidence, scope/custody, uniqueness, file references, stale
power/physical-capacity limits, operator attribution and safe optional
classifications. The existing `capability-assurance.yml` E2 lane now
runs an explicit manifest step. These tests are **committed, not yet
confirmed green at the exact PR head**.

**Remaining to close CT-N15:**

1. Implement the platform-specific Inventory collectors for **every**
   manifest row and method, including complete pagination, version and
   scope binding, operator inputs and independent probe results. The
   `native_field_candidate` label must never be interpreted as already
   collected or supported.
2. Persist append-only evidence with identity, exact API version, observed
   timestamp, expiry, signature/source, interpretation and revocation.
   Enforce max age and conditional-critical applicability at Inventory,
   Planning and immediately-before-effect Lifecycle admission. A changed
   API/identity/backing/topology/policy invalidates a record before TTL.
3. Display per-VM uncollected critical/optional fields and correct
   remediation to administrators, with evidence provenance and actual
   suppressed-effect receipts. Preserve required firewall and negative
   isolation as critical. Add contract, DB, version-drift, loss/retry,
   native E3 and receiving E4 tests.
4. Check native storage, host capacity and project entitlement separately
   from advertised maximums. Current physical capacity/reservation has
   a distinct critical 15-second field; it cannot be inferred from
   datastore size or a Cinder/Placement resource type declaration.

## CT-N14 — Migration API-version compatibility and administrator warnings

[Design, source paths and trust model](docs/implementation/migration-api-capability-compatibility.md).

**E2 code committed, not native support commissioned:** Planning's
`domain/api_compatibility.py` evaluates per-feature, per-environment
negotiated API versions and entitlements. `migration_support.py` gates
current route preview and admission using separately reviewed Assurance
`migration.api_records` evidence. Existing Planning native validation
rechecks this on plan create and execution. Console displays **critical
blockers**, **optional warnings** and a per-feature selected API version.
The active Assurance qualification API carries the implemented API-evidence projection; a separate vendor-documentation record schema has not been published. Native disk source and target
adapters for VMware/OpenStack/AHV have code-level usage tags with a
static test. This is still a **partial rollout**: historical routes lacking
`api_usage` are visibly labelled unassessed rather than falsely claiming
per-feature verification.

| ID | Priority | State | Required closure |
| --- | --- | --- | --- |
| CT-API-01 | P0 | **OPEN** | Populate official per-API release, spec SHA/URL, version introduction/change/deprecation/sunset catalogue for vSphere VI/JSON/REST, Nova/Neutron/Glance/Cinder/Placement and Prism v4 namespaces. Mark unknown dates, do not guess. Run spec diff + semantically versioned contract tests in CI. |
| CT-API-02 | P0 | **OPEN** | Enroll exact VMware, OpenStack and AHV installations; observe version ranges, extensions, available namespaces, caller permissions, license entitlements, source identity, observation timestamps and TTL. Independently verify every API version before it enters a route. |
| CT-API-03 | P0 | **PARTIAL** | Expand code-derived capability tags beyond disk capture/import to VM boot/power, guest preparation, storage formats, network, recovery, data/application interfaces and platform-specific calls; enforce required usage coverage for every selected method and all nine directions. Source tags are not yet a complete static call graph. |
| CT-API-04 | P0 | **OPEN** | Build bounded live capability probes (authorized create → read → cleanup, with loss/retry/reconciliation and negative tests) per installed API version. Retain E2 contracts separately from native E3 owner evidence; document operations impossible to test without effects. |
| CT-API-05 | P0 | **PARTIAL / unverified** | Commission Assurance's separately reviewed `migration.api_records` entitlement/observation binding and test producer→Assurance→Planning with real signed E3/E4 records, negative tamper, expiry, multiple versions, missing permissions, wrong scope and revocation. All source-bound PHP/Python/UI CI remains unverified. |
| CT-API-06 | P0 | **PARTIAL** | Administrator alert UI and impact reasons are implemented. Commission owner-reviewed E4 acceptance for nonessential omissions, verify exact `effect_suppressed_sha256` against a real skipped native operation, persist and display audit/notification/acknowledgment, and reject missing approval or suppression. Required firewall and tenant-isolation flows are **never** an optional bypass. |
| CT-API-07 | P0 | **OPEN** | Persist each qualified selected API family/version and required capability set with immutable migration/native effect grants; re-check current owner API versions, entitlements and capability qualification immediately before every write and retry; hold if version or adapter bytes changed. |
| CT-API-08 | P1 | **OPEN** | Model independently qualified adapter substitutions when destination lacks the source capability. Require equivalent outcomes, target API probe, approved adapter identity/expiry and native negative cases; an unqualified mapping must be blocked. |
| CT-API-09 | P1 | **OPEN** | Execute A01–A16 + multi-version E2 campaigns and native E3 migration tests across all three platforms. Validate admin accessibility, security effects, actual optional suppression, alert delivery and independent E4 receiving sign-off before rollout. |
| CT-API-10 | P0 | **REQUIREMENTS COMMITTED, COLLECTOR INTEGRATION OPEN** | Enforce [VM migration collection manifest](docs/implementation/migration-collection-manifest.md) per source VM and candidate destination: 278 version-controlled attribute rows, separate native/vendor fields and owner evidence, max-age and conditional-critical requirements, append-only observations, API-version scope, signed provenance, missing-fact holds and administrator omission warnings. The data/schema/static coverage checks are added to CI; live collector enforcement, end-to-end tests and E3/E4 remain open. |

A version string, API spec, operator statement or synthetic E2 fixture
must never be interpreted as installed support. Missing `api_usage`,
expired observations, incomplete host entitlement and unqualified critical
capabilities remain **unknown or blocked**, not silently supported. The
new API gating is engaged only for routes with reviewed `api_usage`;
do not claim full programme coverage until CT-API-03/05/07 are closed.

## A01–A16 acceptance coverage (CT-N13)

The precise scenarios are defined in
[the implementation plan](docs/implementation/capability-runtime-assurance.md).
A checked engineering implementation is **not** a passed scenario. Retain
source SHA, original positive/negative results, environment, signed reviewer
and receiving decision before closing a row. All scenarios are presently
**acceptance OPEN**.

| Case | Required failure/positive control | Outstanding acceptance evidence |
| --- | --- | --- |
| A01 | Missing, tampered or foreign evidence cannot qualify | Run signed-source evidence tamper/tenant denial against enrolled observers; E3 pending |
| A02 | Failed independent adapter case overrides declaration | Native negative conformance observation, suspension and plan/effect denial; E3 pending |
| A03 | Drift in adapter bytes, installed tuple or backend/topology forces requalification | Original observation and changed native tuple retest, compare shadow decisions; E3 pending |
| A04 | Concurrent physical vector reservations do not oversubscribe | Real CPU/memory/storage/address owner conflicts across tenants, durable exclusivity; E3 pending |
| A05 | Aggregate headroom with no feasible placement must hold | Prove current allocation topology readback and specific reject reason; E3 pending |
| A06 | Required flow blocked or forbidden flow reachable must fail | Native ingress/egress/return path, address-family and VRF/VPC negatives; E3 pending |
| A07 | Anti-affinity must span real required fault boundary | Read physical placement/fault domain instead of labels; E3 pending |
| A08 | Typed 60/120 versus 180 RPO and unit checks | Exact-source type/unit contract CI plus native observed measurements; E3 pending |
| A09 | RTO/consistency/key/application dependency failure revokes recovery claim | Representative native timed restore, original fault-trigger measurement and review; E3 pending |
| A10 | Approval-to-effect expiry or revocation must halt effect | Cross-service signed revocation during live Lifecycle preflight/effect, prove no write; E2 composed + E3 pending |
| A11 | Delayed/duplicate/reordered hint, stale cache or unavailable owner must fail closed | Complete TLS producer/receiver replay, restart and stale-cache campaign; E2 composed + E3 pending |
| A12 | Omitted mandatory validator/handler cannot skip qualification | Run contract/composition denial checks on exact source and receiving sign-off; E2 + E4 pending |
| A13 | Owner succeeded but reply lost must reconcile, never double-effect | Real owner retry/readback, exactly fenced request identity, no speculative compensation; E3 pending |
| A14 | Old plan replay after definition/workflow upgrade must pin or hold | Source-versioned replay matrix, compatibility denial and no silent reinterpretation; E2 + E3 pending |
| A15 | Registered method without adapter/qualification is visible but not executable | Generator/registry checks, unsupported native-path refusal and reviewed new method; E2 + E3 pending |
| A16 | Passing E2 must not self-upgrade to E3/E4 | Independent native reviewer and operating receiver recorded; no implicit promotion; E3 + E4 pending |

## Execution sequence and handoff rules

1. **Repair and verify P0 correctness first:** CT-N01–N03, including real
   PostgreSQL roles/migrations and both languages' format/type suites. CI
   runs must bind the source SHA of the actual commit being reviewed.
2. **Prove composed invalidation:** CT-N04/N05 and cross-boundary CT-N06,
   then CT-N07 contract parity. Durable receive acknowledgment is the
   only delivery success; no response or ambiguous reply stays pending.
3. **Complete provider-backed native work:** CT-N08–N10. Never use
   synthetically generated receipts as capacity exclusivity or native proof.
4. **Accept or explicitly deny promotion:** CT-N11–N13 with actual owners
   and independent reviewers. E2 green never implies E3/E4 release.

### Status and evidence conventions

- **Implemented, unverified**: committed code exists but source-bound
  passing tests are missing. **PARTIAL**: some paths exist, gates remain.
  **OPEN/NOT RUN**: required integrated/native work not performed.
  **BLOCKED**: an external prerequisite or queued CI prevents proof.
  Mark **DONE** only with exact source SHA, command/workflow run URL,
  negative/recovery results, owner and reviewer where applicable.
- Update this file first for the next handoff; add durable observations to
  [the assurance delivery ledger](docs/implementation/capability-runtime-assurance-ledger.md)
  and commissioning directions to
  [the invalidation runbook](docs/operations/runbooks/qualification-invalidation.md).
  The P05 workflow, Assurance PostgreSQL workflow and native qualification
  evidence remain separate gates.
- Distinguish **code committed**, **CI passed**, **E3 accepted** and
  **E4 commissioned** in both the PR body and the tracker. Do not
  auto-enable the scheduled relay, assert native support, close the delivery
  ledger or merge PR #64 before all mandatory gates are complete.

---

## Implementation checkpoint — current PR #64

Engineering changes made in this continuation (GitHub commits, **not** a green
workflow or external native/receiving acceptance):

- `0de8e22b`, `4981e2b3`, `e8bd963e`: established this authoritative
  13-item queue; archived previous handoffs without losing historical content.
- `918a269e`: authenticated Planning ASGI receiver backed by a real
  PostgreSQL fixture; tests commit-before-HTTP-ack, lost-response replay,
  conflicting event ID, and cross-tenant hold isolation.
- `824bc476`, `66810472`, `aebac503`, `6ff4ee05`: independent canonical
  scope SHA-256 goldens shared between Python and PHP (including Unicode and
  slashes); add both language suites to their existing E2 verification lanes.
- `ac2cb9cb`, `7a17079c`: Assurance HTTPS publisher rejects incomplete,
  unexpected, mismatched state/operation and malformed tenant/scope wire bytes
  *before* any request; adapt positive and negative Pest fixtures.

**Current CI evidence:** the latest inspected engineering head
`d279e408a48c05cf3cd4796346478dc2fabfb093` (PR #64, 135 commits)
had 40 queued check runs, with **no passing confirmations**. Two P01
workflow runs for that same head failed almost immediately and returned no
job records; root cause is **unknown**, not declared a code/test failure.
See https://github.com/awalker0878/multi-tenant/actions/runs/37852674326
and https://github.com/awalker0878/multi-tenant/actions/runs/37852674490.
CT-N01, CT-N02, CT-N03, CT-N04 and CT-N07 remain OPEN. The Planning ASGI/PostgreSQL test is
not a commissioned HTTPS Assurance-to-Planning service campaign. Independent
E3/E4 proof and provider-backed capacity remain outstanding.

### Continued source changes — E2 engineering only

- `7d67a629`, `5e95d9cc`: enforce exact five-field durable inbox
  acknowledgment, bounded HTTP body, exact approved sink path and epoch range;
  malformed/surplus HTTP replies are negative Pest scenarios.
- `6d0e2be7`, `1a17b453`, `318420d6`, `81c82498`,
  `0778bad3`, `468c60c4`, `d279e408`: read-only shadow comparison
  tool plus seven unit test scenarios and a GitHub Actions E2 job. Diff
  coverage includes runtime evidence, adapter bytes, installed tuple,
  definition, method, status/epoch and expiry. Comparator exit zero means
  only that supplied snapshots match; it confers no reviewer approval.
  Runbook: [qualification-shadow-reconciliation.md](docs/operations/runbooks/qualification-shadow-reconciliation.md).
- `1268adfc`: Lifecycle E2 regression exercises revocation between
  preflight and effect, and provider fencing lost after grant redemption.
  Neither grants a native write nor establishes an E3 owner proof.
- `9a1bd65e`, `888a8914`, `d1c7dc0e`, `dedd6b8f`: provider-used
  physical capacity, outstanding debits and class-specific physical limits
  are revalidated on reservation readback; tenant authorization withdrawal
  and quota drift are negative SQL tests. **No provider-native exclusive
  capacity owner has been commissioned.**

### Traceability for current E2 test candidates

| Case | Committed E2 test locations | Acceptance status |
| --- | --- | --- |
| A01–A03 | `tests/contracts/test_native_qualification.py`; `services/inventory/tests/test_capability_observations.py`; `services/assurance/tests/Feature/QualificationAuthorityLedgerTest.php` | Native signed observer/reviewer proof and exact-head CI open |
| A04–A05 | `services/lifecycle/tests/test_placement_reservations.py`; `services/planning/tests/test_placement.py` | Operated physical capacity exclusivity open |
| A06–A07 | `services/planning/tests/test_network_evidence.py`; placement/negative-isolation E2 fixtures | Native topology and security proof open |
| A08–A09 | `services/planning/tests/test_recovery_evidence.py`; typed matching E2 tests | Native measured RTO/RPO and restoration open |
| A10–A11 | `services/assurance/tests/Feature/QualificationAuthorityLedgerTest.php`; `services/planning/tests/test_qualification_invalidations.py`; `services/planning/tests/test_qualification_invalidation_http.py`; `services/lifecycle/tests/test_native_workflow.py` | HTTPS composed outage/reorder + native effect interception open |
| A12–A14 | Lifecycle validation/reconciliation/owner loss fixtures; `services/lifecycle/tests/test_native_workflow.py` | Versioned replay and owner proof open |
| A15–A16 | Versioned capability registry projections; `services/assurance/tests/Feature/QualificationScopeDigestTest.php`; `services/planning/tests/test_qualification_scope_digests.py` | Unsupported native method and independent E3/E4 gates open |

Nothing in this table asserts that all scenarios passed on the latest source.
For **each** scenario, retain exact-head CI, independently authorized native
negative/recovery observations and operating sign-off where required.

## Retained historical handoffs

The previous 38 KB of P0/P01–P10 handoffs, other branch baselines and
related receiving obligations is preserved, without rewriting its content, in
[archived-next-work-handoffs.md](docs/implementation/archived-next-work-handoffs.md).
Those descriptions are not current PR #64 statuses. Return to this file for
the active tracked blockers and next steps.


### Contract working-tree reduction — 2026-10-11

**Implemented, CI unverified:** Removed 40 superseded canonical releases (26 OpenAPI, 14 JSON Schema), 20 superseded installed consumer snapshots, and five obsolete P05/P08 historical-only generator/checker scripts. Tracked file reduction: 65 files, approximately 3.15 MiB of current-tree blob contents. The explicit approved list lives in `architecture/retired-contract-releases.json`; P01 history-gate conformance now exempts only these retired paths and rejects any retired path still registered as active. Contract integrity now rejects every duplicate retained JSON Schema `$id` with no historical SHA exception. P05/P08/P09 current qualification scripts and Planning P05 live campaign now read supported current releases. P07/P10 native grant-negative checks are retained until an equivalent current replacement exists.

**Validation outstanding:** Exact-head CI jobs remain queued. After checks run, resolve genuine failures without restoring retired versions. Do not promote any native capability above E2 or authorize writes based on this cleanup. Preserve PR #64 draft until verified.
