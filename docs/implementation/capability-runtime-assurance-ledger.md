# Capability runtime assurance delivery ledger

Source baseline: 51f4a2afe650456a5afa31ce21f376116862238e.
Branch: codex/capability-runtime-assurance.
The implementation plan is [capability-runtime-assurance.md](capability-runtime-assurance.md).

Qualification remains owned by Assurance. Implementation and synthetic verification
do not establish E3 native qualification or E4 receiving acceptance.

| Increment | Scope | State | Verification |
| --- | --- | --- | --- |
| CT-00a | Required immutable validation composition | Implemented | Planning Ruff, format and strict mypy pass; 383 tests pass locally, 6 PostgreSQL tests await GitHub runner |
| CT-00b / CT-02a | Verified qualification provenance and current execution revalidation | Implemented | Real RSA positive and eight negative controls pass; Planning 403 tests pass locally, 6 PostgreSQL tests delegated to GitHub |
| CT-01 | Canonical definition registry, generated consumers and typed matching | Implemented | Generated projections agree; 30 stage combinations preserved; typed maximum/unit and handler tests pass; strict mypy passes in four products |
| CT-02b | Native observation projection and sticky runtime suspension | In progress | Pending |
| CT-03 | Concrete placement and authoritative reservation owner integration | Planned | Pending |
| CT-04 | Evidence-bound network, isolation and failure-domain evaluation | Planned | Pending |
| CT-05 | Measured recovery profiles and reassessment feedback | Planned | Pending |
| CT-06 | Composed acceptance tests, compatibility and rollout controls | Planned | Pending |

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
