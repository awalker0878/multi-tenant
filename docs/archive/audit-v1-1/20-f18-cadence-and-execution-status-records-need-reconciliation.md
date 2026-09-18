# F18  |  Cadence and execution-status records need reconciliation

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Independent_Audit_v1_1.docx) · [Chapter index](README.md)

> **Source:** AUD11 — Audit of Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: cd901aaf004d45cf29ffe14ff955a0c9cf81f668be674e8d4de8c590303c62d8 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK AUD11:151 BEGIN -->

<!-- SOURCE-BLOCK AUD11:151 END -->

<!-- SOURCE-BLOCK AUD11:152 BEGIN -->

Medium priority • Confirmed local-parameter mismatch and classification ambiguity<br>Location: CT-055 p85; CT-075 p89; Appendix F p93; release reports

<!-- SOURCE-BLOCK AUD11:152 END -->

<!-- SOURCE-BLOCK AUD11:153 BEGIN -->

Observed. CT-055 specifies annual bootstrap recovery, while the proposed critical-configuration recovery parameter and example RecoveryProfile use 180 days. CT-075 is a document/package procedure, yet the appendix groups all 80 tests as infrastructure tests marked not-run while a separate 50-check release suite has executed.

<!-- SOURCE-BLOCK AUD11:153 END -->

<!-- SOURCE-BLOCK AUD11:154 BEGIN -->

Why it matters. Operators cannot derive one unambiguous local schedule, and readers may confuse a specified test with a recorded execution.

<!-- SOURCE-BLOCK AUD11:154 END -->

<!-- SOURCE-BLOCK AUD11:155 BEGIN -->

Improve. Make test cadence a profile-parameter reference; define precedence for adopted versus proposed values. Separate test definitions from execution records and map the 50 release checks to covered CT-075 assertions without claiming unperformed parts passed.

<!-- SOURCE-BLOCK AUD11:155 END -->

<!-- SOURCE-BLOCK AUD11:156 BEGIN -->

Close when. No contradictory cadence literals remain; release checks have explicit coverage, date and result while unexecuted infrastructure tests remain not-run.

<!-- SOURCE-BLOCK AUD11:156 END -->

<!-- SOURCE-BLOCK AUD11:157 BEGIN -->

Owner: Recovery, assurance and release owners

<!-- SOURCE-BLOCK AUD11:157 END -->

<!-- SOURCE-BLOCK AUD11:158 BEGIN -->

<!-- SOURCE-BLOCK AUD11:158 END -->

[Previous chapter](19-f17-qualification-and-portability-need-separate-test-applicability-rules.md) · [Chapter index](README.md) · [Next chapter](21-f19-document-fencing-and-pre-post-activation-verification-explicitly.md)
