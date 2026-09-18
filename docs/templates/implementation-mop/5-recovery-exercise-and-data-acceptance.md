# 5. Recovery exercise and data acceptance

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/03_Implementation/MOP_Test_and_Handover_Template.docx) · [Chapter index](README.md)

> **Source:** IT — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 9a7dd8df4a5abf6482f206cae2d074444ac6fa812bbe4bace970a4de059da370 -->
<!-- SOURCE-BLOCK IT:45 BEGIN -->

<a id="IT_05"></a>

<!-- SOURCE-BLOCK IT:45 END -->

<!-- SOURCE-BLOCK IT:46 BEGIN -->

Measure the recovery of the defined service, not just a restore job.

<!-- SOURCE-BLOCK IT:46 END -->

<!-- SOURCE-BLOCK IT:47 BEGIN -->

Baseline and related records: [SVC §6](../../architecture/shared-services/6-failure-recovery-migration-and-failback-topology.md#SVC_s_006)  •  [IK §9](../../implementation/delivery-guide/9-operational-handover-recovery-migration-and-retirement.md#IK_09)

<!-- SOURCE-BLOCK IT:47 END -->

<!-- SOURCE-BLOCK IT:48 BEGIN -->


<a id="source-table-48"></a>

| Record / decision | What to enter | Working response |
| --- | --- | --- |
| Recovery scope | Exercise ID, failure scenario, failed/surviving dependencies and approved test authority. | {{IT\_REC\_SCOPE}} |
| Objectives and consistency | Accepted RTO/RPO measurement boundaries, actual last consistent data point, start/end milestones and exclusions. | {{IT\_REC\_TARGET}} |
| Authority and fencing | Who may promote the writer; proof the old writer cannot conflict; key/catalogue/identity custody. | {{IT\_FENCE}} |
| Restore execution | Actual backup/data set, isolated target, native steps, integrity/application checks and useful recovered-data evidence. | {{IT\_RESTORE}} |
| Reconnection and failback | Authorized activation, DNS/exposure, reverse transfer or failback feasibility after new writes. | {{IT\_FAILBACK}} |
| Outcome and improvements | Achieved times/consistency/security, owner acceptance, defects and runbook changes. | {{IT\_REC\_RESULT}} |

<!-- SOURCE-BLOCK IT:48 END -->

<!-- SOURCE-BLOCK IT:49 BEGIN -->

<!-- SOURCE-BLOCK IT:49 END -->

<!-- SOURCE-BLOCK IT:50 BEGIN -->

Blank fields and unissued decisions are blockers for the affected action. Record actual evidence and authority; examples elsewhere in the library do not populate these fields.

<!-- SOURCE-BLOCK IT:50 END -->

<!-- SOURCE-BLOCK IT:51 BEGIN -->

<!-- SOURCE-BLOCK IT:51 END -->

[Previous chapter](4-test-procedure-and-actual-execution-record.md) · [Chapter index](README.md) · [Next chapter](6-operational-handover-and-initial-readiness.md)
