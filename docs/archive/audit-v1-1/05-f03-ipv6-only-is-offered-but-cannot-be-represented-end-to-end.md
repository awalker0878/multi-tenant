# F03  |  IPv6-only is offered but cannot be represented end to end

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Independent_Audit_v1_1.docx) · [Chapter index](README.md)

> **Source:** AUD11 — Audit of Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: cd901aaf004d45cf29ffe14ff955a0c9cf81f668be674e8d4de8c590303c62d8 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK AUD11:39 BEGIN -->

<!-- SOURCE-BLOCK AUD11:39 END -->

<!-- SOURCE-BLOCK AUD11:40 BEGIN -->

High priority • Confirmed prose/schema contradiction<br>Location: Chapter 16 p16; Appendix A; WorkloadSecurityDomain and Network schemas

<!-- SOURCE-BLOCK AUD11:40 END -->

<!-- SOURCE-BLOCK AUD11:41 BEGIN -->

Observed. The request model accepts ipv6Mode=ipv6-only but still requires ipv4PrefixSize. The realized Network requires a non-null IPv4 prefix. Omitting that prefix or making it null is rejected.

<!-- SOURCE-BLOCK AUD11:41 END -->

<!-- SOURCE-BLOCK AUD11:42 BEGIN -->

Why it matters. A genuine IPv6-only deployment needs an invented IPv4 allocation or cannot be represented, contradicting the advertised service mode.

<!-- SOURCE-BLOCK AUD11:42 END -->

<!-- SOURCE-BLOCK AUD11:43 BEGIN -->

Improve. Use a single address-family mode in intent and realization, with conditional required/forbidden IPv4 and IPv6 allocation fields. Do not hide a fake IPv4 address inside an IPv6-only profile.

<!-- SOURCE-BLOCK AUD11:43 END -->

<!-- SOURCE-BLOCK AUD11:44 BEGIN -->

Close when. Round-trip valid IPv4-only, IPv6-only and dual-stack request/normalized/realized examples. Reject missing required families and unwanted allocations.

<!-- SOURCE-BLOCK AUD11:44 END -->

<!-- SOURCE-BLOCK AUD11:45 BEGIN -->

Owner: Network and contract engineering  \|  Local probes: M10, M11, M12

<!-- SOURCE-BLOCK AUD11:45 END -->

[Previous chapter](04-f02-cross-object-consistency-checks-do-not-cover-the-complete-graph.md) · [Chapter index](README.md) · [Next chapter](06-f04-reference-dns-service-is-udp-only.md)
