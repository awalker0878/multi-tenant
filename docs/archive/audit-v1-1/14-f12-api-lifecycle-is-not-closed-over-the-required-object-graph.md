# F12  |  API lifecycle is not closed over the required object graph

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Independent_Audit_v1_1.docx) · [Chapter index](README.md)

> **Source:** AUD11 — Audit of Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: cd901aaf004d45cf29ffe14ff955a0c9cf81f668be674e8d4de8c590303c62d8 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK AUD11:106 BEGIN -->

<!-- SOURCE-BLOCK AUD11:106 END -->

<!-- SOURCE-BLOCK AUD11:107 BEGIN -->

High priority • Design-completeness gap<br>Location: Chapters 8, 39-41; Appendix A p61; api\_surface.json

<!-- SOURCE-BLOCK AUD11:107 END -->

<!-- SOURCE-BLOCK AUD11:108 BEGIN -->

Observed. The nine proposed routes mainly create/update WSDs and read operations/capabilities/evidence. WSDs reference FlowIntent and ServiceBinding objects that reference the WSD back. The published surface does not define bundle submission, draft references, or creation ordering for this graph.

<!-- SOURCE-BLOCK AUD11:108 END -->

<!-- SOURCE-BLOCK AUD11:109 BEGIN -->

Why it matters. A fresh consumer cannot determine how to submit a complete new WSD without pre-existing referenced objects or undocumented provisioning steps.

<!-- SOURCE-BLOCK AUD11:109 END -->

<!-- SOURCE-BLOCK AUD11:110 BEGIN -->

Improve. Choose an atomic desired-graph/bundle request or a staged draft-object workflow. Resolve cycles within the staged graph before any infrastructure effects. Specify typed responses/errors, ownership, concurrency, cancellation and deletion behavior.

<!-- SOURCE-BLOCK AUD11:110 END -->

<!-- SOURCE-BLOCK AUD11:111 BEGIN -->

Close when. Create, update and retire a new multi-zone WSD from an empty tenant namespace using only the published contract; no manual object insertion or hidden API is needed.

<!-- SOURCE-BLOCK AUD11:111 END -->

<!-- SOURCE-BLOCK AUD11:112 BEGIN -->

Owner: Service API and controller architecture

<!-- SOURCE-BLOCK AUD11:112 END -->

<!-- SOURCE-BLOCK AUD11:113 BEGIN -->

<!-- SOURCE-BLOCK AUD11:113 END -->

[Previous chapter](13-f11-placementprofile-does-not-express-required-location-distinctions.md) · [Chapter index](README.md) · [Next chapter](15-f13-breaking-change-policy-and-api-version-naming-disagree.md)
