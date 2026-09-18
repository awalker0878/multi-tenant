# F08  |  Qualification record cannot fully express QUAL-001

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Independent_Audit_v1_1.docx) · [Chapter index](README.md)

> **Source:** AUD11 — Audit of Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: cd901aaf004d45cf29ffe14ff955a0c9cf81f668be674e8d4de8c590303c62d8 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
High priority • Confirmed representation and validation gaps<br>Location: Chapter 34 p31; PlatformProfile schema

Observed. QUAL-001 calls for hardware, feature/license and tested-limit context. The closed PlatformProfile has no structured hardware or license/feature tuple, no tested assurance-profile set, and weakly typed numeric limits. A Qualified fixture with empty capabilities and one arbitrary zero-valued limit is accepted.

Why it matters. The record cannot support deterministic eligibility for a particular service, topology, hardware stack or assurance profile without unspecified external interpretation.

Improve. Define a versioned implementation manifest for product components, API/provider, hardware/firmware, enabled features/licenses, topology and qualified service profiles. Give limits names, units, conditions and evidence; qualifications need not support every feature.

Close when. Placement proves the exact requested capabilities/profile under the recorded tuple and rejects missing mandatory tuple or limit evidence.

Owner: Platform qualification and automation  \|  Local probes: M15, M16

[Previous chapter](09-f07-qualification-lifecycle-differs-between-prose-and-schema.md) · [Chapter index](README.md) · [Next chapter](11-f09-evidence-validation-accepts-incomplete-readiness-assertions.md)
