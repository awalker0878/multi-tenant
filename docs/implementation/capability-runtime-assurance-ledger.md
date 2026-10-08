# Capability runtime assurance delivery ledger

Source baseline: 51f4a2afe650456a5afa31ce21f376116862238e.
Branch: codex/capability-runtime-assurance.
The implementation plan is [capability-runtime-assurance.md](capability-runtime-assurance.md).

Qualification remains owned by Assurance. Implementation and synthetic verification
do not establish E3 native qualification or E4 receiving acceptance.

| Increment | Scope | Implementation state | Acceptance / evidence state |
| --- | --- | --- | --- |
| CT-00a | Required immutable validation composition | Delivered in PR #63 | Audited main CI not green; new branch validation pending |
| CT-00b / CT-02a | Verified provenance and effect-boundary revalidation | Delivered in PR #63 | E2 RSA controls present; native E3 not supplied |
| CT-01 | Canonical registry and generated consumers | Delivered in PR #63 | Projection checks exist; full required CI not green |
| CT-02b | Signed native observation and persistent suspension | SQL authority epoch/history, signed publication boundary and outbox producer implemented in draft PR #64 | New PostgreSQL/HTTPS E2 checks pending; downstream receiver, live event replay and native E3 open |
| CT-03 | Placement, reservation and owner enforcement | Partial; current-capacity admission fix in PR #64 | Fresh-pool regressions added; native exclusivity, cross-owner enforcement and E3 still open |
| CT-04 | Directed network, isolation and failure domains | Expanded code/tests for address family, VRF/VPC, return paths, RBAC, storage/key and fault hierarchy in draft PR #64 | Current-head CI and source-bound native E3 control breadth open |
| CT-05 | Representative measured recovery | Failure-trigger RTO, application/key/dependency readiness and policy-review digest implemented in draft PR #64 | Reviewed bounds are E2; independently authenticated native reviewer and representative E3 restore still open |
| CT-06 | Integration and rollout controls | Core E2 integration with new outbox relay/command in draft PR #64 | A01–A16 final evidence, commissioned receiver, shadow reconciliation and E4 sign-off not complete |

## Acceptance scenarios

Track A01-A16 from the plan against executable tests and source-bound observations.
Failures, unavailable checks and native prerequisites remain explicit; a record marked
implemented does not mean its native qualification campaign passed.

## Native commissioning prerequisites

The selected platform tuple, native observer credentials, resource owner endpoints,
independent qualification reviewers and representative recovery data must come from
commissioned owner custody. Do not substitute synthetic records for these inputs.

## Commit discipline

Each code commit includes its focused tests or generator checks and updates this
ledger with the implemented boundary and observed results. Publish through the
GitHub connector using the preceding branch head as a lease. Keep the pull request
draft while mandatory checks or integration work remain incomplete.


## CT-00a observations

Planning now requires a frozen validation composition at construction. Migration
creation, current-plan review and unattended execution use the same required
support authority. Native and migration plan services reject a different
composition. Facts-only consumers use an explicit unavailable authority.
A12 covers omitted validators, attempted hook rewiring, composition mismatch and
support revocation before an unattended recipe read.

Local qualification does not include PostgreSQL: this workspace has no PostgreSQL
binary and cannot change process user IDs. The GitHub PostgreSQL/TLS jobs remain
required. Initial documentation-only CI also reports pre-existing failures:
retained evaluation.log is absent, release-set policy fails and the Governance
broker is not ready. These failures are not waived by this implementation.

## CT-01 observations

The versioned definition registry owns platform/action/strategy/method vocabularies,
legacy aliases, method stage orders, base safety cases and requirement comparisons.
Seven generated projections stay private to their contexts. CI checks projection
bytes and method implementation/conformance coverage. Existing frozen v1 transport
schemas are retained; later assurance contracts pin the definition digest.

Maximum RPO/RTO fields accept a 60-second bound for a 120-second target and reject
180 seconds, invalid numbers and wrong units. Unscoped legacy lists must meet the
objective in every profile; no fastest-sample selection is allowed. Unknown
requirement definitions remain unknown. The registry is metadata, never a native
qualification decision.

## CT-02a observations

