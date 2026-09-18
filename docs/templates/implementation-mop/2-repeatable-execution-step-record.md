# 2. Repeatable execution-step record

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/03_Implementation/MOP_Test_and_Handover_Template.docx) · [Chapter index](README.md)

> **Source:** IT — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 9a7dd8df4a5abf6482f206cae2d074444ac6fa812bbe4bace970a4de059da370 -->
<!-- SOURCE-BLOCK IT:24 BEGIN -->

<a id="IT_02"></a>

<!-- SOURCE-BLOCK IT:24 END -->

<!-- SOURCE-BLOCK IT:25 BEGIN -->

Repeat this page for every independently controlled action; do not bury destructive work inside a generic script step.

<!-- SOURCE-BLOCK IT:25 END -->

<!-- SOURCE-BLOCK IT:26 BEGIN -->

Baseline and related records: [IK §2](../../implementation/delivery-guide/2-work-packages-dependencies-and-authority.md#IK_02)  •  [IK §8](../../implementation/delivery-guide/8-interrupted-work-brownfield-adoption-and-change.md#IK_08)

<!-- SOURCE-BLOCK IT:26 END -->

<!-- SOURCE-BLOCK IT:27 BEGIN -->


<a id="source-table-27"></a>

| Record / decision | What to enter | Working response |
| --- | --- | --- |
| Step and dependency | Step ID, work package, target, prerequisite receipts and single authoritative executor. | {{IT\_STEP}} |
| Action and artifact | Exact approved command/configuration or installer procedure, version, parameter source and protected credential reference. | {{IT\_ACTION}} |
| Expected result | Observable native state, permitted effects, completion signal and maximum wait/retry policy. | {{IT\_EXPECTED}} |
| Stop and recovery | Conditions to stop, resource state to preserve, data impact, supported rollback or forward-repair action and authority. | {{IT\_STOP}} |
| Observed execution | Operator, UTC start/end, native task ID, actual output reference and confirmed side effects. No secrets. | {{IT\_OBSERVED}} |
| Disposition | Completed, failed, blocked or unknown; reviewer, next authorized step and evidence record. | {{IT\_DISPOSITION}} |

<!-- SOURCE-BLOCK IT:27 END -->

<!-- SOURCE-BLOCK IT:28 BEGIN -->

<!-- SOURCE-BLOCK IT:28 END -->

<!-- SOURCE-BLOCK IT:29 BEGIN -->

Blank fields and unissued decisions are blockers for the affected action. Record actual evidence and authority; examples elsewhere in the library do not populate these fields.

<!-- SOURCE-BLOCK IT:29 END -->

<!-- SOURCE-BLOCK IT:30 BEGIN -->

<!-- SOURCE-BLOCK IT:30 END -->

[Previous chapter](1-change-and-method-of-procedure-cover.md) · [Chapter index](README.md) · [Next chapter](3-as-built-deviation-and-defect-record.md)
