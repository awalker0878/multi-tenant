# F04  |  Reference DNS service is UDP-only

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Independent_Audit_v1_1.docx) · [Chapter index](README.md)

> **Source:** AUD11 — Audit of Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: cd901aaf004d45cf29ffe14ff955a0c9cf81f668be674e8d4de8c590303c62d8 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
High priority • Confirmed example defect, externally verified protocol requirement<br>Location: Chapter 17 p17; examples/reference-bundle.json: dns-flow-reference and dns-reference

Observed. The reference DNS FlowProfile permits UDP port 53 only. ServiceProfile points to one FlowProfile. The example therefore does not describe TCP DNS or a multi-flow service bundle.

Why it matters. RFC 7766 requires TCP support for general-purpose DNS implementations and warns that blocking it can cause resolution failures. A basic successful lookup is an inadequate DNS acceptance test. \[W03\]

Improve. Model a service as an explicit set of required protocol flows. The ordinary resolver profile should include appropriate UDP and TCP DNS, while encrypted DNS variants remain separately authorized profiles.

Close when. Exercise UDP resolution, TCP resolution, a truncated UDP response requiring TCP retry, and unauthorized resolver denial in both offered address families.

Owner: Shared-service and network engineering

[Previous chapter](05-f03-ipv6-only-is-offered-but-cannot-be-represented-end-to-end.md) · [Chapter index](README.md) · [Next chapter](07-f05-flowprofile-protocol-semantics-remain-incomplete.md)
