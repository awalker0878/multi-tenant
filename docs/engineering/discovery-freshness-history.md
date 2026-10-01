# B22 — retained freshness checks and history

Reviewed 30 September 2026 (America/Toronto). This is a continuation of
[the existing Wave 2 plan](../product/enterprise-workload-mobility-execution-plan.md),
not a new backlog or authorization to begin Wave 3. It completes the deployment
and recovery contract for the committed history repository, migration 0023 and
HTTP integration. Periodic scheduling and alert delivery remain unfinished.

## Record and inspect one monitoring check

The existing authenticated control API now supports:

```text
PUT /v1/environments/{environment_id}/discovery/freshness/checks/{check_id}
Content-Type: application/json
Authorization: Bearer <current enterprise token>

{}

GET /v1/environments/{environment_id}/discovery/freshness/checks/{check_id}
GET /v1/environments/{environment_id}/discovery/freshness/checks?after=0&limit=20
```

The environment, check ID and credential above are placeholders. PUT accepts only
an empty JSON object, at most 1 KiB, and no query parameters. The client chooses
an exact check ID, not a report, actor, observation, timestamp or monitoring policy.
The server computes the report from the latest stored generation through the
existing [freshness projection](discovery-freshness.md). This does not collect new
native inventory. The original live GET remains read-only and does not append
history; its monitoring defaults and format are unchanged.

Reads require a current exact-scope HUMAN JOB_READER or EXECUTION_OPERATOR grant.
PUT requires EXECUTION_OPERATOR and the existing independent evidence mutation
gate. The authenticated subject supplies the recorded actor. Same-subject identity,
current roles and environment selection are rechecked around database access,
after lock waits and before transaction commit. Evidence holds block append and
PUT replay but do not by themselves deny otherwise authorized historical GETs.
Site-worker logins cannot use this history as a new discovery or write authority.

## Immutable records, not refreshed historical truth

`provisioner/controlplane/discovery/freshness_history.py` owns capture, exact reads
and bounded pages. It uses the existing tenant-scoped PostgreSQL repository; there
is no second journal, native collector or in-memory production fallback. A new
check acquires the environment's cooperative transaction lock, computes metadata
freshness, and appends the check and audit event atomically. A failed audit insert
or revoked authority before commit rolls back both. New records use the database's
UTC clock and must not regress relative to the previous record/check time.

`hosting-discovery-freshness-check/1` retains environment and complete native scope,
check ID, consecutive sequence, report digest, authenticated author, recorded time,
previous-record digest, change kinds, record digest and the original nested
`hosting-discovery-freshness/1` report. Records always carry `historicalOnly: true`,
`notificationAttempted: false`, `collectionRequested: false` and
`executionAuthorized: false`. The stored report's FRESH status is its original
as-of calculation, not a health statement at the later GET time.

The first check records INITIAL_CHECK. Later records distinguish POLICY_CHANGED,
OBSERVATION_CHANGED, FRESHNESS_CHANGED and COLLECTION_HEALTH_CHANGED in that order.
An unchanged report still creates a new audited check when a new ID is explicitly
requested, with an empty change list. Age comes from the original inventory capture,
not the monitoring record's creation or replay. Missing/future/stale inventory,
reported partial collection and unverified native visibility remain distinct.
No raw provider error strings, privileges, tokens or inventory objects are returned.

## Same-ID retry and uncertain acknowledgements

A committed same-ID retry by the same authenticated actor returns the exact original
record, without resampling, duplicate audit or changing its policy/time/generation.
The same ID used by another actor conflicts. The ID is scoped to organization,
tenant and environment, not a globally unique credential or an execution grant.

After a lost, malformed or inconsistent PUT acknowledgement, retain the original
environment/check ID and actor. Read that exact ID with current authorization.
A matching retained record is historical evidence; verify its recorded actor and
digests. Do not choose a new ID to disguise a retry as the original check. A missing
or inaccessible GET does not prove that the earlier PUT never committed. Even an
error response can follow a committed write. An explicit same-ID retry still needs
current write authority and evidence custody. When no original was committed,
that retry may create a sample at its later database time; it cannot recreate an
unrecorded earlier measurement. This slice adds no automatic retry or client-side
monitoring-history command. The existing CLI freshness command remains a live read.

## Bounded pages and cursor-boundary integrity

