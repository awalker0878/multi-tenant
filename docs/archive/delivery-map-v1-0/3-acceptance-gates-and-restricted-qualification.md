# 3. Acceptance gates and restricted qualification

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/07_Quality/prior_v1_0/00_Delivery_Map.docx) · [Chapter index](README.md)

> **Source:** DEL10 — Delivery kits v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: e332c1b37e63439169adf8b105573577fa1ea61bf32f6c3ba383dd69d83a788b -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK DEL10:37 BEGIN -->

<a id="DEL_03"></a>

<!-- SOURCE-BLOCK DEL10:37 END -->

<!-- SOURCE-BLOCK DEL10:38 BEGIN -->

Gate numbers are identifiers, not an automatic chronological ladder. v1.4 requires applicable initial G4 readiness before G3 production activation. Qualification can use a separately authorized non-production fixture before G2 is complete.

<!-- SOURCE-BLOCK DEL10:38 END -->

<!-- SOURCE-BLOCK DEL10:39 BEGIN -->

Baseline and related records: [WD §9](../../solutions/internal-protected-workload/9-build-sequence-with-explicit-acceptance-dependencies.md#WD14_S09)  •  [QUAL §5](../../assurance/site-qualification/5-qualification-stages-applicability-and-evidence.md#QUAL_s_005)

<!-- SOURCE-BLOCK DEL10:39 END -->

<!-- SOURCE-BLOCK DEL10:40 BEGIN -->


<a id="source-table-40"></a>

| Decision | Required preceding condition | Prohibited shortcut |
| --- | --- | --- |
| G0 — Design adoption | None | No build authorization is implied by document acceptance. |
| G1 — Foundation acceptance | G0 for affected scope | A reachable API is not a commissioned platform. |
| Restricted fixture — Non-production test permission | G1; installed safeguarded candidate resources | May generate qualification evidence; cannot authorize production use. |
| G2 — Platform and shared-service qualification | G0/G1; authorized fixture; applicable observed tests | Installed resources and provider availability are not qualification. |
| G4 initial — Operational/recovery readiness | Relevant qualified platform/service | Must precede the production service promise; not deferred until after G3. |
| G3 — Production activation | G0, G1, G2, applicable G4 initial; valid authority | Neither a workbook nor a Terraform exit code grants authority. |
| G4 continuing — Continuing operations and reacceptance | Activated service; approved cadence and change triggers | Historical approval is not evidence for changed topology. |

<!-- SOURCE-BLOCK DEL10:40 END -->

<!-- SOURCE-BLOCK DEL10:41 BEGIN -->

<!-- SOURCE-BLOCK DEL10:41 END -->

<!-- SOURCE-BLOCK DEL10:42 BEGIN -->

A gate record names the actual service/site/version scope, decision authority, evidence and conditions. Failed or missing evidence cannot be converted into acceptance merely by changing a spreadsheet status. Applicability decisions also require an accountable rationale.

<!-- SOURCE-BLOCK DEL10:42 END -->

<!-- SOURCE-BLOCK DEL10:43 BEGIN -->

<!-- SOURCE-BLOCK DEL10:43 END -->

[Previous chapter](2-deliverable-ownership-and-handoffs.md) · [Chapter index](README.md) · [Next chapter](4-working-records-examples-and-evidence.md)
