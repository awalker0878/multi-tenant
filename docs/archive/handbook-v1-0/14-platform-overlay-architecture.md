# 14. Platform Overlay Architecture

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_0.docx) · [Chapter index](README.md)

> **Source:** HB10 — Draft v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 100c760003b9ff956ae369ece65c5ffe7736f6d481496d8df4c99dd6105d4190 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
High-cardinality tenant routing and segmentation should normally live in the platform overlay. Each approved platform implements the same Security Domain, Network, Flow, Service Binding and Exposure semantics using native constructs. The platform boundary is where tenant lifecycle changes should normally occur.


<a id="source-table-148"></a>

| OVL-001 | A platform SHALL provide an isolated routing/policy mechanism capable of realizing the Security Domain semantics required by the applicable conformance profile. |
| --- | --- |


<a id="source-table-149"></a>

| OVL-002 | Internal routing inside one Security Domain MAY be provided natively by the platform; routing between different zone instances SHALL follow the security-edge path. |
| --- | --- |

[Previous chapter](13-physical-fabric.md) · [Chapter index](README.md) · [Next chapter](15-routing-architecture-and-route-authority.md)
