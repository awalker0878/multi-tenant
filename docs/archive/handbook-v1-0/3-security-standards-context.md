# 3. Security Standards Context

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_0.docx) · [Chapter index](README.md)

> **Source:** HB10 — Draft v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 100c760003b9ff956ae369ece65c5ffe7736f6d481496d8df4c99dd6105d4190 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
ITSP.80.022 defines baseline network security zones including PAZ, OZ, RZ, HRZ, MZ and ZIPs. It also states that a zone does not need to map to a business function and that multiple zones may exist. The architecture therefore models security zones as reusable trust domains rather than organizational or service silos.

The handbook treats ITSG-33 as the lifecycle framework: security requirements are identified early, implemented through engineering controls, tested, operated, monitored, reassessed, and eventually disposed of securely. The architecture therefore includes evidence, drift, exception, change, and destruction workflows rather than ending at provisioning.

Where PBMM is applicable, it is treated as a security-control baseline that must be reused only in an appropriate context and tailored following analysis. The architecture therefore carries a Security Profile and Assurance Profile as explicit metadata instead of assuming that a single “Protected B network” topology is universally sufficient.


<a id="source-table-70"></a>

| IMPORTANT<br>Network zoning is one component of the control set. The handbook does not claim that correct zoning alone establishes authorization for Protected B or any other security category. |
| --- |

[Previous chapter](2-normative-language-and-architectural-invariants.md) · [Chapter index](README.md) · [Next chapter](4-core-conceptual-model.md)
