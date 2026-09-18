# 4. Test procedure and actual execution record

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/03_Implementation/MOP_Test_and_Handover_Template.docx) · [Chapter index](README.md)

> **Source:** IT — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 9a7dd8df4a5abf6482f206cae2d074444ac6fa812bbe4bace970a4de059da370 -->
<a id="IT_04"></a>

Expected outcomes and observations are different fields. A not-run test is never a successful test.

Baseline and related records: [IK §6](../../implementation/delivery-guide/6-restricted-qualification-and-meaningful-observations.md#IK_06)  •  [WD §13](../../solutions/internal-protected-workload/13-verification-assertions-and-actual-evidence.md#WD14_S13)


<a id="source-table-41"></a>

| Record / decision | What to enter | Working response |
| --- | --- | --- |
| Test identity and scope | Execution ID, CT/addendum/W14 assertion, requirement, service class, tuple, family, topology and target. | {{IT\_TEST}} |
| Preconditions and authorization | Healthy permitted control path, endpoint identities, authorized test window, disposable data and restoration safeguards. | {{IT\_PRECONDITIONS}} |
| Procedure and expected outcome | Approved step sequence, observation points, permitted/denied behaviour and quantitative threshold with source. | {{IT\_TEST\_METHOD}} |
| Actual observations | UTC times, actual native state and endpoint results, logs/trace/configuration artifacts and integrity references. | {{IT\_TEST\_OBS}} |
| Result | Not run / passed / failed / blocked / not applicable. Not applicable needs a scoped reason and approval; never infer pass from timeout. | {{IT\_RESULT}} |
| Review and impact | Reviewer, discrepancy/defect IDs, applicability decision, evidence freshness and dependent gate. | {{IT\_TEST\_REVIEW}} |

Blank fields and unissued decisions are blockers for the affected action. Record actual evidence and authority; examples elsewhere in the library do not populate these fields.

[Previous chapter](3-as-built-deviation-and-defect-record.md) · [Chapter index](README.md) · [Next chapter](5-recovery-exercise-and-data-acceptance.md)
