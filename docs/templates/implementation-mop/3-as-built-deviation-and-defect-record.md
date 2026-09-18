# 3. As-built, deviation and defect record

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/03_Implementation/MOP_Test_and_Handover_Template.docx) · [Chapter index](README.md)

> **Source:** IT — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 9a7dd8df4a5abf6482f206cae2d074444ac6fa812bbe4bace970a4de059da370 -->
<a id="IT_03"></a>

Record what exists, not merely what the deployment intended to create.

Baseline and related records: [ET §10](../lld/10-engineering-review-and-controlled-handoff.md#ET_10)  •  [IK §8](../../implementation/delivery-guide/8-interrupted-work-brownfield-adoption-and-change.md#IK_08)


<a id="source-table-34"></a>

| Record / decision | What to enter | Working response |
| --- | --- | --- |
| As-built identity | Resource ID/type, owner, tenant/WSD/domain/site, exact release and current authoritative tool. | {{IT\_ASBUILT}} |
| Observed configuration | Actual interfaces/routes/policy, placement, data attachments, service memberships and configuration digest. | {{IT\_CONFIG}} |
| Difference from design | Expected design record versus actual state; affected boundaries and dependent resources. | {{IT\_DEVIATION}} |
| Defect record | Defect ID, observed facts, service/security impact, severity rationale, owner and remediation deadline. | {{IT\_DEFECT}} |
| Decision and retest | Accepted variation or correction reference, residual risk authority and relevant re-verification. | {{IT\_RETEST}} |
| Closure | Actual evidence and reviewer; retained issue or confirmed resolution with timestamps. | {{IT\_CLOSE}} |

Blank fields and unissued decisions are blockers for the affected action. Record actual evidence and authority; examples elsewhere in the library do not populate these fields.

[Previous chapter](2-repeatable-execution-step-record.md) · [Chapter index](README.md) · [Next chapter](4-test-procedure-and-actual-execution-record.md)
