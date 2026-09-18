# 5. Concurrency, ownership and failed execution

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/04_Provisioning_and_Commissioning_v1_4.docx) · [Chapter index](README.md)

> **Source:** PROV — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 483df77cff70166fbdfdf711135efa3beeecc8fe1015a58290cbebff5b80bdfd -->
<a id="__RefHeading___Toc7820_1525915568"></a>
<a id="PROV_s_005"></a>

Parent architecture: [RA §24](../../architecture/reference/24-terraform-across-the-vendor-stacks.md#RA_s_024)  •  [RA §25](../../architecture/reference/25-change-brownfield-adoption-and-configuration-ownership.md#RA_s_025)

One authoritative tool/owner controls a native resource at a time. State boundaries help organize that ownership, but a lock on one state file is not a lock over every API, shared gateway or external address service involved in a delivery. Shared edge or service objects need an explicitly serialized owner where concurrent changes could conflict. Independent per-WSD resources can proceed concurrently only within accepted shared limits.


<a id="source-table-68"></a>

| Failure or race | Required operational decision | Evidence before resumption |
| --- | --- | --- |
| Two runs target one native object | Stop the competing writer; preserve authoritative desired state and current native state. | Assigned owner, completed/active tasks and matching accepted plan. |
| Executor loses network or lease | Do not assume its native API task stopped. Discover task/resource outcome through the authorized owner. | Task identity, eventual completion/failure and any late side effects. |
| Credential revoked mid-operation | Prevent new activity; account for already accepted work at the target. | Actual native task results and scope of still-valid sessions. |
| Old plan versus new policy/state | Re-evaluate against current approval, capacity, policy and configuration. | A fresh compatible change record, not a reused unrelated approval. |
| State backend unavailable/corrupt | Pause untracked changes; recover protected state/configuration and reconcile real objects. | Known writer status, ownership and native resource comparison. |
| Incident containment conflicts with normal desired state | Containment remains higher priority until the incident authority releases it. | Approved override/release and reconciled source, rules and sessions. |

An ambiguous outcome is a controlled stop point, not permission to guess. Query by stable native identity and operation correlation, examine outstanding tasks, and determine whether the intended resource already exists. Where the target cannot provide adequate observation or cancellation, the supported recovery procedure and residual limitations are part of the service class. Do not claim exactly-once multi-system changes from a single successful pipeline run.

Compensation is resource-specific. Releasing an unused reservation can be safe; deleting a newly written volume may not be. Removing a failed tenant’s private policy object differs from removing a shared edge context. The accepted recovery record identifies data impact, shared dependencies, approval authority and the checks required before retries. This is an operational strategy; no particular transaction engine is mandated.

Related engineering: [Copy ownership and retained data](../../architecture/shared-services/4-storage-copies-and-retained-data-ownership.md#SVC_s_004)  •  [Incident and operational authority](../../assurance/site-qualification/7-operating-accountability-handover-and-change.md#QUAL_s_007)

[Previous chapter](4-end-to-end-fixture-provisioning-and-safe-activation.md) · [Chapter index](README.md) · [Next chapter](6-brownfield-adoption-growth-and-retirement.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0016 — Assign one authoritative writer per native object and sensitive subresource](../../adr/0016-assign-one-authoritative-writer-per-native-object-and-sensitive-subresource.md)
- [ADR-0031 — Discover uncertain native outcomes instead of blind replay or rollback](../../adr/0031-discover-uncertain-native-outcomes-instead-of-blind-replay-or-rollback.md)
- [ADR-0032 — Keep incident containment above routine reconciliation](../../adr/0032-keep-incident-containment-above-routine-reconciliation.md)

<!-- END GENERATED DECISION LINKS -->
