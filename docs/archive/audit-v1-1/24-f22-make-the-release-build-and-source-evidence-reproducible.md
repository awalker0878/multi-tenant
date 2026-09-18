# F22  |  Make the release build and source evidence reproducible

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Independent_Audit_v1_1.docx) · [Chapter index](README.md)

> **Source:** AUD11 — Audit of Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: cd901aaf004d45cf29ffe14ff955a0c9cf81f668be674e8d4de8c590303c62d8 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK AUD11:181 BEGIN -->

<!-- SOURCE-BLOCK AUD11:181 END -->

<!-- SOURCE-BLOCK AUD11:182 BEGIN -->

Medium priority • Release-engineering improvement<br>Location: Companion package, source register and publishing reports

<!-- SOURCE-BLOCK AUD11:182 END -->

<!-- SOURCE-BLOCK AUD11:183 BEGIN -->

Observed. All 39 listed package hashes match, and the self-tests reproduce. The package includes schema generation source and document content catalogues, but not a complete documented handbook/publishing build. Runtime dependency ranges are broad; review dates are not preserved source snapshots.

<!-- SOURCE-BLOCK AUD11:183 END -->

<!-- SOURCE-BLOCK AUD11:184 BEGIN -->

Why it matters. Another maintainer cannot independently regenerate every published table, report and page from one locked source release.

<!-- SOURCE-BLOCK AUD11:184 END -->

<!-- SOURCE-BLOCK AUD11:185 BEGIN -->

Improve. Provide build entry points, a locked validation/render environment, source snapshots or hashes with exact locators, generated-artifact parity tests and a provenance manifest. Preserve source availability/licensing constraints; a hash is integrity evidence, not authority approval.

<!-- SOURCE-BLOCK AUD11:185 END -->

<!-- SOURCE-BLOCK AUD11:186 BEGIN -->

Close when. A clean build reproduces schema/catalogue content and publishing checks, with documented rendering tolerances and no manually stale crosswalk.

<!-- SOURCE-BLOCK AUD11:186 END -->

<!-- SOURCE-BLOCK AUD11:187 BEGIN -->

Owner: Release and documentation engineering

<!-- SOURCE-BLOCK AUD11:187 END -->

<!-- SOURCE-BLOCK AUD11:188 BEGIN -->

<!-- SOURCE-BLOCK AUD11:188 END -->

[Previous chapter](23-f21-complete-protocol-profile-and-standards-adoption-traceability.md) · [Chapter index](README.md) · [Next chapter](25-f23-improve-reader-navigation-and-verification-evidence-not-page-count.md)
