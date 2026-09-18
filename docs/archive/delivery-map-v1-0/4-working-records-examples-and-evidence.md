# 4. Working records, examples and evidence

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/07_Quality/prior_v1_0/00_Delivery_Map.docx) · [Chapter index](README.md)

> **Source:** DEL10 — Delivery kits v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: e332c1b37e63439169adf8b105573577fa1ea61bf32f6c3ba383dd69d83a788b -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<a id="DEL_04"></a>

Use one controlled site record set; do not maintain independent conflicting versions in every team. The three workbooks are working registers. Shared CSVs are reference snapshots unless explicitly designated as the project record.

Baseline and related records: [RA §28](../../architecture/reference/28-architecture-acceptance-and-verification.md#RA_s_028)  •  [WD §13](../../solutions/internal-protected-workload/13-verification-assertions-and-actual-evidence.md#WD14_S13)


<a id="source-table-47"></a>

| Material | Treatment | Where to work |
| --- | --- | --- |
| Frozen reference documents | Read and cite; retain original bytes and record variations separately. | 05\_Reference\_v1\_4/ |
| Kit guides | Instructions, quality criteria and boundary conditions. | Each role directory |
| Word templates | Copy for a named project; complete the tagged response controls and attach actual diagrams. | HLD, LLD and MOP/test/handover templates |
| Workbooks | Enter actual owners, approved values and evidence. Example-labelled sheets are not site allocations. | Architecture\_Registers, Engineering\_Schedules, Implementation\_Tracker |
| Runbooks | Adapt to the reviewed LLD, product tuple and approved change window before execution. | 03\_Implementation/runbooks/ |
| Local tools | Package/link checking and a limited offline Terraform plan review; no infrastructure access. | 06\_Tools/ |
| Evidence | Store approved artifacts in the controlled repository; record IDs, hashes, scope and collection times. | Implementation evidence register; not unprotected logs in email. |

## Status discipline

Separate design completion, engineering review, installation, technical qualification, operational readiness and authorization. “Not run”, “unknown” and “not applicable” are distinct. A plan, receipt or signature-reference string is not proof that the underlying control or authority exists.

[Previous chapter](3-acceptance-gates-and-restricted-qualification.md) · [Chapter index](README.md) · [Next chapter](5-review-sequence-and-change-control.md)
