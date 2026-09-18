# 47. Operating Model and Separation of Duties

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_0.docx) · [Chapter index](README.md)

> **Source:** HB10 — Draft v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 100c760003b9ff956ae369ece65c5ffe7736f6d481496d8df4c99dd6105d4190 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK HB10:354 BEGIN -->

<!-- SOURCE-BLOCK HB10:354 END -->

<!-- SOURCE-BLOCK HB10:355 BEGIN -->


<a id="source-table-355"></a>

| Role | Primary Responsibilities |
| --- | --- |
| Architecture authority | Own portable contract, invariants, implementation profiles and exceptions to architecture. |
| Security authority | Own security profiles, assurance requirements, ZIP/control policy and authorization criteria. |
| Platform engineering | Build and maintain platform adapters and native modules. |
| Network engineering | Own physical fabric, external routing and approved physical L3 domains. |
| Security-edge operations | Operate ZIP/security service, policy realization and HA/capacity. |
| Automation platform | Operate service API, pipeline, state backends, policy-as-code and evidence services. |
| Service owner | Own WSD business/service requirements and lifecycle. |
| Operations/SRE | Monitor, respond, reconcile, capacity plan and restore services. |

<!-- SOURCE-BLOCK HB10:355 END -->

<!-- SOURCE-BLOCK HB10:356 BEGIN -->


<a id="source-table-356"></a>

| GOVERNANCE PRINCIPLE<br>No single routine role should need unrestricted authority over the physical fabric, management plane, security edge, platform tenancy, and workload configuration. |
| --- |

<!-- SOURCE-BLOCK HB10:356 END -->

[Previous chapter](54-part-vi-governance-and-delivery.md) · [Chapter index](README.md) · [Next chapter](48-architecture-review-checklist.md)