Assurance v2 resolves signed observer evidence and independently signed reviewer
decisions against separately enrolled, scope-bound RSA keys. It verifies content
hashes, exact record/scope/artifact/definition binding, referenced evidence, required
case coverage and a separately refreshed runtime record. Observer and reviewer
identities and key material must differ. Legacy unsigned records remain unknown.
A stale, failed, changed or missing runtime record cannot publish positive support.

Planning verifies the resolver's record digest and definition version. Runtime
validity bounds plan freshness. A required service-only qualification read also
runs on unattended native plan reads, which Lifecycle repeats at effect boundaries.
No cached user delegation is borrowed. Isolated E2 live-test peers now sign fixture
records with scope-bound fixture keys; this exercises the protocol without granting
E3 support to any actual platform. The original E2 simulation custody API is unchanged.

## CT-02b observations

The worker now has a bounded read-only observer poll with protected manifests,
independent native principals, mounted artifact hashing, measured case bindings,
RSA signatures and atomic publication. A failed poll suspends its reviewed decision
persistently; later successful polls cannot clear that suspension. Only a separately
reviewed decision creates a new publication key. Inventory verifies signatures,
enrolled scope, tuple, generation and original measurement freshness before its v2
projection, while retaining discovery and ownership holds. Legacy migration records
are no longer positive support: signed reviewed evidence must bind the complete
route support response digest. E4 still requires separate receiving acceptance.

Focused E2 tests exercise signature rejection, expiry, tuple drift, sticky failure,
artifact drift and preservation of Inventory holds. A dedicated GitHub matrix runs
format, lint, strict types and product tests; local execution became unavailable
before this increment, so its verification results are recorded from CI.

## CT-03a observations

Planning now requires the v2 Inventory projection to bind the current Assurance
runtime signature, decision, exact scope and definition before positive placement.
Placement fits each workload against physical pool vectors, existing usage and
pending reservations, storage/network classes, architecture, zone policy and actual
failure-domain labels. CPU overcommit requires explicit dated approval; memory and
storage retain physical bounds. Bounded search returns unknown on exhaustion.
The immutable inventory digest excludes runtime fetch timestamps but retains the
complete measured snapshot and authority bindings. Assessment remains unreserved.
Focused E2 tests cover fragmentation, pending debits, fault-domain collision and
missing/foreign/stale native snapshots. Authoritative admission follows separately.

## CT-04 observations

Eligibility now evaluates native directed routes, firewall rules and default-deny
policy against fresh measured required and forbidden flows. Measurements bind the
exact topology and policy digests; a required flow without a route or firewall rule
cannot pass from its own declaration. Isolation requires native project/tenant
identity, distinct observer/writer principals, distinct domain instances and measured
negative controls covering each security domain and the tenant boundary. Concrete
placement verifies failure-domain separation. Missing measurements remain unknown;
failed controls block. E2 tests cover route removal, forbidden traffic leakage,
domain aliasing and observer/writer reuse.

## CT-05 observations

Recovery eligibility now uses the latest observed attempt for each dataset, bound
to method, consistency, generation, native scope, backend, profile, policy and
artifacts. Representative byte volume, accepted load and restore concurrency are
required. RPO is failure time minus the last consistent checkpoint; RTO is application
readiness minus restore start. Units and timestamp order are checked explicitly.
A later failed or slower restore overrides earlier successful samples and holds
the next assessment. The observer's failed-case suspension additionally requires
new independent review before positive publication. E2 tests cover latest failure,
RPO/RTO violations, byte/second confusion, undersized restores and insufficient load.

## CT-03b observations

Lifecycle now owns a production SQL vector ledger and service-only reservation,
readback, confirmation, renewal and release routes. Transactions serialize globally
by physical pool authority across tenants; identities bind provider and native host.
The independently observed provider lease, current usage and exact protected request
approval must be available. Confirmed provider usage is counted once only after
readback identifies the reservation token. Unknown and expired allocations retain
their debits. Release requires fresh absence and unused-resource evidence.

Unattended Planning validation resolves the retained assessment reference, re-reads
Assurance and a separately granted Inventory capability generation, evaluates current
network/isolation/recovery findings and requires a matching live vector receipt from
the commissioned capacity owner. The receipt binds plan digest, allocation witness,
generation and policy. No browser delegation or simulation receipt can satisfy it.
Real PostgreSQL tests cover competing tenants, exact retry after restart, conflicting
requests, expiry with live allocation and confirmed consumption without double debit.

## CT-06 integration observations

