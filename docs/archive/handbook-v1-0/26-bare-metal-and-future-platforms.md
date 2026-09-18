# 26. Bare Metal and Future Platforms

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_0.docx) · [Chapter index](README.md)

> **Source:** HB10 — Draft v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 100c760003b9ff956ae369ece65c5ffe7736f6d481496d8df4c99dd6105d4190 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK HB10:218 BEGIN -->

<!-- SOURCE-BLOCK HB10:218 END -->

<!-- SOURCE-BLOCK HB10:219 BEGIN -->

Bare-metal and future platforms can participate when they can realize the same semantics. A physical VRF may become the Security Domain implementation if the fabric must provide L3 routing for the physical systems. The portable API does not change; only the implementation profile changes.

<!-- SOURCE-BLOCK HB10:219 END -->

<!-- SOURCE-BLOCK HB10:220 BEGIN -->


<a id="source-table-220"></a>

| FUT-001 | A new platform SHALL pass the applicable conformance suite before it is approved for production placement. |
| --- | --- |

<!-- SOURCE-BLOCK HB10:220 END -->

<!-- SOURCE-BLOCK HB10:221 BEGIN -->


<a id="source-table-221"></a>

| FUT-002 | A platform SHALL declare unsupported capabilities explicitly; unsupported capabilities SHALL NOT be emulated by weakening a mandatory control. |
| --- | --- |

<!-- SOURCE-BLOCK HB10:221 END -->

[Previous chapter](25-openstack-implementation-profile.md) · [Chapter index](README.md) · [Next chapter](27-platform-capability-registry.md)
