# F17  |  Qualification and portability need separate test applicability rules

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Independent_Audit_v1_1.docx) · [Chapter index](README.md)

> **Source:** AUD11 — Audit of Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: cd901aaf004d45cf29ffe14ff955a0c9cf81f668be674e8d4de8c590303c62d8 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
Medium priority • Design inconsistency requiring applicability decision<br>Location: Chapter 48 p43; Chapter 61 pp54-55; CT-016 pp77-78

Observed. Qualification calls for all applicable tests, while CT-016 requires two independently qualified adapters. The delivery roadmap first qualifies one platform and adds a second later. No machine-readable applicability rule explains when the two-platform test is required.

Why it matters. A literal reading produces a circular prerequisite for first-platform qualification or encourages an undocumented N/A decision.

Improve. Define stage/profile applicability: contract/offline checks, single-platform qualification, per-deployment checks, cross-platform portability qualification and operational exercises. First-platform approval must not imply cross-platform portability.

Close when. The first platform qualifies without circular prerequisites; a portability claim is blocked until the separate two-platform test succeeds.

Owner: Qualification and delivery owners

[Previous chapter](18-f16-requirement-to-test-links-do-not-yet-prove-assertion-level-coverage.md) · [Chapter index](README.md) · [Next chapter](20-f18-cadence-and-execution-status-records-need-reconciliation.md)
