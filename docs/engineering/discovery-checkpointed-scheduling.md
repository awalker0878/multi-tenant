# B22 — checkpointed scheduling for an enrolled discovery batch

Reviewed 2 October 2026. This continuation starts from
`73731f7e6432e5adc44e11a89c0b5ddd5f3578e9` under the
[existing B01–B50 execution plan](../product/enterprise-workload-mobility-execution-plan.md).
It adds durable local progress and bounded waiting to the existing batch dispatcher.
It does not complete fleet-wide scheduling, periodic monitoring or native acceptance.

## Installed commands

The existing `hosting-discovery-collect` command accepts an opt-in private journal.
The directory must already exist, be owned by the service user and have private
permissions. These paths illustrate an approved installation, not supplied site values.

```sh
hosting-discovery-collect batch-stage --config /etc/hosting/discovery/batch.json --state-directory /var/lib/hosting/discovery/batch-state
hosting-discovery-collect batch-run --config /etc/hosting/discovery/batch.json --state-directory /var/lib/hosting/discovery/batch-state
hosting-discovery-collect batch-inspect --config /etc/hosting/discovery/batch.json --state-directory /var/lib/hosting/discovery/batch-state
hosting-discovery-collect batch-reconcile --config /etc/hosting/discovery/batch.json --state-directory /var/lib/hosting/discovery/batch-state
```

`batch-stage` without a journal preserves its existing one-shot contract. With a
journal it selects currently due, unstarted tasks, retaining their starts and outcomes.
`batch-run` requires a journal and additionally waits for future pre-enrolled tasks,
up to the existing manifest's maximum run duration. The same dispatcher, executor,
endpoint gates and duration timer survive those waits; rate spacing is not reset at
each due time. There is no repeating daemon, campaign issuer or token-refresh action.

`batch-inspect` reports retained progress without reading collector configuration,
contacting platforms or creating enrollment. `batch-reconcile` additionally invokes
only the installed collector's existing **inspect** operation for unresolved tasks.
It never invokes stage, publish or a native adapter as a fallback. The existing
[original-outbox inspection contract](discovery-outbox-inspection.md) remains authoritative.
No public API, SQL migration, human/service role change or new executable is introduced.

## One manifest, one local progress owner

The [existing batch manifest](discovery-batch-scheduling.md) and its exact byte digest
bind every task, environment, campaign digest, collector configuration digest, endpoint
policy and time window. `batch_journal.BatchJournal` is the sole progress owner;
`batch_runtime` still owns one dispatcher for both ordinary and checkpointed runs.
The journal checks its original manifest again while work is admitted and native reads
recheck their current callback. Editing or replacing the manifest cannot silently
relabel a previously started task. A different reviewed batch needs separate custody;
changing directories must never be used to escape an unresolved campaign.

The journal has a persistent, nonblocking POSIX lock plus a thread lock. Cooperating
processes sharing **that same directory** cannot dispatch the same batch concurrently.
The lock file is never deleted. Directory and lock identities are rechecked so a
replaced path cannot continue under an obsolete lock. This is not a cross-host lock
service, global endpoint budget or protection from an administrator changing custody.
No support for network/distributed filesystems is claimed.

Events are canonical, create-only, digest-linked records with consecutive sequence
numbers, batch identity, original manifest digest, UTC time, task identity and bounded
outcome metadata. A complete record is flushed and published before its effect can
start. No mutable state head, overwrite, retry reset, delete or repair endpoint exists.
The existing private artifact utility provides descriptor-relative/no-follow custody
and no-overwrite publication; no second file-publication implementation was introduced.

| Event | Permitted transition |
|---|---|
| ENROLLED | First record only; binds this journal to the immutable manifest. |
| TASK_STARTED | An unstarted task inside its original window; persisted before invoking stage. |
| TASK_EXPIRED | An unstarted task whose window has ended; it cannot later run. |
| TASK_HELD | A started task with unsuccessful or uncertain execution; no automatic retry follows. |
| TASK_STAGED | A started task whose exact bounded stage outcome was returned and retained. |
| TASK_RECONCILED | A started/held task with currently verified original signed outbox custody; no collection request. |

Partial or unexpected files, changed bytes, gaps, invalid transitions and clock
regression hold. Maximum accepted history is 385 records (enrollment plus at most
start/hold/reconcile per 128 tasks), at most 8 KiB per record. These are accepted data
bounds, not a hard operating-system memory/disk deadline. A poisoned append instance
cannot continue writing: failure after publication may already have left the final
record, which must be read and reconciled on a new invocation.

## Restart and original-result reconciliation

A fresh invocation replays the complete journal before selecting work. Already-staged
records return **ALREADY_RECORDED** with `historicalOnly: true`; they are not revalidated
as current observations and do not count as new staging. Revocation does not rewrite
historical checkpoints. Before publication or assessment, the corresponding active
owner still checks current authority independently.

