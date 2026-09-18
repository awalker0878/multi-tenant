# F07  |  Qualification lifecycle differs between prose and schema

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Independent_Audit_v1_1.docx) · [Chapter index](README.md)

> **Source:** AUD11 — Audit of Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: cd901aaf004d45cf29ffe14ff955a0c9cf81f668be674e8d4de8c590303c62d8 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK AUD11:69 BEGIN -->

<!-- SOURCE-BLOCK AUD11:69 END -->

<!-- SOURCE-BLOCK AUD11:70 BEGIN -->

Medium priority • Confirmed internal inconsistency<br>Location: Chapter 34 pp30-31; Appendix A p60; PlatformProfile

<!-- SOURCE-BLOCK AUD11:70 END -->

<!-- SOURCE-BLOCK AUD11:71 BEGIN -->

Observed. The prose lifecycle includes Testing, Restricted, and Expired/Revoked. The machine-readable enumeration is Candidate, Qualified, Suspended, Retired. Testing and Revoked objects are rejected.

<!-- SOURCE-BLOCK AUD11:71 END -->

<!-- SOURCE-BLOCK AUD11:72 BEGIN -->

Why it matters. Operators and automation cannot follow one authoritative state machine or agree how qualification expiry affects placement.

<!-- SOURCE-BLOCK AUD11:72 END -->

<!-- SOURCE-BLOCK AUD11:73 BEGIN -->

Improve. Choose one lifecycle and generate the prose table, schema enums, API transitions and examples from it. Specify whether expiry is derived from time or an explicit state, and distinguish limited qualification from suspension.

<!-- SOURCE-BLOCK AUD11:73 END -->

<!-- SOURCE-BLOCK AUD11:74 BEGIN -->

Close when. Every documented state and transition round-trips; expired qualification blocks new placement without deleting historical evidence.

<!-- SOURCE-BLOCK AUD11:74 END -->

<!-- SOURCE-BLOCK AUD11:75 BEGIN -->

Owner: Platform qualification owner  \|  Local probes: M13, M14

<!-- SOURCE-BLOCK AUD11:75 END -->

[Previous chapter](08-f06-security-sensitive-profile-approval-is-not-a-consistent-contract.md) · [Chapter index](README.md) · [Next chapter](10-f08-qualification-record-cannot-fully-express-qual-001.md)
