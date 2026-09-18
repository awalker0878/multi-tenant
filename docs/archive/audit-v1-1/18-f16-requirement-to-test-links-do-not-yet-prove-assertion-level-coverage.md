# F16  |  Requirement-to-test links do not yet prove assertion-level coverage

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Independent_Audit_v1_1.docx) · [Chapter index](README.md)

> **Source:** AUD11 — Audit of Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: cd901aaf004d45cf29ffe14ff955a0c9cf81f668be674e8d4de8c590303c62d8 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
Medium priority • Assurance-completeness improvement<br>Location: Appendices C-D; 194 requirements and 80 procedures

Observed. All requirement-to-test and reverse links resolve. Procedures are broad execution specifications, however, and a single test can be linked to many distinct clauses. Numeric thresholds, individual assertions and evidence targets are not normalized in the test contract.

Why it matters. Counting linked IDs proves traceability presence, not that every SHALL clause has a pass/fail observation.

Improve. Split compound requirements into identifiable assertions without renumbering stable parent IDs. Give tests assertion IDs, profile parameters, vantage points, preconditions, expected observations, failure/cleanup rules and evidence targets. Permit examination/interview where automation is inappropriate.

Close when. Every mandatory assertion has a verification method; each test result identifies which assertions it actually covered and which were blocked or inapplicable.

Owner: Assurance engineering

[Previous chapter](17-f15-printed-control-family-crosswalk-omits-existing-catalogue-mappings.md) · [Chapter index](README.md) · [Next chapter](19-f17-qualification-and-portability-need-separate-test-applicability-rules.md)
