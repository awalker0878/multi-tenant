# Commissioned discovery scheduling and original-only publication

Reviewed 3 October 2026. This B22 increment extends the existing finite batch,
collector, original outbox and checkpoint journal. It supplies installed service
composition for preauthorized campaigns and one shared host's endpoint budget.
It does not issue campaigns or prove native visibility or estate scale.

## Collection, publication and recovery

The protected batch manifest still pins exact collector configuration bytes,
campaign digest, environment, endpoint policy and finite task window. Use:

```sh
hosting-discovery-collect batch-run --config /etc/hosting/discovery/batches/batch-1.json --state-directory /var/lib/hosting-discovery/batches/batch-1 --fleet-state-directory /var/lib/hosting-discovery/endpoint-budgets
hosting-discovery-collect batch-publish --config /etc/hosting/discovery/batches/batch-1.json --state-directory /var/lib/hosting-discovery/batches/batch-1
```

`batch-run` retains starts/staged outcomes and waits for due tasks within its original
runtime. `batch-publish` uses only original signed outbox bodies. It never collects
or re-signs. Current issuer, witness, collector, campaign, protected configuration,
mTLS and task-window checks remain with their existing owners. A receipt must match
the retained campaign, environment, request/result digests and collection quality.

A publication start is flushed before delivery. A lost reply or interrupted process
remains `DELIVERY_UNKNOWN`, including a start without completion. Ordinary publication
leaves that uncertainty intact. After reconciling the external ingest owner, select:

```sh
hosting-discovery-collect batch-retry-publication --config /etc/hosting/discovery/batches/batch-1.json --state-directory /var/lib/hosting-discovery/batches/batch-1
```

At most three attempts are allowed per task. Acknowledged tasks are historical on
later invocations and are not posted again. Checkpoints do not renew signatures or
grant a later capture. `batch-inspect` reports retained delivery uncertainty;
`batch-reconcile` still reconciles only original capture custody. Publication cannot
clear a capture hold or select new bytes. Exit 3 identifies unknown delivery; exit 2
identifies a hold; exit 0 on publication means all selected tasks retain acknowledgements.

## Persistent shared-host endpoint budget

`SharedNativeReadGate` extends the existing `NativeReadGate` contract. Every cooperating
batch on this host must use the same existing private budget directory and service UID.
Budget identity is organization, site, platform family and endpoint; changing tenant
or native scope cannot create another budget for that endpoint.

An immutable policy and retained directory/lock identities bind concurrent GET limits
and intervals. OS slot locks remain held through native socket cleanup. The next rate
slot is reserved and fsynced before admission: failed reads/process exits do not refund
it. The kernel releases concurrency after process exit. Queued requests retain their
original monotonic deadline and recheck current authority while waiting and after
admission. Policy changes, replaced locks/directories, missing rate custody, malformed
records, clock regression and deadline expiry hold.

Output states `ONE_SHARED_POSIX_COORDINATOR_HOST`. Independent hosts/directories or
bypassing clients are outside this budget. It is not a multi-host global scheduler,
distributed/native lease or native fence. Use commissioned local POSIX flock/fsync
semantics. Change policy only after draining old collectors and reconciling custody.

## Service and timer composition

The reviewed units in `deploy/discovery/` use installed commands in `/opt/hosting/bin`.
Commission that prefix, the nonprivileged `hosting-discovery` account, protected
campaign/configuration/trust material and retained outbox before installing them.
`StateDirectory` creates private per-batch journals plus the common endpoint budget.
The collection service explicitly stages and then publishes only after successful
staging. Its timer evaluates an enrolled immutable manifest each minute; systemd
excludes concurrent invocations of that unit. Missed ticks reuse the same journal.
Held/unknown outcomes stop at their retained decision and require reconciliation.

For a reviewed finite manifest named `batch-1`, commission the units, validate them
with `systemd-analyze verify`, reload the unit manager and enable
`hosting-discovery-collect@batch-1.timer`. Timer ticks never create/renew campaigns.
Changing manifest bytes after enrollment holds. Later collections require a new
authorized campaign set, batch identity and journal; preserve the prior history.

## Conversion and qualification boundaries

The B48 conversion scope includes complete batch journals, original outboxes,
campaign/trust material and endpoint policy/rate/identity files. Quiesce collection
and publication before backup/conversion. Complete rollback is not detected by local
hashes alone: external custody and actual ingest-generation reconciliation remain
necessary. Relocating identity-bound budget files requires reviewed commissioning on
the new host after old collectors are fenced. Never reset custody to turn an uncertain
operation into a fresh attempt.

Tests execute real native TLS, signatures, mTLS publication, exact original retries,
process locks/exits, persistent rate limits, independently constructed gates,
corruption/replacement and revocation. They establish local protocol/service behavior.
Native omission/privilege reconciliation, commissioned deployment/identity/custody,
measured estate performance, multi-host global budgets, large-result ingest and
operating acceptance remain open. The 1 MiB signed aggregate bound is unchanged.
