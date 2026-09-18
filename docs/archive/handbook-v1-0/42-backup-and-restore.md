# 42. Backup and Restore

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_0.docx) · [Chapter index](README.md)

> **Source:** HB10 — Draft v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 100c760003b9ff956ae369ece65c5ffe7736f6d481496d8df4c99dd6105d4190 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
Backup is a service, not a routing domain. The backup data path and backup management path must be separated. Workloads should reach only the approved backup data endpoint/proxy/agent service; backup administration belongs on the management trust plane.


<a id="source-table-319"></a>

| BKP-001 | Backup consumers SHALL NOT receive connectivity to backup management interfaces merely because they consume backup service. |
| --- | --- |


<a id="source-table-320"></a>

| BKP-002 | Restore workflows SHALL enforce the same tenant, security-zone, identity, and evidence controls as backup ingestion. |
| --- | --- |

[Previous chapter](41-high-availability-and-failure-behaviour.md) · [Chapter index](README.md) · [Next chapter](43-incident-response-and-containment.md)
