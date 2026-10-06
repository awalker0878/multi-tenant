# P06 — Durable simulation execution

The six P06 engineering packages implement isolated E2 simulation. Verification
is in progress; the delivery register retains the actual gate decision and
reviewers. The implementation contains no native effect adapter or operational
admission lane.

## Admission and exact authority

Lifecycle owns the PostgreSQL admission, tenant command fingerprint, immutable
plan/approval/campaign and reservation bindings, stable `p06/tenant/job` workflow
identity, dispatch outbox, resource/field holds and ordered operation journal.
One transaction records admission and dispatch intent. Repeated matching commands
recover the same logical job; changed payloads conflict. The independent campaign
registry supplies bounded simulation inputs, explicit endpoints/credentials/data,
cleanup owner, worker IDs, expiry and custody epoch. It cannot waive missing
isolation, ownership, state, freshness or reservation facts.

The API gets immutable content from Planning and current delegated actor authority
from Governance. Each privileged attempt and grant redemption fetches Planning
again and verifies current Governance approval, executor membership, independent
requester/reviewer authority, source revision, exact campaign, resource holds and
custody epoch. An unavailable dependency denies new effects. Execution uses the
approved actor's current authority independently of the original browser session;
subsequent Console requests always require a current session and delegation.

## Workflow, uncertainty and writer boundaries

The Python SDK is locked to Temporal 1.34.0. `SimulationJourneyV1` uses task queue
`p06-simulation-v1`; type and queue versioning retain V1 code for V1 histories.
Dispatcher uses reject-duplicate ID reuse and fail-on-conflict, then verifies the
existing workflow type and memo before acknowledging the outbox. An ambiguous
start retains the original identity. No replacement ID is generated.

Activities have one Temporal attempt, a 30-second start-to-close limit and a
2-minute schedule-to-close limit. They never infer external absence from timeout.
The workflow observes committed controls every 15 seconds while held; signals
only wake it and convey no authority. Worker restart recovers durable work.
Hold/stop controls persist; cancellation observes accepted work and keeps holds.

Every effect has a stable operation ID and a separately journaled attempt/grant.
Grants expire after 15 seconds and redeem once. The independently owned simulator
serializes acceptance against readback: an accepted attempt has one effect, and
an absent attempt is sealed against a delayed arrival. Lost acknowledgements
hold dependent writes. Only sealed absence can support an authorized unstarted
retry. The target-first-write boundary remains conservative even after a failed
attempt: forward recovery or a separately approved source-return decision is
required. Source fencing, target activation and retirement have independently
observed writer state; no command claims native undo or allocation release.

## Custody and jobs experience

Assurance accepts only bounded, allowlisted observation JSON (64 KiB), verifies
SHA-256, exact tenant/job/plan/source and the Lifecycle binding, and reads each
observation directly from the separate simulator before finalizing. Runtime roles
can insert/read custody records but cannot update/delete them. Retention is
recorded for 365 days; no runtime purge is implemented. Raw logs and credentials
are excluded by the observation schema. Current scoped delegation controls reads
and independent review. Reviews cannot turn simulation into native support.
Reads return the most recent 1,000 reviews in chronological order; older immutable
reviews remain in custody.

Custody for committed facts may finish after executor revocation. Missing or
invalid evidence prevents job completion. Review decisions and receipts remain
separate; fixture reviewers are not designated G06 receiving reviewers.

Console provides simulation admission, bounded current-state polling, a recent
300-event timeline, explicit uncertainty and target-write explanations, pause,
stop, cancel, reconciliation, and authorized recovery controls. Requests use
stable identities and expected revisions. A lost command reply offers receipt
recovery. Stale or revoked authority disables controls and clears protected
history. Evidence drilldown separately monitors current Assurance access.

## Recovery and boundaries of the evidence

An independently mounted custody epoch is outside Lifecycle backups. A restored
old epoch or quarantine denies effects; reading a database snapshot cannot mint
new authority. Restore tests preserve the separate simulator's accepted effects
and retain holds rather than replaying missing journal writes. P06 does not expose
an automatic epoch rebind, release, old-source restart or native recovery command.
Re-enable requires the incident procedure's independently reconciled version set
and newly bound authority; a successful restart alone is insufficient.

The complete campaign composes P05's real PostgreSQL, owner APIs, TLS broker and
browser path with the P06 services, a pinned Temporal server and separate SQL
schema identity, worker/engine restarts, actual process crashes, dependency faults,
independent effects, alerts, evidence and older-journal restore. Controlled
Inventory/qualification-shaped inputs and simulation effects remain E2. Verified
loopback TLS proxies and automated keyboard/reflow checks do not establish
operated ingress, a representative user's comprehension or assistive support.

Use the [simulation runbook](../operations/runbooks/durable-simulation.md) for
configuration, operator decisions and recovery. Native E3, operating acceptance,
prior receiving obligations and named G06 acceptance remain separate.