A start without a confirmed completion, including process termination immediately
after the start, returns **OUTCOME_UNKNOWN**. The scheduler does not infer rollback,
delete the start or call stage again. The existing first-capture outbox claim remains
an additional independent protection, not a reason to skip scheduling uncertainty.

Explicit reconciliation verifies the exact scheduled configuration, environment and
campaign digest through the existing collector inspector. Only **STAGED_ORIGINAL**
can close the task. Original campaign/result signatures and live enrollment/witness
checks must pass. Missing signer/native credential files need not block inspection of
already-retained bytes; missing, corrupt, expired or revoked original custody does.
An absent reference or unresolved collection claim never means permission to recapture.
The journal cannot adopt arbitrary files as original results or renew their timestamps.

Failed reconciliation preserves all original journal bytes and reports a hold. A
successful reconciliation appends an event without rewriting previous failures.
No reconciliation of publication status, native inventory completeness, ownership,
read admission elsewhere or migration authority is implied.

## Output and stopping rules

Checkpointed stage/run results use `hosting-discovery-checkpointed-batch-outcome/1`.
They retain the batch identity, task order and stage counts, adding journal sequence/
digest, unresolved/pending task counts, `waitedForDue`, `durableSchedule: true` and
`scheduleScope: ONE_LOCAL_BATCH_JOURNAL`. Native read `limitScope` remains
**THIS_PROCESS_ONLY**. A local durable queue must not be advertised as globally
coordinated fleet admission. Every result retains `executionAuthorized: false` and
`publicationAttempted: false`.

`stagedCount` counts only this invocation's successfully checkpointed stage results.
Previously recorded tasks are explicitly historical. `pendingTaskCount` counts future
or unstarted tasks remaining when the bounded run stops. Exit zero means the selected
work was evaluated, not that every future task ran or that inventory is complete.
Any expired, held or unknown due task makes the batch held. Inspection exit zero means
history was inspected without unresolved starts, not health or native qualification.

The existing run-duration limit remains 1–3600 seconds. Running native sockets drain
under existing request deadlines when the timer or ordinary interruption stops new
reads. Operating-system termination cannot promise cleanup; its retained start is the
recovery boundary. Future tasks retain their original windows for another authorized
invocation. There is no implicit publication, data mutation, cleanup or broader request.

## Deployment, retention and verification

Protect this directory, the original discovery outboxes, manifest/configuration,
issuer/witness revision floors and signed artifacts as one recovery set. Journal hashes
are not signatures or an independent audit service. Removing a complete suffix or
restoring all files to an earlier consistent snapshot cannot be detected without an
external high-water mark. Restore initially without collection enabled and reconcile
original custody before authorizing any new work. Never use a new journal/outbox to
turn an old unknown operation into a new attempt.

Tests use actual private files, process locks and a child process exiting after its
saved start. They cover unknown outcomes, invalid transitions, changed manifests,
clock regression, partial records, unsafe paths, lock replacement, interrupted
publication and bounded waiting. Actual signed loopback VMware/AHV/OpenStack fixtures
exercise the existing native read paths and original-result inspection. An installed
wheel check creates, inspects and runs the bounded wait for future-only scheduling
state outside the checkout, without native credentials. These are component/protocol tests, not deployed fleet
performance, filesystem failover, access-control or native-platform qualification.

The real-process fixtures now separate interpreter/import setup from the operation
being tested. A test-only readiness marker and activation handshake allow competing
children to be prepared before either begins collection. Setup and activation waits
are bounded to 30 seconds; the existing active five-second collection/exclusion and
ten-second journal operation checks remain unchanged. Readiness is never interpreted
as successful collection or a valid refusal: exit codes, original signed bytes,
request counts, recovery state and scope assertions still determine the result.
The normal installed `-m` command tests remain, and the contending CLI fixture invokes
the same command entry point only after setup. The helper is not installed runtime
code and changes no campaign lifetime, native timeout, production lock or permission.

B22 still requires durable fleet-wide policy/endpoint budgets, authenticated periodic
freshness monitoring and alerts, scalable resumable publication, independent omission
reconciliation and estate measurements. The freshness HTTP routes remain human-only;
this change does not reuse human sessions as machine credentials. B05 and later native
provisioning/migration/recovery waves remain open. No production system was contacted.

## Primary implementation references

Consulted 2 October 2026: Python's [fcntl interface](https://docs.python.org/3.13/library/fcntl.html)
defines exclusive/nonblocking advisory locks, and its [OS interface](https://docs.python.org/3.13/library/os.html)
defines descriptor-relative file operations and fsync. Platform/filesystem behavior
still requires site qualification; the references do not establish a distributed lock
or a hard persistence deadline. No Python, provider or dependency pin changed.
