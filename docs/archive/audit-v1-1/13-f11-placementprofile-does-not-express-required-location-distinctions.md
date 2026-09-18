# F11  |  PlacementProfile does not express required location distinctions

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Independent_Audit_v1_1.docx) · [Chapter index](README.md)

> **Source:** AUD11 — Audit of Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: cd901aaf004d45cf29ffe14ff955a0c9cf81f668be674e8d4de8c590303c62d8 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
High priority • Confirmed prose/schema coverage gap<br>Location: Chapter 29 p26, PLACE-002; Appendix A p58; PlacementProfile

Observed. PLACE-002 separately names data, backup, telemetry, diagnostics, control plane, administrative access and key constraints. The schema exposes only dataLocations and controlLocations, with free-text support/key policies.

Why it matters. The intended placement decision cannot mechanically distinguish a permitted primary-data site from an impermissible backup, diagnostic or administrative location.

Improve. Add a typed constraints map by asset/access category, with enforcement and evidence references. Distinguish location, jurisdiction/control, access path and key custody; do not pretend a location field resolves legal sovereignty.

Close when. Independently reject fixtures violating only backup, telemetry, diagnostics, key or administrative-access constraints while the primary site remains allowed.

Owner: Placement, security and data governance

[Previous chapter](12-f10-per-control-evidence-trace-is-described-but-not-contracted.md) · [Chapter index](README.md) · [Next chapter](14-f12-api-lifecycle-is-not-closed-over-the-required-object-graph.md)