The Console action and strategy choices and direction counts now come from the
canonical generated metadata. A separate read-only placement proposal endpoint
exposes the deterministic allocation witness for capacity-owner review without
changing existing v1 plan bytes or granting effects. The E2 live Inventory peer now
returns signed, scope-bound native-protocol snapshots, while actual uncommissioned
Inventory still returns unknown. Composed unattended-read tests cover missing or
released receipts, allocation tampering, network drift, failed restore and legacy
qualification. The v2 source contract documents the new Inventory and service-only
qualification reads. The four-product CI matrix records independent format, lint,
type and test outcomes and cancels obsolete runs of that matrix.

## Receiving acceptance and resource refinement

An E4 record now requires a separately enrolled receiver with distinct identity and
key material, an unrevoked signed acceptance, and exact qualification/record/scope/
definition bindings. Missing or substituted acceptance cannot establish E4. Review
and acceptance digests remain pinned during unattended reads, so a new review does
not silently upgrade an old plan. Synthetic RSA controls exercise this protocol as
E2 only. No receiving environment is commissioned by these tests.

Placement vectors include storage-class and network/address-family sublimits,
preventing aggregate storage or address headroom from hiding exhausted classes.
The runtime observer suspends a decision when the latest restore outcome failed.

## October 8, 2026 audit and remediation branch

Audited `main` revision: `88f77d5b4dd5e4da8ae3e96be09ab8779b9c4843`
(merged PR #63). The audit found required CI failing (31 checks passed, 22 failed,
6 still running at its snapshot). **Merged is not equivalent to qualified.**
The follow-up is draft PR #64 on
`codex/capability-runtime-assurance-audit-fixes`. Evidence below describes
code changes, not completed native commissioning or validated full CI.

- **Inventory test collection:** repaired the incomplete signed observer trust
  fixture and unmatched parenthesis, restoring syntactically valid test source.
- **Current capacity admission (A04/A05/A10/A13):** every mandatory current
  capacity finding must be eligible; the original witness is compared against
  a newly solved placement on fresh observed pools. Exact allocations and
  ledger revisions must agree before a current owner receipt can admit the
  plan. Regressions cover headroom shrinking with an unchanged pool identity,
  exhausted class sublimits, ledger revision drift, summary capacity loss and
  stale owner receipts.
- **Measured RTO (A09):** the authoritative clock runs from failure to
  verified application readiness, never from restore initiation. Evidence
  must include key availability, native application probe and required
  dependent-service readiness; absent proof is unknown, observed failure is
  blocked. Reviewed recovery limits are bound to the protected policy
  by a digest and distinct reviewer/observer identities in E2 fixtures.
  These fields alone are **not cryptographic native reviewer attestation**.
  E3 requires a separately authenticated decision authority.
- **CI repair:** applied reported formatting adjustments in Planning,
  Inventory and Lifecycle; narrowed HTTP ASGI scopes for strict typing
  and asserted non-null SQL test rows. A complete current-head CI matrix
  and comparison with unrelated baseline failures are still required.

### Source-bound acceptance register

| Scenarios | Engineering tests | Native E3 / operating E4 |
| --- | --- | --- |
| A01–A03 | Synthetic RSA and contradiction tests present | E3 open |
| A04–A05 | SQL races plus new fresh-capacity admission regressions | E3 exclusive owner still open |
| A06–A07 | Directed flow and negative isolation checks partial | E3 native control breadth open |
| A08 | Typed numeric matching tests present | E3 open |
| A09 | Failure-trigger RTO and complete readiness tests added | E3 actual representative restore open |
| A10–A11 | Authority epoch/history and fail-closed producer relay now coded; new E2 SQL/transport tests pending | Commissioned receiver, out-of-order inbox reconciliation and E3 open |
| A12 | Missing validators fail closed in tests | Receiving E4 open |
| A13–A14 | Owner retry/loss cases partial | E3 multi-owner compensation open |
| A15–A16 | Unsupported methods fail closed; E2/E3/E4 separate | E3 and E4 open |

Never mark CT-06 or an E3/E4 scenario accepted solely on a unit-test or CI
success. Attach native owner custody, signed reviewer decisions, real provider
exclusivity and receiving-owner sign-off before changing authoritative rollout.

## October 8, 2026 continued implementation — direct draft-branch commits

