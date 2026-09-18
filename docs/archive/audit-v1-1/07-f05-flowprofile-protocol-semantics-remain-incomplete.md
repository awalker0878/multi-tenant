# F05  |  FlowProfile protocol semantics remain incomplete

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Independent_Audit_v1_1.docx) · [Chapter index](README.md)

> **Source:** AUD11 — Audit of Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: cd901aaf004d45cf29ffe14ff955a0c9cf81f668be674e8d4de8c590303c62d8 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK AUD11:54 BEGIN -->

<!-- SOURCE-BLOCK AUD11:54 END -->

<!-- SOURCE-BLOCK AUD11:55 BEGIN -->

Medium priority • Confirmed underspecification<br>Location: Chapter 40 pp35-36; Appendix A p59; FlowProfile schema

<!-- SOURCE-BLOCK AUD11:55 END -->

<!-- SOURCE-BLOCK AUD11:56 BEGIN -->

Observed. TCP with an empty ports array is accepted without defining whether that means no ports or all ports. protocol=other is accepted without a protocol identifier. There are no structured ICMP type/code fields or a multi-flow service composition contract.

<!-- SOURCE-BLOCK AUD11:56 END -->

<!-- SOURCE-BLOCK AUD11:57 BEGIN -->

Why it matters. Different adapters could produce different permissions from the same syntactically valid intent.

<!-- SOURCE-BLOCK AUD11:57 END -->

<!-- SOURCE-BLOCK AUD11:58 BEGIN -->

Improve. Define discriminated protocol variants, explicit port/range semantics and ICMP type/code handling. Reject unsupported variants rather than silently translating them. Reference versioned application/L7 policy separately.

<!-- SOURCE-BLOCK AUD11:58 END -->

<!-- SOURCE-BLOCK AUD11:59 BEGIN -->

Close when. The same protocol fixture yields equivalent effective policy on each adapter; ambiguous and unsupported variants fail admission.

<!-- SOURCE-BLOCK AUD11:59 END -->

<!-- SOURCE-BLOCK AUD11:60 BEGIN -->

Owner: Contract and security engineering  \|  Local probes: M19, M20

<!-- SOURCE-BLOCK AUD11:60 END -->

[Previous chapter](06-f04-reference-dns-service-is-udp-only.md) · [Chapter index](README.md) · [Next chapter](08-f06-security-sensitive-profile-approval-is-not-a-consistent-contract.md)
