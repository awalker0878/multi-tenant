# Roll back an application deployment

Use this procedure when a product release causes a regression and the previous release remains compatible with persisted state and active work. [Upgrade](upgrade.md) owns compatibility and migration rules. A deployment rollback changes product software/configuration; it does not reverse completed native effects or recover divergent application data.

## Ownership and inputs

The delivery owner proposes the target release; SRE controls deployment; service/database owners validate persisted-state compatibility; lifecycle validates workflow histories and workers; assurance reviews qualification impact. The change authority or incident commander approves the bounded rollback under [support](../support.md).

Gather current and target signed release manifests, exact image/configuration digests, API/event/schema compatibility records, migration receipts, active workflow and native-operation inventory, worker routing assignments, evidence/qualification bindings, backup recovery points and the triggering incident/change record.

Use only deployment actions supplied by the selected release and runtime. This document defines the required decisions and observations; it does not assert an available rollback CLI, manifest path or automated endpoint. If a compatible rollback action is unavailable, contain the incident and select repair forward or coordinated recovery.

## Prerequisites and decision

- Verify the previous release artifact is available, its signatures/trust are valid and its configuration references resolve without exposing secrets.
- Confirm old service code can read the current database schema and all values written by the newer release, including new enum variants and mandatory fields.
- Confirm current consumers/producers can interoperate with events and API payloads already emitted, queued or retained for replay.
- Confirm the selected Temporal server/SDK/worker combination supports the histories and persistence formats in scope; restoring an old binary is not proof of replay compatibility.
- Identify destructive or irreversible migrations, changed external effects and qualification invalidations before choosing a rollback target.
- Record the accepted observation windows and abort criteria for the change; use environment-specific values from approved release/support records.

| Observed condition | Allowed path |
| --- | --- |
| Previous code supports current schema, contracts and affected histories | Bounded software rollback with preserved durable state |
| New worker histories require the newer compatible worker | Retain/reroute those histories to a compatible worker; roll back only independently compatible components |
| Destructive schema contraction or unsupported persisted values occurred | Repair forward or explicitly planned data recovery; no blind down-migration |
| Temporal persistence or server downgrade compatibility is unproven | Keep the compatible engine version and escalate to lifecycle/SRE; do not downgrade by assumption |
| Native effect outcome is unknown | Hold affected resources and reconcile independently before changing execution ownership |
| Migration target accepted application writes | Preserve target data/source fencing; authorize source-return or forward recovery separately |

## Contain and preserve

1. Declare the release regression and bound the rollback scope by environment, services, workers and tenants. Record known symptoms, current native exposure and the coordinator.
2. Stop affected new admissions and deployment automation that could race with the rollback. Preserve independently safe read-only services where their compatibility is established.
3. Inventory active jobs, histories, operations and reservations. Record each worker version and the histories it can execute, plus any currently dispatched native requests.
4. Move affected work to documented safe points where possible. Observe in-flight native operations; a drain timeout or cancellation request does not establish that an effect ended.
5. Where worker replacement changes execution ownership, revoke or isolate superseded native authority and verify effective old-worker fencing. A new deployment revision or lease epoch does not block a partitioned worker with valid cached access.
6. Capture protected backups/checkpoints required by the release's rollback plan, migration receipts, workflow identifiers and relevant audit/telemetry. Preserve configuration and artifact digests without copying secrets.

Expected observation: the selected rollback has one owner, no competing rollout is active, in-flight effects are tracked, and affected execution ownership can be changed without overlapping writers.

## Verify compatibility before changing code

7. Database owners inspect applied migration receipts and stored-data changes against the previous release's declared reader/writer support. Preserve additive schema where required; do not run destructive reversal merely to match an older migration list.
8. Contract owners check the active mixed-version window for service APIs, command receipts, event envelopes and queued messages. Keep unsupported messages held for a compatible consumer rather than deleting or rewriting them.
9. Lifecycle reviews affected Temporal histories against the target worker's validated compatibility. Keep compatible version routing explicit; do not reset workflow history or launch a second job to force old code to proceed.
10. SRE confirms the deployment action will not inadvertently downgrade database, broker, Temporal or storage dependencies whose persisted formats require their current versions.
11. Assurance checks whether the previous artifacts/configuration still have applicable qualification and whether intervening native or policy changes invalidate reuse. Reinstalling a formerly qualified image does not automatically restore its support claim.
12. Record the go/no-go decision with component-specific scope, accepted compatibility evidence and unresolved holds. Obtain the named change/incident authorization before altering the deployment.

Expected observation: every component selected for rollback has a supported state/contract/history path; incompatible components remain on a contained compatible version or move to a separately approved recovery path.

## Deploy the compatible release

13. Apply the release-specific rollback action to a bounded component/pool while preserving current durable databases, history and journal state. Use the exact reviewed artifact and non-secret configuration revisions.
14. Verify startup validation, dependency connectivity, trust, health and schema access. Stop on incompatible stored records, migration attempts outside the plan or unexpected bootstrap behavior.
15. Route only compatible histories/tasks to the selected workers. Keep existing ownership and operation identifiers; deployment rollback never creates new authority or turns an unknown operation into `not_started`.
16. Independently reconcile any operation whose response or ownership changed during deployment. Keep its hold until native facts and the current authorization permit a next action.
17. Exercise read-only and bounded authorized journeys through the complete console/service path. Check exact-plan binding, idempotent retries, denied tenant access and truthful held-job presentation.
18. Re-establish fresh telemetry and actual alert delivery using [observability](../observability.md). Observe the change under the accepted window and abort conditions before expanding rollout.
19. Roll back remaining compatible components in the reviewed dependency order. Preserve a written map of mixed versions until the transition completes.

Expected observation: the chosen components serve compatible state and traffic, required denial paths hold, workflow histories progress safely where allowed, and no duplicate native effects or hidden schema reversal occur.

## Stop or recover forward

Stop the rollout if old code cannot interpret current state, workflow replay fails, ownership becomes ambiguous, authority cannot be validated or independent application/native checks regress. Hold affected admission and preserve observations; do not oscillate releases or replay jobs hoping to clear the error.

If the previous release cannot operate safely, restore the compatible current worker/service where justified and apply a reviewed forward fix. Any database rollback requires a coordinated decision under [recovery](recovery.md), including post-checkpoint reconciliation and effective fencing; restoring only one service database can invalidate cross-service records.

If application target writes have occurred, keep the source fenced while application owners choose the approved data-recovery path. A product code rollback supplies no authority to discard those writes, delete target resources or release live allocations.

## Closure and evidence

20. Reopen admission gradually only after current grants, plan freshness, reservation ownership and exact-tuple qualification are revalidated. Unresolved jobs remain explicitly held with named reconciliation owners.
21. Record actual deployed digests, retained schema/dependency versions, worker routing, compatible/incompatible histories, native observations, alert receipt and user-journey results. Measure interruption against the accepted operating objectives.
22. Obtain receiving-owner acceptance of the recovered scope and remaining restrictions. Remove temporary access and containment only when its protection is no longer needed.

Attach the change evidence to R02/R15/R16/R24/R29/R30/R35 and Q04/Q09 in [requirements and qualification](../../implementation/requirements-and-qualification.md). Preserve the failed release's evidence and document the compatibility defect so subsequent promotion cannot repeat the same unsafe transition.
