# Restore the control plane

This procedure restores the product's control services after loss or corruption while preserving the relationship between accepted plans, native effects, workflow histories and evidence. The recovery policy and recovery-point selection rules are in [recovery](recovery.md). Application datasets have their own recovery boundaries; restoring the control plane does not restore them.

## Ownership and inputs

The incident commander authorizes the restoration scope. SRE coordinates the restore; persistence, IAM, lifecycle and assurance owners perform their respective checks. Native resource owners independently establish platform outcomes. Application owners decide any recovery that affects accepted application data. Use the escalation and receiving-owner responsibilities in [support](../support.md).

Required inputs are the incident ID, affected environment, release manifest, configuration revision, dependency BOM, backup catalogue, available recovery points, key/trust recovery references, audit records and active-operation inventory. Include source/target writer status, reservation ownership and the last trustworthy evidence watermarks.

Use the recorded release-specific restore actions for the selected products. No product restore command or automated restore endpoint is established by this document; missing executable procedures, unavailable keys or an unverified backup are reasons to hold recovery, not to improvise a success result.

## Prerequisites

- Confirm the approved recovery location satisfies the deployment's residency, trust and access requirements.
- Obtain independently controlled access to backups, encryption keys and trust configuration without relying solely on the failed control plane.
- Record the accepted recovery objectives for this environment and the incident start time; compare measured results at closure without inventing target values.
- Select consistent checkpoints or documented per-system watermarks and identify the possible gap between restored state and actual native work.
- Confirm the recovery environment can deny native mutation paths while allowing approved read-only observation.
- Assign a recorder and a rollback/containment decision owner before modifying any recovered system.

## Contain and preserve

1. SRE stops new user admission, dispatch and scheduled execution in the affected scope. Preserve accessible workflow histories, operation journals, audit and native request identifiers before replacing infrastructure.
2. Lifecycle lists admitted jobs, dispatched operations and allocations that may still be active. Include jobs absent from a restored database when independent audit or native observations identify them.
3. IAM and native owners invalidate old execution authority and establish effective containment of previous workers. Revoke cached native credentials or isolate their native paths as required by the selected platform.
4. Independently verify that a partitioned or restarted old worker cannot issue another write. A stopped task queue, expired lease or incremented database epoch alone is insufficient evidence.
5. Record any operation still running inside a native platform after worker containment. Preserve its resource hold and observe it; containment of the caller does not cancel a previously accepted native operation.
6. Take protected copies of available damaged/current state and record checksums, timestamps, custody and retention. Preserve forensic material before cleanup.

Expected observation: the incident has one accountable coordinator, new work is held, old-worker writes are effectively blocked, and every identified in-flight operation has a tracked disposition. Stop if the containment boundary cannot be demonstrated.

## Restore in quarantine

7. Recover the trust, key and identity dependencies needed to decrypt and authenticate restored state. Reconcile post-backup revocations before allowing restored identities to act.
8. Provision the recorded compatible dependency and application versions in the isolated environment. Keep schedulers, outbox dispatchers, event consumers capable of triggering work and mutating worker pools disabled.
9. Restore each context's database through its approved procedure, including command receipts, outbox/inbox, immutable plans, grants/revocations, lifecycle operations and reservations. Record recovery point and integrity observations separately for each store.
10. Restore Temporal persistence and required visibility data at the selected recoverable point. Preserve history and namespace identity; do not start replacement workflows merely because a projection lacks a job.
11. Restore protected evidence bytes, versions and metadata, IaC state and locks, and the required broker replay/retention state. Restore configuration by its reviewed revision rather than copying secrets into evidence.
12. Verify database integrity, key access, evidence digests, object references, state ownership and dependency health. A healthy process or matching record count does not establish complete restoration.

Expected observation: required state is readable under restricted authority, each store has an explicit recovery point, and no resumed dispatcher or restored worker can mutate native systems.

## Reconcile before resuming

13. Lifecycle compares admission records, operation journals and Temporal histories using stable job/workflow/operation identifiers. Record missing, duplicated and newer-than-backup references without inventing execution history.
14. Service owners reconcile outbox/inbox receipts and broker watermarks. Rebuild disposable projections from authoritative records only after identifying replay effects and verifying idempotency; replay cannot recreate approval or redispatch a native write.
15. Native owners independently observe every operation that could have reached a platform or shared-service owner. Classify it as `not_started`, `confirmed_failed`, `confirmed_succeeded` or `outcome_unknown`, with the observation source and timestamp.
16. Retain resource holds for `outcome_unknown`. Use the bounded reconciliation behavior in the [lifecycle specification](../../services/lifecycle.md); never retry a possible write solely because the ledger predates it.
17. Reconcile local reservations and native bindings with authoritative IPAM, capacity, storage and other owners. Expired local leases do not justify releasing allocations still in use or creating competing ownership.
18. Assurance verifies required evidence bytes, provenance, qualification validity and affected release bindings. Quarantine missing or altered evidence and withhold dependent support/admission claims.
19. Governance re-establishes current grants, revocations, exact approvals and time validity using independent records. Reissue reviewed authority where currency cannot be proven; do not resurrect approval from an old snapshot.
20. Lifecycle revalidates plan freshness, inventory generation, commissioned endpoints, reservations and current exact-tuple qualification. Establish new effective execution fencing only after old authority is demonstrably blocked.

Expected observation: reconciled operations have attributable facts, unresolved operations remain held, and restored authority matches current decisions rather than historical permissions.

## Resume and verify

21. Admit only reviewed workflows whose histories are compatible with the restored server, SDK and worker versions. Keep incompatible histories quarantined for lifecycle engineering; consult [upgrade](upgrade.md) for version-routing constraints.
22. Enable non-mutating queries and projections first. Verify tenant isolation, authorized reads, denied cross-tenant access and honest display of held or incomplete jobs.
23. Restore telemetry and exercise alert delivery using [observability](../observability.md) and [handle alert](handle-alert.md). Confirm named on-call receipt before reopening consequential operations.
24. Resume a bounded approved scope, observe its journal, authority checks and independent postconditions, and then expand admission under the incident commander's decision.
25. For a migrated application, identify whether the target accepted writes. If it did, keep the old source fenced and obtain an approved source-return or forward-recovery decision; never restart a stale source as a shortcut.

Expected observation: reopened work is independently verified, authority holds remain effective, tenant boundaries hold, and application checks support the claimed restoration scope.

## Stop, escalation and closure

Stop new effects for missing keys, unresolved containment, incompatible histories, evidence-integrity failure, irreconcilable ownership or uncertain application writer state. Preserve running native observations and escalate to the relevant owners; a control-plane recovery deadline does not authorize unsafe write admission.

If restoration fails, keep the recovery environment isolated and preserve the attempt. Select a different validated recovery point or repair forward under an explicit decision. Do not merge diverging restored databases or silently discard records beyond the earlier checkpoint.

The closure record contains restore actions and actors, artifact/configuration digests, per-store recovery points, key/trust verification, containment proof, reconciliation decisions, retained holds, denied-access checks, application observations and alert receipt. Include measured data loss and recovery duration, the accepted remaining restrictions and named owners for follow-up.

Attach the record to Q09 and the affected R15/R16/R24/R29/R30/R35 controls in [requirements and qualification](../../implementation/requirements-and-qualification.md). A successful rehearsal supports only its exercised environment and failure scope.
