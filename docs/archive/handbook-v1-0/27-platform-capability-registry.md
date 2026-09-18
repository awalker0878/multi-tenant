# 27. Platform Capability Registry

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_0.docx) · [Chapter index](README.md)

> **Source:** HB10 — Draft v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 100c760003b9ff956ae369ece65c5ffe7736f6d481496d8df4c99dd6105d4190 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.

<a id="source-table-223"></a>

| platform\_profile:<br>  network\_domain: true<br>  ipv4: true<br>  ipv6: true<br>  distributed\_firewall: true<br>  gateway\_policy: true<br>  dynamic\_routing: true<br>  service\_insertion: false<br>  native\_load\_balancer: true<br>  dedicated\_edge\_context: true<br>  audit\_logging: true<br>  tested\_assurance\_profiles:<br>    - standard<br>    - enhanced<br> |
| --- |

The capability registry is an input to placement. Capability assertions must be backed by test evidence and version-specific implementation documentation. A provider upgrade can invalidate a previously certified capability until regression tests are complete.

[Previous chapter](26-bare-metal-and-future-platforms.md) · [Chapter index](README.md) · [Next chapter](33-part-iv-zero-touch-automation-and-terraform.md)
