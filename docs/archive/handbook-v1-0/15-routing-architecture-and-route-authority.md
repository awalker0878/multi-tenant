# 15. Routing Architecture and Route Authority

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_0.docx) · [Chapter index](README.md)

> **Source:** HB10 — Draft v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 100c760003b9ff956ae369ece65c5ffe7736f6d481496d8df4c99dd6105d4190 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK HB10:150 BEGIN -->

<!-- SOURCE-BLOCK HB10:150 END -->

<!-- SOURCE-BLOCK HB10:151 BEGIN -->

Routing is generated from security intent rather than accepted as arbitrary consumer input. The Route Authority consumes IPAM allocations, Security Domain membership, ZIP relationships, Service Bindings, External Exposure objects, site topology, and placement results to compile permitted routes and advertisements.

<!-- SOURCE-BLOCK HB10:151 END -->

<!-- SOURCE-BLOCK HB10:152 BEGIN -->


<a id="source-table-152"></a>

| Consumer May Request | Consumer Shall Not Directly Control |
| --- | --- |
| “Connect this WSD to the approved identity service.” | Raw route to service subnet |
| “Allow approved Internet egress.” | 0.0.0.0/0 next-hop |
| “Expose HTTPS publicly.” | External BGP peer or route target |
| “Connect to approved enterprise service X.” | Arbitrary prefix import/export |
| “Enable migration connection for 72 hours.” | Permanent shared transit route |

<!-- SOURCE-BLOCK HB10:152 END -->

<!-- SOURCE-BLOCK HB10:153 BEGIN -->


<a id="source-table-153"></a>

| RTE-001 | Routes, route imports/exports, and BGP adjacencies SHALL be provider-controlled outputs of authorized intent. |
| --- | --- |

<!-- SOURCE-BLOCK HB10:153 END -->

<!-- SOURCE-BLOCK HB10:154 BEGIN -->


<a id="source-table-154"></a>

| RTE-002 | A generalized shared transit VRF SHALL NOT be used as a default inter-zone routing mechanism. |
| --- | --- |

<!-- SOURCE-BLOCK HB10:154 END -->

<!-- SOURCE-BLOCK HB10:155 BEGIN -->


<a id="source-table-155"></a>

| RTE-003 | Temporary migration or transition routes SHALL have explicit scope, approval, expiry, telemetry, and automated teardown. |
| --- | --- |

<!-- SOURCE-BLOCK HB10:155 END -->

[Previous chapter](14-platform-overlay-architecture.md) · [Chapter index](README.md) · [Next chapter](16-ip-address-management.md)
