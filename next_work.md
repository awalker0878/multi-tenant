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
`contracts/schemas/capabilities/api-version-record-v1.json` provides
immutable vendor documentation metadata. Native disk source and target
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
