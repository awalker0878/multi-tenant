# F02  |  Cross-object consistency checks do not cover the complete graph

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Independent_Audit_v1_1.docx) · [Chapter index](README.md)

> **Source:** AUD11 — Audit of Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: cd901aaf004d45cf29ffe14ff955a0c9cf81f668be674e8d4de8c590303c62d8 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK AUD11:31 BEGIN -->

<!-- SOURCE-BLOCK AUD11:31 END -->

<!-- SOURCE-BLOCK AUD11:32 BEGIN -->

High priority • Reproduced selected-semantic gaps<br>Location: Chapters 11, 17-20 and 40; validate\_bundle()

<!-- SOURCE-BLOCK AUD11:32 END -->

<!-- SOURCE-BLOCK AUD11:33 BEGIN -->

Observed. The supplied validator accepts removal of a mandatory service binding, a public Exposure naming an external domain different from its ZIP endpoint, and an EdgeAttachment whose instance is not on its declared boundary. Referenced objects exist, but the relationships disagree.

<!-- SOURCE-BLOCK AUD11:33 END -->

<!-- SOURCE-BLOCK AUD11:34 BEGIN -->

Why it matters. Existence checks alone can label an internally contradictory intended topology consistent. Native adapters would have to invent missing interpretations.

<!-- SOURCE-BLOCK AUD11:34 END -->

<!-- SOURCE-BLOCK AUD11:35 BEGIN -->

Improve. Add graph invariants for WSD-to-flow ownership, required bindings, instance/domain membership, edge-to-ZIP endpoint matching, exposure-to-external-domain matching and shared-resource deletion. Declare which component evaluates each invariant.

<!-- SOURCE-BLOCK AUD11:35 END -->

<!-- SOURCE-BLOCK AUD11:36 BEGIN -->

Close when. Each inconsistent graph is rejected before reservations or provider actions; a valid cross-zone graph still passes.

<!-- SOURCE-BLOCK AUD11:36 END -->

<!-- SOURCE-BLOCK AUD11:37 BEGIN -->

Owner: Automation and network/security engineering  \|  Local probes: M18, M22, M23

<!-- SOURCE-BLOCK AUD11:37 END -->

<!-- SOURCE-BLOCK AUD11:38 BEGIN -->

<!-- SOURCE-BLOCK AUD11:38 END -->

[Previous chapter](03-f01-reference-identity-does-not-preserve-tenant-namespace.md) · [Chapter index](README.md) · [Next chapter](05-f03-ipv6-only-is-offered-but-cannot-be-represented-end-to-end.md)
