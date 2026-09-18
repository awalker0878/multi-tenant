# F10  |  Per-control evidence trace is described but not contracted

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Independent_Audit_v1_1.docx) · [Chapter index](README.md)

> **Source:** AUD11 — Audit of Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: cd901aaf004d45cf29ffe14ff955a0c9cf81f668be674e8d4de8c590303c62d8 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
High priority • Confirmed structured-contract omission<br>Location: Chapter 49 p44; Appendix E pp91-92; EvidenceRecord schema

Observed. The handbook describes requirement/source/control-to-owner-to-realized-object-to-test traceability. EvidenceRecord has generic artifact/realization strings but no defined per-control result contract. Adding a controlResults structure is rejected. External artifacts may hold detail, but their schema and resolver are unspecified.

Why it matters. An assessor can receive files but cannot rely on a standardized machine-readable chain or completeness query.

Improve. Define a ControlImplementation/ControlResult record or a versioned external evidence schema. Include catalogue edition, selected control/enhancement, parameters, owner, implementation IDs, test executions, artifact digests, inheritance and residual gaps.

Close when. From one requirement or selected control, resolve the exact implementation, applicable tests, actual outcomes and accountable decision without free-text inference.

Owner: Assurance architecture  \|  Local probes: M17

[Previous chapter](11-f09-evidence-validation-accepts-incomplete-readiness-assertions.md) · [Chapter index](README.md) · [Next chapter](13-f11-placementprofile-does-not-express-required-location-distinctions.md)
