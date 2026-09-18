# F14  |  Reference validation needs explicit coverage tiers and stronger negatives

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Independent_Audit_v1_1.docx) · [Chapter index](README.md)

> **Source:** AUD11 — Audit of Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: cd901aaf004d45cf29ffe14ff955a0c9cf81f668be674e8d4de8c590303c62d8 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK AUD11:121 BEGIN -->

<!-- SOURCE-BLOCK AUD11:121 END -->

<!-- SOURCE-BLOCK AUD11:122 BEGIN -->

High priority • Reproduced validation limits and robustness issue<br>Location: validate\_package.py; README; validation-report.json; Chapter 48

<!-- SOURCE-BLOCK AUD11:122 END -->

<!-- SOURCE-BLOCK AUD11:123 BEGIN -->

Observed. The supplied 50 self-checks pass, but independent probes find the documented gaps. Empty bundles are accepted; malformed entries can raise KeyError before item validation. Unknown policy-reference strings are not resolved. These observations are consistent with the README limiting the tool to selected semantics.

<!-- SOURCE-BLOCK AUD11:123 END -->

<!-- SOURCE-BLOCK AUD11:124 BEGIN -->

Why it matters. A single successful validator invocation is too easy to interpret as whole-contract consistency or readiness.

<!-- SOURCE-BLOCK AUD11:124 END -->

<!-- SOURCE-BLOCK AUD11:125 BEGIN -->

Improve. Return separate results for shape, graph, profile applicability, evidence completeness and authorization-not-evaluated. Validate input before indexing, give object-level diagnostics, and distinguish internal typed references from externally resolved policies. Add boundary/negative/property-based fixtures.

<!-- SOURCE-BLOCK AUD11:125 END -->

<!-- SOURCE-BLOCK AUD11:126 BEGIN -->

Close when. The reported validation scope lists every evaluated invariant; malformed inputs return diagnostics; every reproduced gap has a regression test or an explicit non-evaluated boundary.

<!-- SOURCE-BLOCK AUD11:126 END -->

<!-- SOURCE-BLOCK AUD11:127 BEGIN -->

Owner: Automation quality assurance  \|  Local probes: M21, M24, M25

<!-- SOURCE-BLOCK AUD11:127 END -->

<!-- SOURCE-BLOCK AUD11:128 BEGIN -->

<!-- SOURCE-BLOCK AUD11:128 END -->

[Previous chapter](15-f13-breaking-change-policy-and-api-version-naming-disagree.md) · [Chapter index](README.md) · [Next chapter](17-f15-printed-control-family-crosswalk-omits-existing-catalogue-mappings.md)
