# F21  |  Complete protocol-profile and standards-adoption traceability

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Independent_Audit_v1_1.docx) · [Chapter index](README.md)

> **Source:** AUD11 — Audit of Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: cd901aaf004d45cf29ffe14ff955a0c9cf81f668be674e8d4de8c590303c62d8 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK AUD11:174 BEGIN -->

<!-- SOURCE-BLOCK AUD11:174 END -->

<!-- SOURCE-BLOCK AUD11:175 BEGIN -->

Medium priority • Externally verified improvement; preserve correct 2026 baseline<br>Location: Chapter 3; Chapter 25; Appendix H

<!-- SOURCE-BLOCK AUD11:175 END -->

<!-- SOURCE-BLOCK AUD11:176 BEGIN -->

Observed. The updates to ITSP.10.033 and ITSP.40.111 v5 are correct. The next refinement is protocol configuration, exact source locators and lifecycle/adoption tracking, rather than reverting to old catalogue or algorithm assumptions. ITSP.40.062 covers secure protocol configuration; ITSP.10.033 identifies related lifecycle publications. \[W01,W02,W05\]

<!-- SOURCE-BLOCK AUD11:176 END -->

<!-- SOURCE-BLOCK AUD11:177 BEGIN -->

Why it matters. An approved algorithm inventory alone does not specify endpoint authentication, protocol version/ciphers, trust validation and retirement behavior.

<!-- SOURCE-BLOCK AUD11:177 END -->

<!-- SOURCE-BLOCK AUD11:178 BEGIN -->

Improve. Add versioned TLS/SSH/IPsec and other offered protocol profiles tied to current guidance. Record clause/section, source edition, adoption decision and source-change triggers. Track related lifecycle guidance without asserting that unverified publications supersede every ITSG-33 annex.

<!-- SOURCE-BLOCK AUD11:178 END -->

<!-- SOURCE-BLOCK AUD11:179 BEGIN -->

Close when. An implementation can resolve its approved protocol configuration and exact guidance basis, and changed sources trigger a scoped reassessment.

<!-- SOURCE-BLOCK AUD11:179 END -->

<!-- SOURCE-BLOCK AUD11:180 BEGIN -->

Owner: Security standards and cryptography owners

<!-- SOURCE-BLOCK AUD11:180 END -->

[Previous chapter](22-f20-add-one-end-to-end-service-materialization-contract.md) · [Chapter index](README.md) · [Next chapter](24-f22-make-the-release-build-and-source-evidence-reproducible.md)
