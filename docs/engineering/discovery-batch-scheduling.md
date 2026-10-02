# B22 — bounded discovery batch staging

Reviewed 2 October 2026. The default no-journal operation is described below. This is an implementation increment within
[Wave 2 of the existing B01–B50 plan](../product/enterprise-workload-mobility-execution-plan.md),
not a new programme or completion of B22. It composes the
[installed collector](discovery-collector-runtime.md) and the existing native HTTPS
adapters. Native qualification and operating acceptance remain separate.

## Default installed operation

```sh
hosting-discovery-collect batch-stage --config /etc/hosting/discovery/batch.json
```

The path is illustrative, not a supplied site configuration. The command parses one
protected batch manifest, selects tasks due at the initial UTC cutoff and dispatches
those tasks once. Future tasks are reported NOT_DUE without waiting or reading their
collector files. Expired task windows are reported WINDOW_EXPIRED. Due tasks are
round-robin across endpoint queues, oldest first within each endpoint. Output stays
in manifest order, independently of completion order.

Each dispatched task uses the actual existing `stage` operation. It verifies current
campaign signatures, collector enrollment and independent native read witnesses,
then either resumes original signed bytes or collects and stages a new result.
Batch staging never publishes a generation, requests mutation authority, refreshes
credentials, signs a new campaign, retries a failed task or creates a migration job.
Existing `stage` and explicit `publish` commands retain their separate purposes.

## Closed manifest contract

`hosting-discovery-batch/1` contains exactly `format`, `batchId`,
`maxParallelCollections`, `maxDurationSeconds`, `endpoints` and `tasks`.
The manifest is a protected regular file of at most 128 KiB. Duplicate JSON keys,
nonfinite numbers, booleans in integer fields, unrecognized fields and noncanonical
paths are refused. Bounds are 1–16 active collections, 1–3600 seconds of admission,
1–64 endpoint policies and 1–128 tasks. An invalid manifest is rejected before any
task is dispatched. Its exact byte digest is returned for audit correlation, not as
independent signed authority.

Each endpoint policy contains exactly `policyId`, `organizationId`, `siteId`,
`platformFamily`, `endpointId`, `maxConcurrentReads` and
`minReadIntervalMilliseconds`. Concurrent reads are bounded to 1–16 and minimum
admission spacing to 1–15000 milliseconds. Each exact organization/site/platform/
endpoint has one policy. The policy is shared across tenant and native-scope
selections using that endpoint, rather than allocating a new allowance per VM,
project, cluster, credential or service. OpenStack's three service reads share its
selected endpoint allowance. Endpoint aliases must be reconciled by the site owner;
different logical endpoint IDs are not proof of different physical servers.

Each task contains exactly `taskId`, `environmentId`, `campaignDigest`,
`collectorConfigFile`, `collectorConfigDigest`, `policyId`, `notBefore` and
`notAfter`. Windows are explicit UTC, increasing and no longer than one hour.
Duplicate task IDs, campaign digests and collector configuration paths are refused.
The policy selector must exist. The collector configuration digest binds the exact
private file bytes actually parsed; it is not a digest of a later reread. The
campaign digest and environment are compared to the actual campaign, and its native
scope must match the selected endpoint policy. Signature verification remains
independent. A protected manifest or matching digest does not itself authorize any
native contact.

## Native backpressure and stopping

`read_budget.NativeReadGate` implements a FIFO admission queue shared by the batch's
actual adapters. `native_https.read_json` holds a concurrency slot through trust
loading, TLS, GET, response validation and socket cleanup. Read admission is paced
with a monotonic clock; network/server arrival times are not a hard rate guarantee.
A failed read releases concurrency but does not refund its rate slot. Different
endpoint gates progress independently. Waiting consumes the existing per-request
native timeout; an expired queue cannot start a new connection.

Current authority is checked while waiting, after admission, before credentials are
sent and after the response. Stop events prevent further reads and publication of
late results. A local admission failure is latched in the adapter, so a pure
collector cannot convert scheduling refusal into publishable native error evidence.
Genuine native errors retain the existing platform-specific UNKNOWN/hold semantics;
no native absence or completeness is inferred from a local scheduling decision.

The batch duration stops new dispatch/read admission. It is not a promise that a
running thread or remote request can be killed at precisely that instant. The
command drains all started workers and closes their bounded local native requests
before returning. Interruptions request the same stop/drain and use exit 130 with
reconciliation required. A staged original may already exist after a hold or an
interrupted process; explicit replay must use original custody, not assume rollback.

## Outcomes and recovery boundaries

`hosting-discovery-batch-outcome/1` reports the batch identity/digest, initial
`checkedAt`, per-task outcomes and `stagedCount`. BATCH_EVALUATED (exit 0) means the
one-shot evaluation completed without a failed/expired/undispatched due task. It can
contain only NOT_DUE tasks and zero staged results; it is not scheduled-work
completion. BATCH_HELD (exit 2) exposes HELD, WINDOW_EXPIRED or NOT_STARTED tasks
without exception bodies, tokens, secret paths or native error payloads.
Every result explicitly includes `limitScope: THIS_PROCESS_ONLY`,
`durableSchedule: false`, `publicationAttempted: false` and
`executionAuthorized: false`.

Without `--state-directory`, scheduling progress and rate counters are not persisted.
Separate invocations do not share these read limits, endpoint queues or cancellation.
The checkpointed mode described below retains task starts/outcomes, but not fleet-wide
read budgets; it serializes cooperating processes sharing the same private journal. Direct one-shot
collection is not retroactively governed by another batch. Consequently this
increment is **not fleet-wide admission or B22 closure**. Do not run overlapping
batches and infer a combined platform rate limit. Site orchestration must supply
independent non-overlap controls until durable fleet coordination is implemented.
Original-byte outbox recovery and central inventory idempotency remain unchanged;
they alone do not provide exactly-once native collection or durable scheduling.

## Verification and remaining work

Tests exercise real threaded admission, rate spacing, timeout, cancellation,
revocation, error cleanup, exact endpoint scope, and fresh-process batch execution.
Real local VMware/AHV/OpenStack HTTPS fixtures test the actual installed runtime,
independent synthetic signatures and original-byte staging/replay. Wrong config,
campaign, environment and endpoint selections fail before native reads. Dispatcher
fixtures separately test global concurrency, endpoint order, per-task failure
isolation and thread draining. These tests do not qualify an installed platform,
production load, an estate benchmark or a distributed scheduler.

Checkpointed local multi-process exclusion and finite future-task dispatch are now
implemented separately below. B22 still needs fleet-wide scheduling/dispatch, globally
coordinated endpoint budgets, freshness monitoring, larger resumable publication and measured
estate-scale acceptance. Wave 2 also retains its other B14–B21 implementation and
native/owner acceptance gates. No Wave 3 work is started or marked complete by this
increment. No compatibility wrapper, SQL migration, new privilege or native mutation
path is introduced.


## Checkpointed scheduling continuation — 2 October 2026

The optional `--state-directory` on batch-stage now persists a finite schedule's
starts/outcomes. `batch-run` additionally waits for enrolled future tasks within the
existing duration bound. `batch-inspect` and `batch-reconcile` expose history and
original-only recovery. The ordinary no-journal path is unchanged. Read the
[checkpointed scheduling contract](discovery-checkpointed-scheduling.md) for exact
commands, formats, locks, uncertainty, historical results and remaining fleet gates.