History GET returns `hosting-discovery-freshness-history/1` with exact scope,
original items, nextAfter, `consistency: APPEND_ONLY_PAGE` and the same false
authority/action flags. The default limit is 20; accepted limits are 1–50, and after
is a canonical nonnegative signed-64-bit sequence. Unknown, duplicated, negative,
nonintegral, leading-zero and overflowing query values are rejected. A cursor is
only a position: it grants no scope and is not an independent signature.

For a positive cursor, the repository includes that cursor's predecessor record,
the requested page and one lookahead in a single bounded SQL statement. At most
52 rows are loaded. The anchor validates continuity but is never returned as a new
item. Every loaded row must have valid canonical content and digests. Consecutive
rows must have the exact predecessor digest, nonregressing record/check timestamps
and change kinds recomputed from the two retained reports. Invalid lookahead
prevents partial success. A corrupt terminal anchor is checked even for an empty
page; a missing anchor with surviving successors is held rather than ignored.

Separate pages are not a frozen whole-history export: subsequent appends may appear
on later requests. Positions beyond all retained rows remain empty. This local
consistency check is not full-chain verification, independent audit custody, or a
whole-database rollback/deletion detector. A completely removed suffix or restored
consistent prefix needs the existing signed audit checkpoints and operational
reconciliation. Exact-ID GET validates that record's content, not all its ancestors.
The repository does not repair/rewrite damaged history or reinterpret old formats.

## Deployment and restore

Apply the packaged checksum-bound migrations through 0023 with the dedicated
migration owner before using the history routes. Do not edit prior SQL or its
migration ledger. The API runtime needs only SELECT and INSERT on
`hosting_controlplane.discovery_freshness_checks`, plus its existing discovery
SELECT, audit INSERT and schema privileges. It must not own the table or have
UPDATE, DELETE, TRUNCATE, trigger-changing or arbitrary SQL access. There is no
new discovery-ingest, site-worker or native-platform privilege. The API creates
history through its trusted service, not from caller-supplied rows.

Migration 0023 enforces the full immutable environment binding, per-environment
sequence and check-ID uniqueness, exact predecessor, append-only records, forced
tenant row-level security and site-worker exclusion. It creates no historical
samples or native qualification. Existing migration 0022 remains the separate
signed application-owner-review contract. See the
[migration deployment instructions](../../provisioner/controlplane/persistence/migrations/README.md)
for required role separation and grants.

Preserve the history table, audit chain/checkpoints, environment registrations,
original inventory and migration ledger together. The existing disposable dump/
restore gate includes the table and restores without runtime access until reviewed
reconciliation. Historical checks do not prove current inventory signatures,
complete native visibility or native writer exclusion after restore. API and
database clocks must remain consistent; a regressing clock holds new operations.

## Errors and verification

HTTP 200 means a validated live read or retained historical result, including
MISSING, STALE and partial observations; it is not a health pass. The API retains
401 authentication, 403 non-human, indistinguishable unknown/unauthorized 404,
409 DISCOVERY_FRESHNESS_CHANGED and DISCOVERY_FRESHNESS_CHECK_CONFLICT, 413 body
bound, and 422 request-shape/query errors. Evidence holds and unavailable or corrupt
metadata return 503 without raw database/credential details. No history DELETE,
PATCH or launch route exists. Every response is no-store.

Repository and HTTP regressions cover immutable same-actor retries, conflicting
actors, exact scope, evidence/identity loss, missing and corrupt rows, clock checks
and unchanged live GET behavior. Disposable PostgreSQL tests cover actual locks,
concurrent appends/retries, audit rollback, forced tenant isolation, denied worker/
update/delete/truncate operations, trigger guards and authenticated API round trips.
The pagination continuation adds 15 protocol tests and four real-database tests;
11 new protocol assertions reproduced the old behavior before correction.

Record exact final-revision CI and local skips in the delivery record. Protocol
fixtures are not PostgreSQL tests, and database tests are not installed vendor
qualification. No production guest, platform or dataset is contacted by this work.

## Remaining Wave 2 gate

On-demand retained checks and their history API are implemented. Periodic fleet
monitoring, authenticated service scheduling, alert delivery, globally coordinated
endpoint budgets, larger resumable publication and estate measurements remain open.
Independent inventory visibility, remaining native image/hardware/security facts,
verified external dependencies and guided authoring/adoption/owner acceptance also
remain unfinished. Move to the next wave only when the existing wave's gates are
complete; history, a successful read or a passing fixture cannot supply that closure.
