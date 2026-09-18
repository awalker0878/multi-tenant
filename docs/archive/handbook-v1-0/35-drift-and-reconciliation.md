# 35. Drift and Reconciliation

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_0.docx) · [Chapter index](README.md)

> **Source:** HB10 — Draft v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 100c760003b9ff956ae369ece65c5ffe7736f6d481496d8df4c99dd6105d4190 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
Continuous reconciliation compares declared intent, Terraform state, platform state, route/security policy, and evidence. Manual changes should be detected and either reverted or converted into an approved change. Drift is not merely a configuration hygiene issue; it can invalidate authorization evidence.


<a id="source-table-278"></a>

| DRIFT-001 | Security-significant drift SHALL generate an actionable event and SHALL affect the compliance/authorization state of the WSD until resolved or accepted. |
| --- | --- |


<a id="source-table-279"></a>

| DRIFT-002 | Emergency changes SHALL be reconciled back into the source of truth after the incident or maintenance action. |
| --- | --- |

[Previous chapter](34-ci-cd-and-change-gates.md) · [Chapter index](README.md) · [Next chapter](42-part-v-assurance-testing-and-operations.md)
