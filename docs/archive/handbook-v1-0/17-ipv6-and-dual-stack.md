# 17. IPv6 and Dual-Stack

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_0.docx) · [Chapter index](README.md)

> **Source:** HB10 — Draft v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 100c760003b9ff956ae369ece65c5ffe7736f6d481496d8df4c99dd6105d4190 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
IPv6 must be part of the architecture from the beginning even where an initial release is IPv4-only. The service schema, security policy, routing authority, logging, conformance tests and evidence model must be capable of representing IPv6 so that an alternate protocol cannot become an ungoverned path.


<a id="source-table-164"></a>

| IPV6-001 | Security semantics SHALL be equivalent across IPv4 and IPv6 unless an explicit, approved protocol-specific exception exists. |
| --- | --- |


<a id="source-table-165"></a>

| IPV6-002 | Conformance testing SHALL include IPv6 negative-path tests before a platform is certified for dual-stack service. |
| --- | --- |

[Previous chapter](16-ip-address-management.md) · [Chapter index](README.md) · [Next chapter](18-shared-services-and-service-bindings.md)
