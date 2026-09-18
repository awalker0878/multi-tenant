# F20  |  Add one end-to-end service materialization contract

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Independent_Audit_v1_1.docx) · [Chapter index](README.md)

> **Source:** AUD11 — Audit of Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: cd901aaf004d45cf29ffe14ff955a0c9cf81f668be674e8d4de8c590303c62d8 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
Medium priority • Proposed engineering strengthening<br>Location: Chapters 8, 22-31 and 61; WSD request examples

Observed. Compute, storage, images, reliability and application responsibilities are now covered. The reference WSD predominantly selects profiles and network/service references; it does not demonstrate a full resource-demand and workload-to-network/storage realization sequence.

Why it matters. Teams still need to decide how quota/reservation inputs, VM or workload counts, attachments and application-readiness evidence connect to WSD lifecycle.

Improve. Add one vertical slice: two workloads, OZ/RZ networks, storage and backup demand, approved identities, reservation result, compiled graph, provider realization mapping, application handover and retirement. Keep provider IDs in status and implementation artifacts.

Close when. Every offered capability is represented in intent or a declared linked service contract and has an owner, realization, capacity basis and evidence.

Owner: Hosting service and platform architecture

[Previous chapter](21-f19-document-fencing-and-pre-post-activation-verification-explicitly.md) · [Chapter index](README.md) · [Next chapter](23-f21-complete-protocol-profile-and-standards-adoption-traceability.md)
