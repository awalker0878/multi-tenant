# F01  |  Reference identity does not preserve tenant namespace

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Independent_Audit_v1_1.docx) · [Chapter index](README.md)

> **Source:** AUD11 — Audit of Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: cd901aaf004d45cf29ffe14ff955a0c9cf81f668be674e8d4de8c590303c62d8 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK AUD11:24 BEGIN -->

<!-- SOURCE-BLOCK AUD11:24 END -->

<!-- SOURCE-BLOCK AUD11:25 BEGIN -->

High priority • Confirmed contract ambiguity and reproduced validation gap<br>Location: Chapters 6-9 and 39; Appendix A pp57-61; validate\_package.py key() and walk\_refs()

<!-- SOURCE-BLOCK AUD11:25 END -->

<!-- SOURCE-BLOCK AUD11:26 BEGIN -->

Observed. Typed references contain kind, name and version but no namespace or immutable object identity. The validator indexes the same three fields. Moving a referenced FlowIntent or ServiceBinding into tenant-002 leaves the tenant-001 bundle accepted. Conversely, equal local names in different namespaces are treated as duplicate identities.

<!-- SOURCE-BLOCK AUD11:26 END -->

<!-- SOURCE-BLOCK AUD11:27 BEGIN -->

Why it matters. Administrative namespaces are described as isolation boundaries, but reference resolution cannot unambiguously distinguish local names or enforce every relationship across those boundaries.

<!-- SOURCE-BLOCK AUD11:27 END -->

<!-- SOURCE-BLOCK AUD11:28 BEGIN -->

Improve. Define reference scope explicitly. Use namespace plus stable UID, and distinguish immutable profile version from resource generation. Validate all ownership edges and authorize provider-shared or cross-tenant references explicitly. A globally unique naming alternative must be declared, not inferred.

<!-- SOURCE-BLOCK AUD11:28 END -->

<!-- SOURCE-BLOCK AUD11:29 BEGIN -->

Close when. Two tenants can reuse local names without collisions; foreign flows, bindings and objects are denied unless an explicit scoped grant permits them.

<!-- SOURCE-BLOCK AUD11:29 END -->

<!-- SOURCE-BLOCK AUD11:30 BEGIN -->

Owner: Architecture and automation  \|  Local probes: M07, M08, M09

<!-- SOURCE-BLOCK AUD11:30 END -->

[Previous chapter](02-scope-method-and-confirmed-improvements.md) · [Chapter index](README.md) · [Next chapter](04-f02-cross-object-consistency-checks-do-not-cover-the-complete-graph.md)
