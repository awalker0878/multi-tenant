# Upgrade services and workers

Procedure ID: OPS-UPGRADE. Owners: delivery/SRE with context, lifecycle and dependency owners. Scope: R02/R15/R16/R29/R31/R35; P01.04, P10.02/P10.05; Q09. Applies to a reviewed source→target release pair and its explicit compatibility window.

## Inputs and readiness

Record source/target manifests and configuration revisions, component dependency versions, current schema/migration state, workflow/worker version inventory, active/held/unknown operations, support tuples, backup checkpoints and change owner. Read target release compatibility, upgrade notes, qualification impact and known limits. Missing compatibility or recovery information stops the affected upgrade.

Confirm exercised recovery from the existing release, protected keys and an independent operator route if console/identity services are affected. Verify promoted immutable artifacts using [promote release](promote-release.md). Configure the observation window and rollback decision deadline from the accepted operating record; do not invent them during a failure.

## Compatibility decision

| Area | Required evidence before rollout |
| --- | --- |
| APIs/events | Supported mixed-version producers/consumers; unknown-field/version handling; retained events remain readable |
| Databases | Expand migration readable/writable by both supported versions; clear irreversible contraction boundary and data validation |
| Temporal/workers | Server/SDK compatibility and replay behavior for existing histories; selected routing/versioning keeps each workflow on a compatible worker |
| Native adapters/plans | Artifact/profile changes assessed against immutable plans, qualifications and running effect semantics |
| Trust/configuration | New and retiring issuer/certificate/configuration behavior validated without broadening scope |
| Evidence/state | Stored evidence, key references, IaC state and operation journal remain readable and consistent |
| Laravel local jobs/schedules | Old payloads and failed-job replays remain compatible; driver-specific redelivery budgets, tenant context reset, drain and scheduler handover are exercised |
| Runtime configuration/keys | Protected caches rebuilt for the target environment; every process reloads the selected key/configuration revision; mixed-instance decryption and rollback policy verified |

Do not upgrade simply because every component has a newer available version. The release BOM defines the tested dependency combination. Select dependency-first or application-first order from that combination's compatibility requirements.

## Procedure

1. **Inventory and bound work — SRE/lifecycle.** Capture current durable jobs, queued tasks, native operations, reservations, evidence backlog and resource ownership. Hold affected new admissions when required by the compatibility plan. Confirm the hold is enforced and identify any permitted existing work.
2. **Prepare recovery — persistence/key owners.** Capture documented backups/checkpoints and verify their recoverability/retention. Record consistency watermarks and native effects that may continue beyond them. A snapshot is not authority to revert external effects.
3. **Expand schema/configuration — migration owner.** Apply only the reviewed additive changes under the dedicated identity. Check actual schema/version and representative records. On partial failure, stop and reconcile migration state before retry.
4. **Roll compatible services — SRE/context owners.** Replace one bounded instance/group at a time using target digests. Confirm authentication, readiness, cross-version contracts and tenant-negative journeys before broadening rollout. Preserve sufficient healthy capacity.
5. **Roll compatible workflow workers — lifecycle.** Use the selected tested worker-version routing. Existing histories retain a compatible execution path; new work uses only eligible target workers. Observe replay/task failures and admitted job identity before further rollout.
6. **Roll site pools — platform/lifecycle.** Hold the affected pool, establish safe points and effective fencing where old/new workers could overlap, then enroll target artifacts/scopes. Reconcile in-flight native effects before the new pool may continue them. Disconnected sites retain their supported version/hold explicitly.
7. **Validate under bounded load — SRE/quality.** Exercise representative operator journeys, idempotent retry, denial, evidence finalization, queue recovery and supported native observations in the authorized environment. Compare against accepted latency/error/backlog and safety conditions.
8. **Release holds gradually — lifecycle/service owner.** Recheck grants, plan freshness, reservations, commissioning and qualification before resuming each held scope. Upgrade completion alone does not renew old approvals or authorize a changed plan.
9. **Contract later — migration/release owner.** Remove old columns/contracts/workers only when old readers/writers, retained workflow histories, event replay windows and the published rollback window no longer need them. Record the irreversible boundary before execution.

## Laravel rollout controls within steps 3–4

Follow [data and messaging](../../engineering/data-and-messaging.md) for schema and job compatibility and the [deployment model](../deployment-model.md) for process/configuration/key ownership.

| Control | Operator action and observation |
| --- | --- |
| Schema expansion | Use the dedicated migration job/identity; confirm expected schema and index validity, not only a successful exit. Keep large backfills separately resumable with lock/load limits and invariant checks |
| Config and caches | Generate the target environment's protected cache only after injecting its configuration and secret references. Check non-secret effective settings; prevent resolved secrets entering images or evidence. Avoid whole-store cache flushes |
| HTTP instance retirement | Remove the instance from new traffic, allow the bounded request drain, then replace it. Verify target readiness and tenant-negative journeys before restoring traffic |
| Local queue retirement | Stop new consumption by retiring workers; observe completion or record interruption at the declared deadline. Replace processes under the supervisor/orchestrator and verify their image/configuration revision. Preserve stable job/operation identities |
| Queue timing | Recheck external request deadlines, job/worker timeout, redelivery (`retry_after` or SQS visibility) and process termination grace together. A forced exit may leave work outcome unknown; it is not proof that its effect failed |
| Scheduled tasks | Hand over the single scheduler ownership mechanism; interrupt/replace any sub-minute process running the prior code. Preserve named lock scope and missed-run reconciliation; do not clear locks blindly |
| Long-lived state | Verify alternating tenant/actor jobs after replacement, including an exception path. If Octane is selected, include retained HTTP worker state and memory checks |
| Encryption rotation | Follow the staged key lifecycle in the deployment model; old and new instances must decrypt each other's required values before changing the encryption key. Confirm old queued ciphertext/backup recovery and the key retirement boundary |

Release bindings record the tested graceful reload/replacement mechanism for the selected Laravel version and process manager. A generic reload signal is not sufficient evidence that all workers exited, the scheduler handed over, or old native writers were fenced. Do not use Laravel maintenance mode alone as a system-wide lifecycle/native admission hold.

## Stop and recovery decisions

Stop rollout on unexpected contract/schema errors, replay incompatibility, authorization widening, lost evidence, unknown native effects, unexpected writer overlap or unacceptable user impact. Preserve working compatible instances; hold affected new work; retain observation access and diagnostics. Escalate to the owner of the failing boundary.

Use [rollback deployment](rollback-deployment.md) only when current persisted state, histories and dependencies remain compatible with the prior version. If a destructive migration or target-write/data transformation crossed the reversal boundary, use an approved forward repair or [recovery](recovery.md). Restoring an older database under a newer/native-active worker is prohibited by the recovery contract.

If rollout loses worker routing information, hold dispatch until existing workflow histories and worker versions are reconciled. Do not kill a workflow or submit a new job merely to obtain a clean target-version execution.

## Verification and records

Record old/new digest inventory, mixed-version duration, migration actions/checks, worker routing/history evidence, independent native observations, denied-access results, outage/latency/backlog measures and any rollback/forward-repair outcome. Confirm alerts, backup and restore still work on the resulting combination.

Update the installed BOM and effective support scope. Assurance records qualification reuse or rerun decisions for changed artifacts/tuples; preserve limitations for disconnected/held sites. Do not publish an upgraded combination as supported until its required gate evidence and receiving-owner acceptance exist.