The following commits target `codex/capability-runtime-assurance-audit-fixes`
directly; they are **not a native qualification, E3 decision, E4 receipt or a
completed CI claim**.

- `50bb4d6a`: correct three invalid PL/pgSQL trigger-body delimiters in
  `002_qualification_authority.sql` so migrations can be executed by PostgreSQL.
- `045eaec1`: E2-only SQL transaction tests for exact idempotent publication,
  monotonic epochs, append-only event and outbox history, sticky suspension,
  independent restoration and stale-epoch rejection.
- `0d519df3`: dedicated GitHub Actions PostgreSQL lane provisions isolated
  runtime/migrator roles, installs SQL migrations and runs the feature tests.
- `c8b07bd4` through `8d2d16c1`: explicit durable-ack publisher contract,
  scope-ordered `SKIP LOCKED` relay, HTTPS/TLS sink with exact persisted
  acknowledgment, configuration and registered bounded Artisan command.
- `5a2121e8` onward: E2 test coverage for failed publication, retry, ordering,
  wrong acknowledgment and transport fail-closed behavior; corrected a URL-userinfo
  guard and fixture warnings.
- See [invalidation commissioning runbook](../operations/runbooks/qualification-invalidation.md)
  for the required receiving inbox, duplicate/out-of-order handling and operational
  restrictions.

**Verification is outstanding.** At last inspection, GitHub Actions for the
current branch were queued with no current-head results. A passing workflow must
establish source SHA and tested jobs; until then this ledger records code present,
not tests passed. The new relay is intentionally not scheduled and cannot clear an
invalidation without a commissioned, explicitly configured receiving endpoint
returning the exact durable inbox receipt. No downstream consumer or E3 native
reviewer has been commissioned by these changes.

Follow-up acceptance: run the isolated PostgreSQL job, inspect any PHP
format/strict-type failures, confirm that a failed/missing/late HTTP receipt keeps
SQL outbox rows pending, commission the implemented Planning receiving inbox
under distinct credentials and verified TLS, then run end-to-end A01–A16 tests
including scope isolation, reordered events, effect-boundary revocations and
E3/E4 shadow-rollout acceptance separately.

### A10/A11 follow-on — Planning receiving inbox (direct branch commits)

- `c0174fc6`: bind the immutable Assurance outbox event to its originating
  tenant; `7958bc54` cross-checks the outbox payload against the stored
  authority-history tenant before delivery.
- `a2540f5c`: Planning-owned `003_qualification_invalidations.sql` provides a
  tenant-scoped, append-only inbox and monotonically advancing per-scope heads.
- `14c16164` and `04515ce3`: durable receive/ack application boundary and
  authenticated, bounded internal HTTP transport; `35bcaf6c` wires the new
  endpoint into Planning's router.
- `40bce52c` and `9aec2823`: E2 PostgreSQL and HTTP denial/replay tests.
  These require CI to report a current-source pass before being counted as passed.
- `fe958a89`, `27d308aa`, `b4db098d`: independent plan-to-qualification-scope
  index, exact-scope invalidations and conservative holds when source scope is
  unknown. Immutable plan content is unchanged; known unrelated scopes remain
  unaffected.
- `085755c5` and `c79770e2`: serialize plan creation against a
  qualification-scope invalidation and add a late-revocation regression.
- `4fc4fadd`: operator protocol updated with the Planning receiver configuration
  and still-uncommissioned HTTPS/credential custody gate.

**Outstanding:** CI was queued at the last current-head inspection and tests
have not been verified green. A receiving endpoint is now present in source but
has not been commissioned, TLS/secret custody has not been enrolled and no
live end-to-end campaign or independent E3 native review has passed. Existing
effect-boundary direct source revalidation remains mandatory.


### Follow-on audit repair — SQL integrity and negative-admission read paths

A fresh direct audit of PR #64 found an invalid `003_qualification_invalidations.sql`
file: a previous splice had cut the scope SHA check midway and duplicated its
trigger, grants and transaction end. Commit `6eb16a1b` replaces the file with
one complete transaction, separate scope index, append-only inbox and proper
owner/runtime grants. No prior migration success is claimed. The disposable
Planning PostgreSQL test fixture now executes migrations 002 and 003.

