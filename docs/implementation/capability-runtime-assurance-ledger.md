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
| CT-02b | Signed native observation and persistent suspension | Partial | E2 paths exist; durable Assurance decision history and authority epoch still required |
| CT-03 | Placement, reservation and owner enforcement | Partial; current-capacity admission fix in PR #64 | Fresh-pool regressions added; native exclusivity, cross-owner enforcement and E3 still open |
| CT-04 | Directed network, isolation and failure domains | Partial | Address family, VRF/VPC, return paths, RBAC, storage/key and fault hierarchy coverage open |
| CT-05 | Representative measured recovery | Partial; failure-trigger RTO and readiness evidence added in PR #64 | Reviewed bounds binding is E2; independently authenticated native reviewer and E3 campaign still open |
| CT-06 | Integration and rollout controls | Partial | Source-bound A01–A16, shadow reconciliation and E4 receiving sign-off not complete |

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
| A10–A11 | Runtime and admission revocation tests partial | Durable authority epoch open |
| A12 | Missing validators fail closed in tests | Receiving E4 open |
| A13–A14 | Owner retry/loss cases partial | E3 multi-owner compensation open |
| A15–A16 | Unsupported methods fail closed; E2/E3/E4 separate | E3 and E4 open |

Never mark CT-06 or an E3/E4 scenario accepted solely on a unit-test or CI
success. Attach native owner custody, signed reviewer decisions, real provider
exclusivity and receiving-owner sign-off before changing authoritative rollout.
