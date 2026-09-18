# 7. Gate decision and production activation

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/03_Implementation/MOP_Test_and_Handover_Template.docx) · [Chapter index](README.md)

> **Source:** IT — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 9a7dd8df4a5abf6482f206cae2d074444ac6fa812bbe4bace970a4de059da370 -->
<a id="IT_07"></a>

This is a decision record, not a calculated approval. Check the exact service scope and freshness.

Baseline and related records: [DEL §3](../../governance/delivery-framework/3-apply-gate-dependencies-rather-than-numerical-order.md#DEL_03)  •  [WD §9](../../solutions/internal-protected-workload/9-build-sequence-with-explicit-acceptance-dependencies.md#WD14_S09)


<a id="source-table-62"></a>

| Record / decision | What to enter | Working response |
| --- | --- | --- |
| Decision requested | Gate ID, service/site/tuple/revision, requested action and accountable authority. | {{IT\_GATE}} |
| Prerequisite decisions | G0/G1/G2 and applicable G4 initial references; restricted-test permission is not production permission. | {{IT\_PREREQ}} |
| Evidence and blockers | Current test/restore/ownership records, unresolved findings, accepted exceptions and service restrictions. | {{IT\_GATE\_EVIDENCE}} |
| Operating authority | Separately attributable valid authorization scope/conditions; do not substitute a test report or workbook colour. | {{IT\_OPERATE}} |
| Actual decision | Not issued / approved / rejected / conditional / suspended; issuer, timestamp, scope and review/expiry. | {{IT\_GATE\_DECISION}} |
| Activation and verification | Permitted exposure change, executor, post-activation observations and safe withdrawal result if needed. | {{IT\_ACTIVATION}} |

Blank fields and unissued decisions are blockers for the affected action. Record actual evidence and authority; examples elsewhere in the library do not populate these fields.

[Previous chapter](6-operational-handover-and-initial-readiness.md) · [Chapter index](README.md) · [Next chapter](8-migration-retirement-and-retained-data.md)
