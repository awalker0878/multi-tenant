# F06  |  Security-sensitive profile approval is not a consistent contract

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Independent_Audit_v1_1.docx) · [Chapter index](README.md)

> **Source:** AUD11 — Audit of Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: cd901aaf004d45cf29ffe14ff955a0c9cf81f668be674e8d4de8c590303c62d8 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
High priority • Confirmed schema coverage and semantic gaps<br>Location: Chapters 4, 25 and 47; Appendix A pp57-60; profile schemas

Observed. Approval fields exist on only some profile types. A Dedicated AssuranceProfile with Approved state and every isolation dimension shared-qualified is accepted. Other profiles use free-text policies without a common approval, applicability, validity or supersession envelope.

Why it matters. A profile name or approval string can be mistaken for an accountable, current security decision; local profile semantics are not consistently checkable.

Improve. Adopt a common governance envelope or a typed approval-record reference. Bind issuer authority, object digest/version, validity, scope and revocation. Define the minimum guarantees for each named assurance level without equating dedication with all hardware being exclusive.

Close when. Reject contradictory assurance vectors, expired or absent mandatory approvals, and approval records for a different profile generation.

Owner: Security authority and contract engineering  \|  Local probes: M06

[Previous chapter](07-f05-flowprofile-protocol-semantics-remain-incomplete.md) · [Chapter index](README.md) · [Next chapter](09-f07-qualification-lifecycle-differs-between-prose-and-schema.md)