Commits `89717fc5` and `88c16f8d` strengthen Assurance's deferred SQL
constraint: an epoch update must agree with its stored tenant, signed-decision
metadata, immutable predecessor, result projection and outbox payload. This is
in addition to application-side checking; it does not make an unsigned SQL
event E3 proof. Commit `23c04467` adds SQL negative tests for an unjournaled
head advance and runtime mutation of outbox wire bytes.

Commit `ad864083` introduces `Planning.qualification_hold` and requires the
persisted scope index/current negative head/append-only invalidations to be
checked before approval bindings, execution plans and placement proposals can
be released. Absence of a pinned scope now denies admission, even if no
invalidation event has yet been seen. Commits `4974e530`, `62d0cc24`,
and `ce5142e1` add unknown-scope, withdrawn-source, and concurrent
plan-save/revocation PostgreSQL tests. Commits `9dcb31b1`, `4da3bd36`
and `695e41b1` bind the approval read to the persisted database tenant
rather than trusting tenant information inside a plan payload.

**All changes above are engineering implementations, not acceptance
measurements.** GitHub's current-head checks were still queued as inspected;
there is no proven CI pass, integrated TLS receiver, E3 native reviewer, E4
receiving acceptance, or production rollout. The next gate is to execute and
repair the real PostgreSQL/PHP/Python jobs, followed by source-bound
A01–A16 composition and explicitly authorized native campaigns.

## PR #64 follow-on — exact receipt, read-only shadow and provider readback

This increment remains **E2 implemented, not E2 verified or E3/E4 accepted**:

- Assurance's external relay now requires a response within 8 KiB with
  exactly five acknowledgment fields, not a copied outbound event. The
  configured HTTPS URL must use the approved private receiving path.
  Test: `services/assurance/tests/Feature/QualificationInvalidationPublisherTest.php`.
- The read-only `scripts/assurance/shadow_compare.py` produces source
  revisions, SHA-256 manifest bindings and per-scope changes without
  granting authority, even when no diff exists. Negative and drift tests
  are at `scripts/assurance/test_shadow_compare.py`; a new separate
  E2 GitHub job runs the stdlib suite. A native signed comparison, owner
  reviews, and an approved promotion decision remain unperformed.
- Lifecycle rechecks fresh provider-used physical capacity, the sum of
  all live reservation debits and native class-specific limits on
  reservation receipt readback, not only at initial allocation. Its
  SQL tests cover provider drift, tenant withdrawal and omitted class
  limits. Only actual operated providers can establish exclusivity.
- E2 Lifecycle tests prove a plan/approval withdrawal after preflight and
  loss of provider fencing between redemption and effect lead to denial;
  no live signed cross-service campaign is claimed.

At inspection of source `d279e408a48c05cf3cd4796346478dc2fabfb093`,
40 checks were queued. Two P01 runs reported failure without job records.
Do not invent failure logs or claim green. The **authoritative remaining
work and per-scenario traceability** is `next_work.md` (CT-N01–CT-N13).

## CT-N14 — API-version-aware migration capability admission (E2 only)

Implementation addition to draft PR #64:
- `planning/domain/api_compatibility.py` selects only fresh
  environment- and API-release-scoped, entitlement-authorized native
  `live_probe` evidence carrying independent E3/E4 Assurance review.
  A route may use VMware VI/JSON 8.x and target OpenStack 2.x or AHV v4.3
  simultaneously; there is no cross-product version equality check.
  Outdated/unsupported individual versions are not inherited by another
  release, and only the separately qualified release is selected.
- Approved route `api_usage` is bound in `planning/domain/expansion.py`
  and evaluated at `MigrationSupport.read` and `require`. Critical
  disk, boot, storage/data, security/isolation, required network and
  recovery feature categories cannot be relabelled optional.
- Assurance `MigrationQualificationController` only returns the
  API evidence when an independently resolved `migration.api_records`
  capability covers the exact scope, tranche, release and API bytes.
  E4 is additionally required for omission claims. Planning consumes
  the new bounded closed `api_evidence` response from that authenticated
  service boundary; no browser-provided observation is accepted.
- Console's MigrationSupport page reports per-route API warnings and
  selected native API release, including a warning on historical routes
  that have not been enrolled for feature-level evaluation.
- Disk export/import source code tags cover all three platform families;
  `scripts/assurance/test_migration_api_usage.py` verifies AST tags.
  `services/planning/tests/test_api_compatibility.py` covers mixed
  API generations, stale discovery, missing mandatory disks, untrusted
  documentation evidence, optional E4 impact acknowledgements, and
  route admission rechecks. This test evidence remains **unverified**
  until exact-head CI runs actually complete.
