# 7. Retire live service separately from retained data

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/03_Implementation/Operations_Recovery_and_Transition_Playbook.docx) · [Chapter index](README.md)

> **Source:** OPS — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: d935614ed1639f56859dfe29bc226af4cfced35bafeb7d544440577ddaa95a09 -->
<a id="OPS_07"></a>

A retired WSD can leave legitimate protected copies. Make those obligations explicit rather than declaring all data destroyed because live resources were removed.

Design basis and related records: [RA §27](../../architecture/reference/27-recovery-migration-and-retirement.md#RA_s_027)  •  [SVC §4](../../architecture/shared-services/4-storage-copies-and-retained-data-ownership.md#SVC_s_004)  •  [IK §9](../../implementation/delivery-guide/9-operational-handover-recovery-migration-and-retirement.md#IK_09)


<a id="source-table-79"></a>

| Object / obligation | Retirement decision | Evidence of safe completion |
| --- | --- | --- |
| Shared domains and services | Remove only the departing consumer’s authority; retain objects with other approved dependents. | Dependency review and absence of unintended impact on remaining consumers. |
| Routes, policies, names and addresses | Withdraw obsolete live access, reconcile caches/leases/sessions and quarantine reuse. | Actual residual scan and ownership history, not only a destroy command’s exit status. |
| Snapshots, replicas and backups | Reconcile retention, holds, approved copy locations and data owner. | Known copy inventory, current access boundary and explicit disposal/review date. |
| Keys and recovery catalogue | Retain what authorized copies still require; separate use, recovery and destruction authority. | Verified recoverability and custody until approved final disposal. |
| Media and resource reuse | Use the applicable approved sanitization method and qualified handling process. | Method, scope, verification and exceptions before reassignment. A deleted volume record is insufficient. |

A retained-copy record includes former WSD identity, copy identity, category/location, owner, hold/retention, key/catalogue dependencies, authorized recovery access, review date and final disposition authority. It does not retain unnecessary live tenant access merely because a backup still exists.

If an offline copy, supplier-held media or shared key prevents immediate disposal proof, record the unresolved obligation and its owner. Do not label total destruction complete. Conversely, do not delete a shared key to satisfy one workload’s retirement while other retained data still depends on it.

Physical media handling and equipment disposal use the organization’s approved process and qualified personnel. This playbook records scope, authority and evidence; it does not replace handling or safety procedures.

Continue with: [IT §8](../../templates/implementation-mop/8-migration-retirement-and-retained-data.md#IT_08)  •  [OPS §8](8-accept-operational-responsibility-for-the-delivered-scope.md#OPS_08)

[Previous chapter](6-migrate-and-fail-back-without-conflicting-writers.md) · [Chapter index](README.md) · [Next chapter](8-accept-operational-responsibility-for-the-delivered-scope.md)
