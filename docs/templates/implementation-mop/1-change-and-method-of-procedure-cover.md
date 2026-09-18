# 1. Change and method-of-procedure cover

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/03_Implementation/MOP_Test_and_Handover_Template.docx) · [Chapter index](README.md)

> **Source:** IT — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 9a7dd8df4a5abf6482f206cae2d074444ac6fa812bbe4bace970a4de059da370 -->
<a id="IT_01"></a>

Capture the actual authority and build boundary before executing any change.

Baseline and related records: [IK §1](../../implementation/delivery-guide/1-implementation-workplan-and-required-inputs.md#IK_01)  •  [ET §10](../lld/10-engineering-review-and-controlled-handoff.md#ET_10)


<a id="source-table-20"></a>

| Record / decision | What to enter | Working response |
| --- | --- | --- |
| Change identity | Change ID, purpose, site/service, environment and affected tenants. | {{IT\_CHANGE}} |
| Controlled inputs | Approved HLD/LLD revisions, package/artifact identifiers and integrity references. | {{IT\_INPUTS}} |
| Targets and ownership | Exact native resources, current writer/tool, management tuple and exclusions. | {{IT\_TARGETS}} |
| People and window | Named lead, executors, reviewers, stop authority, escalation and permitted window. | {{IT\_ROLES}} |
| Readiness and safety | Accepted prerequisites, tested recovery access and approved physical/fault-test safety scope. | {{IT\_READY}} |
| Approval and conditions | Actual authority-issued change decision, scope, conditions, expiry and evidence reference. Leave unissued until decided. | {{IT\_AUTH}} |

Blank fields and unissued decisions are blockers for the affected action. Record actual evidence and authority; examples elsewhere in the library do not populate these fields.

[Chapter index](README.md) · [Next chapter](2-repeatable-execution-step-record.md)