- `contracts/schemas/capabilities/api-version-record-v1.json` provides
  a documentation record model, not an automatically populated catalogue.

**Outstanding:** full call-site mapping and route rollout, commissioned
version discovery and live probes, independently enrolled E3/E4 evidence,
actual no-op/skip receipts for optional capabilities, required API
version pinning into effect grants, adapter equivalence and native
recovery tests. See CT-N14 / CT-API-01–09 in `next_work.md`. None of
these external gates can be closed by synthetic fixtures.

## CT-N15 — Version-controlled VM collection attribute catalogue

Committed `contracts/capabilities/migration-collection-manifest-v1.json`
with 278 source/destination/owner attribute entries across VMware (86),
AHV (89) and OpenStack (103). Every entry defines stable ID, native API
field or explicit owner attestation, collector module, collection method,
maximum age, conditional applicability and mandatory/optional criticality.
A strict JSON Schema and stdlib static/source-field assurance test are
version controlled; E2 CI was extended to run it. The manifest has
non-affirmative `native_field_candidate`/`external_evidence_required`
statuses, so documentation cannot be mistaken for E3 support.
Published policy and freshness semantics:
`docs/implementation/migration-collection-manifest.md`.

**Code-level manifest checks and GitHub commit do not constitute native
data collection, freshness enforcement, an operator alert or E3/E4
acceptance.** Real per-environment collection, append-only evidence, owner
review, conditional applicability, native-effect admission and independent
tests are outstanding as CT-N15 / CT-API-10.

## CT-N16 — VMware / AHV / OpenStack field-by-field semantic mapping

Committed:
- `contracts/capabilities/migration-field-crosswalk-v1.json` — **116**
  canonical field groups linking every one of the **278** manifest inputs
  to corresponding VMware/AHV/OpenStack API or owner fields, source/target
  scope, freshness, severity, conditional applicability and an explicit
  `not_qualified` sentinel. Gaps become null/unknown.
- `contracts/schemas/capabilities/migration-field-crosswalk-v1.json`
  — closed schema; no affirmative native support status.
- `scripts/assurance/validate_migration_field_crosswalk.py` and
  `test_migration_field_crosswalk.py` — enforce lossless per-platform
  coverage, field provenance, criticality, scope, min-TTL, negative
  security/unknown and capacity/identity boundaries. Explicit E2 CI step
  added to `capability-assurance.yml`.
- `docs/implementation/migration-field-crosswalk.md` — full human
  comparison (61 source, 28 destination and 27 owner groups), including
  transformations and critical non-equivalences.

**Truth status:** Mapping requirements are version-controlled; installed
API support, live source field extraction, executable conversion, destination
adapter equivalence, automatic per-VM impact alerts and native effect
gates are **not** implemented/qualified by this mapping. See CT-N16
and CT-N15/CT-API-01–10 in `next_work.md`. GitHub hosted CI and
independent E3/E4 closure are still required.

## CT-N17 — Feature-level mapping, operator console requirements and evidence split

**E2 contracts/UI committed:** `migration-feature-policy-v1.json`
defines 30 typed feature categories and all nine directional candidate
plans, covering the 116 canonical crosswalk groups and 278 original
collection attributes. Feature severity is critical if any contributing
crosswalk group is critical, with conditional requirements evaluated
independently. 27 operator/independent input obligations link to exact
pre-existing per-VM review or operator-readiness Console fields. No
vendor API observation may be overwritten by operator input; E4
effect suppression is needed for an approved nonessential omission.

Read-only Console UI shows feature treatment and required
operator/independent references without claiming verification.
Inventory server review constraints were regression-tested for all
eight owner reference fields, datasets and objectives. A closed
schema, exact Console JSON mirror and E2 contract validators were
added to CI and browser coverage. Original source crosswalk,
field/owner age, criticality and nine-direction correspondence were
cross-checked programmatically without errors.

**Native truth still missing:** full server-side per-VM joined
readiness/conditionality, installed-version capability observations,
Assurance signed independent proof, accepted optional omissions
and Lifecycle per-effect admission. Current UI is advisory, not
native execution authority. Required work CT-N17 in `next_work.md`.
