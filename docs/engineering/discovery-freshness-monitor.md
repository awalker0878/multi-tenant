# Periodic freshness monitoring projection

Reviewed 2 October 2026. This B22 continuation composes the existing retained
[freshness history](discovery-freshness-history.md) into a finite periodic evaluator.
It does not collect inventory, refresh credentials, contact native platforms, deliver
notifications or authorize execution.

The 3 October [installed monitoring service](discovery-monitor-service.md) composes
this projection with current SERVICE IAM, retained delivery attempts and explicit
authenticated alert-owner transport. This module remains the pure projection owner;
deployment/delivery evidence must use the service's own outcomes.

## Deterministic monitoring slots

`FreshnessMonitor` accepts a bounded set of exact environment/native-scope targets and
a server-owned cadence policy. Each target and interval maps to a deterministic check
ID. Repeating the same slot after restart therefore reuses the existing immutable
freshness check instead of resampling inventory under a new identity.

The default policy is a 300-second interval, no more than 256 targets and no more than
288 cycles. Supported bounds are 30–86,400 seconds, 1–2,048 targets and 1–2,016 cycles.
Runtime is separately bounded to seven days. UTC monitor time must be monotonic; clock
regression holds rather than creating a reordered history.

A cycle uses the existing `FreshnessHistoryRepository.capture` owner and its tenant,
scope, database-role, current-authority, audit, source-recheck and exact-ID semantics.
One target failing authorization or retained-history validation produces `CHECK_HELD`
for that target. It is not converted into a healthy observation and does not request a
new collection.

## Alert intent, not alert delivery

An alert is a deterministic projection of one retained freshness record. Before the
projection is accepted, the complete report SHA-256 and retained record SHA-256 are
recomputed from the canonical content. This prevents altered issue lists, bindings or
metadata from being treated as the original retained check.

Critical intents cover missing/future/stale inventory and missing privileges. Warning
intents cover refresh-due, partial/unknown collection and reported collection errors.
`NATIVE_VISIBILITY_UNVERIFIED` remains important evidence context but does not by itself
create a notification intent because this repository has no independent enumeration
proof. Each intent retains the exact check record digest, issue codes and change kinds.

Every intent says `notificationRequired: true`, `notificationAttempted: false`,
`deliveryOwner: EXTERNAL`, `collectionRequested: false` and
`executionAuthorized: false`. No email, paging, ITSM ticket or webhook is sent. Delivery,
acknowledgement/escalation and operating ownership therefore remain B22/B45 work.

## Restart and operating limits

The periodic runner is deliberately not a distributed scheduler. Slot identity makes a
restarted evaluator idempotent against the existing database history, but multiple
service instances still require an externally owned deployment/scheduling model and
current service identity. The monitor does not extend a human session, mint a collection
campaign or invoke `hosting-discovery-collect`.

A retained alert remains historical evidence. Later inventory or review may change the
current state, so consumers must evaluate the newer retained check rather than treating
an older alert intent as continuing authority. Database restore must preserve freshness
history/audit ordering before the monitoring service resumes writes.

## Verification and remaining B22 work

Dedicated unit tests cover policy/target bounds, deterministic IDs, exact-slot replay,
warning/critical selection, digest tampering, duplicate/oversized target refusal,
per-target revocation holds, finite periodic execution and monitor-clock regression.
They run with the existing freshness-history transaction fixture and make no native
calls. Existing freshness-history/page tests remain in force.

B22 now has [service scheduling and original-only batch publication](discovery-service-scheduling.md),
a shared-host persistent endpoint budget and installed alert-delivery composition.
Commissioned deployment/receiver/identity/custody, multi-host global budgets,
independent omission/privilege-loss reconciliation, large-result publication and
measured estate qualification remain open. This projection neither closes B22 nor
supplies native/operational acceptance.
