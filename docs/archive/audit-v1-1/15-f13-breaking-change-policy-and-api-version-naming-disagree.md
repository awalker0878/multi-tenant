# F13  |  Breaking-change policy and API version naming disagree

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Independent_Audit_v1_1.docx) · [Chapter index](README.md)

> **Source:** AUD11 — Audit of Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: cd901aaf004d45cf29ffe14ff955a0c9cf81f668be674e8d4de8c590303c62d8 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
Medium priority • Confirmed policy ambiguity<br>Location: Chapter 39 p35; Appendix B p64

Observed. The handbook calls for a major version for breaking semantic changes, but uses hosting.platform/v1.1 for a substantially different envelope and field model from the illustrative v1 request. A migration paragraph acknowledges these changes.

Why it matters. Document release numbering can be mistaken for wire-contract compatibility.

Improve. Separate handbook release, schema dialect, API compatibility major and profile version. Use a new API major for breaking changes, or explicitly declare the original contract pre-stable and document the compatibility boundary.

Close when. Old request fixtures either convert with an explicit reviewed semantic diff or fail with an actionable version error; no silent default expansion.

Owner: Contract governance

[Previous chapter](14-f12-api-lifecycle-is-not-closed-over-the-required-object-graph.md) · [Chapter index](README.md) · [Next chapter](16-f14-reference-validation-needs-explicit-coverage-tiers-and-stronger-negatives.md)
