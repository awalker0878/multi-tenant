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

## Stop and recovery decisions

Stop rollout on unexpected contract/schema errors, replay incompatibility, authorization widening, lost evidence, unknown native effects, unexpected writer overlap or unacceptable user impact. Preserve working compatible instances; hold affected new work; retain observation access and diagnostics. Escalate to the owner of the failing boundary.

Use [rollback deployment](rollback-deployment.md) only when current persisted state, histories and dependencies remain compatible with the prior version. If a destructive migration or target-write/data transformation crossed the reversal boundary, use an approved forward repair or [recovery](recovery.md). Restoring an older database under a newer/native-active worker is prohibited by the recovery contract.

If rollout loses worker routing information, hold dispatch until existing workflow histories and worker versions are reconciled. Do not kill a workflow or submit a new job merely to obtain a clean target-version execution.

## Verification and records

Record old/new digest inventory, mixed-version duration, migration actions/checks, worker routing/history evidence, independent native observations, denied-access results, outage/latency/backlog measures and any rollback/forward-repair outcome. Confirm alerts, backup and restore still work on the resulting combination.

Update the installed BOM and effective support scope. Assurance records qualification reuse or rerun decisions for changed artifacts/tuples; preserve limitations for disconnected/held sites. Do not publish an upgraded combination as supported until its required gate evidence and receiving-owner acceptance exist.
