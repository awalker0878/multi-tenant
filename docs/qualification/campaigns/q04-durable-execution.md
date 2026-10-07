# Q04 — Durable execution

Q04 verifies R15–R17 and R29–R31. It supports P06.01–P06.06, P07 failure/recovery work and P10 recovery reruns. The principal criteria are G06.01–G06.04, G07.03, G09.04 and G10.02. Its central rule is that an uncertain native outcome holds dependent mutation until authoritative reconciliation resolves it.

## Scope and ownership

Lifecycle and worker owners supply workflow/activity contracts; SRE supplies persistence and dependency recovery; assurance supplies evidence custody. Quality coordinates injection timing and an independent observer reads effects. E2 uses real databases, broker and Temporal with controlled platform adapters. E3 reruns relevant faults on the exact authorized native tuple.

Use the [lifecycle specification](../../services/lifecycle.md), [assurance specification](../../services/assurance.md) and [application walkthrough](../../product/application-walkthrough.md). Bind workflow, worker, adapter, native-plan and state identities in the run manifest.

## Preparation

1. Complete the applicable Q01/Q03 checks for current contracts, admission and reservation behavior.
2. Instrument boundaries before dispatch, before native acceptance, after acceptance/before acknowledgement, after evidence upload and before completion publication.
3. Prepare two worker epochs, duplicate messages, identity/approval revocation and partition controls; retain a separate observation path.
4. Define expected hold, reconciliation, permitted retry and compensation behavior for each tested effect. Identify effects without reliable native idempotency/readback.
5. Verify bounded stop/revocation, restoration inputs, alert routing and test-owned cleanup scope before injecting failures.

## Case matrix

| Case | Action or injected fault | Required observation | Evidence |
| --- | --- | --- | --- |
| Q04.01 | Crash after durable admission but before dispatch; redeliver admission/outbox messages | One logical job/workflow starts; no admitted work disappears or starts twice | Admission/outbox/inbox/workflow identity timeline |
| Q04.02 | Crash before native acceptance and restart with a duplicate activity | Effect is absent or safely resumed after authority/precondition checks; no duplicate owned object | Journal, worker trace and independent readback |
| Q04.03 | Accept the native effect but drop the response and restart the worker | Outcome becomes unknown; dependent writes and release remain held; readback resolves before any retry | Native acceptance timestamp and reconciliation timeline |
| Q04.04 | Resume an old worker after lease expiry/new epoch and attempt the same effect | Stale identity/epoch cannot mutate; no overlapping writer for the owned scope | Fence/identity denial and native effect count |
| Q04.05 | Revoke approval or identity between activities and immediately before a native effect | New effects fail admission; already accepted outcomes are observed and contained under declared recovery authority | Revocation/effect ordering and hold record |
| Q04.06 | Partition workflow, database, broker, owner API or evidence store separately | Persisted state remains consistent; bounded retries do not imply success; unavailable evidence prevents false completion | Dependency faults, journals and recovery observations |
| Q04.07 | Request pause/cancel/stop during reserve, apply and activation boundaries | No new prohibited effect starts; accepted work is reconciled; cancellation does not pretend to undo native state | Boundary-state timeline and operator-visible outcome |
| Q04.08 | Restore older workflow/database state and reconnect an active worker | Restored system starts read-only; epochs and accepted native effects reconcile before writes resume | Restore version set, native readback and re-enable decision |
| Q04.09 | Tamper with an evidence object/digest, use wrong-tenant evidence or interrupt finalization | Custody/digest/tenant checks reject invalid evidence; job cannot claim verified completion | Evidence validation and access-denial records |
| Q04.10 | Hold a job long enough to trigger its approved alert, then exercise operator reconciliation | Alert is received/acknowledged; authorized action follows the runbook and leaves attributable evidence | Alert receipt, operator action and final reconciled state |

## Execution and observations

For each effect class, run the failure on both sides of the native acceptance boundary. Record the observed boundary rather than inferring it from a worker log. A replay-safe workflow alone does not establish an idempotent external effect.

Repeat the unknown-outcome case with native response identity missing or ambiguous. The correct outcome may be an unresolved hold requiring operator review. The test fails if the implementation guesses success, retries blindly or releases a possibly consumed allocation.

Bind native operation plan and state/backend identity to any tested apply. Independent native readback cannot by itself repair state history or prove a stale native API writer has stopped.

## Pass criteria and evidence

Each fault produces one logical operation or an explicit held uncertainty. Authority is checked at the declared effect boundary; stale workers never regain write permission. Evidence finalization, alert delivery and recovery must be observed rather than inferred from configuration.

Retain chronological journal/workflow/worker/native observations, message IDs, scope/epoch transitions, state versions, evidence digests, alerts and operator decisions. Classify simulation as E2 and native observations as E3. Link results to [gate criteria](../../implementation/gates.md) through the [delivery register](../../implementation/delivery-register.yaml).

## Cleanup and reruns

Reconcile every held operation and allocation before cleanup; never delete unknown resources merely to reset a test. Rotate test identities and retain failed-run evidence. Rerun affected cases after workflow versioning, adapter retry/readback, fencing, journal, evidence or recovery changes.

## Executed P06 simulation

The [P06 check matrix](../../../verification/p06/check-matrix.md) maps this campaign
to source-bound PostgreSQL, actual Temporal and three-browser observations.
The [qualification index](../../../verification/p06/final/qualification-index.json)
retains passing results and the [correction record](../../../verification/p06/corrections.md)
retains failed attempts. These are E2 simulation observations. The older-journal
restore deliberately denies re-enable; no native recovery or automatic epoch
rebind is inferred. Designated receiving remains in the canonical G06 record.
