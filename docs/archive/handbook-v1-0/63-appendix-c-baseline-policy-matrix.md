# Appendix C — Baseline Policy Matrix

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_0.docx) · [Chapter index](README.md)

> **Source:** HB10 — Draft v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 100c760003b9ff956ae369ece65c5ffe7736f6d481496d8df4c99dd6105d4190 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.

<a id="source-table-423"></a>

| Source | Destination | Class | Default | Exception / Allowed Mechanism |
| --- | --- | --- | --- | --- |
| Tenant A | Tenant B | Any | DENY | Explicit approved inter-tenant service only |
| WSD A | WSD B | Same Security Domain | DENY by default | Approved microsegmentation flow |
| OZ | RZ | Inter-zone | DENY by default | Explicit ZIP flow |
| RZ | Public | External | DENY | Approved egress service only |
| Public | Internal workload | Ingress | DENY | Approved PAZ/ingress service only |
| Workload | MZ/OOB | Management | DENY | No normal exception |
| Workload | DNS/NTP/identity | Service binding | DENY unless bound | Approved Service Binding |
| Workload | Backup management | Management | DENY | No normal exception |
| Workload | Backup data service | Service binding | DENY unless bound | Approved backup profile |
| Tenant automation | Physical fabric | Control plane | DENY | Foundation identity only |

[Previous chapter](62-appendix-b-terraform-root-and-module-patterns.md) · [Chapter index](README.md) · [Next chapter](64-appendix-d-conformance-test-catalogue.md)
