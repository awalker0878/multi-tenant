# 6. High-Level Reference Architecture

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_0.docx) · [Chapter index](README.md)

> **Source:** HB10 — Draft v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 100c760003b9ff956ae369ece65c5ffe7736f6d481496d8df4c99dd6105d4190 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
![Image: image1.png](../../assets/diagrams/ddb61257a4e5cdc7cdcc.png)

Figure 2. Reference architecture layers.

The service contract is the durable interface. The security control plane compiles desired state into a validated, routable, placeable design. Platform adapters translate that design into native provider resources. The security edge mediates trust transitions. The physical fabric carries traffic but is intentionally kept largely unaware of application and tenant lifecycle.


<a id="source-table-92"></a>

| REF-001 | The service contract SHALL remain stable when a supported platform is replaced, provided the replacement platform passes the required conformance profile. |
| --- | --- |


<a id="source-table-93"></a>

| REF-002 | Platform-specific extensions MAY be offered, but they SHALL be declared as capabilities and SHALL NOT redefine the portable core semantics. |
| --- | --- |

[Previous chapter](09-part-ii-reference-architecture.md) · [Chapter index](README.md) · [Next chapter](7-tenant-namespace.md)
