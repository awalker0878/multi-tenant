# 1. Purpose, Scope, and Intended Use

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_0.docx) · [Chapter index](README.md)

> **Source:** HB10 — Draft v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 100c760003b9ff956ae369ece65c5ffe7736f6d481496d8df4c99dd6105d4190 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK HB10:40 BEGIN -->

<!-- SOURCE-BLOCK HB10:40 END -->

<!-- SOURCE-BLOCK HB10:41 BEGIN -->

The purpose of this handbook is to define a reusable hosting architecture for multi-tenant virtualized and cloud-like environments while preserving Government network-security-zone semantics and minimizing dependence on any one virtualization or networking product.

<!-- SOURCE-BLOCK HB10:41 END -->

<!-- SOURCE-BLOCK HB10:42 BEGIN -->

The handbook is intended to be both normative and practical. Architecture requirements use SHALL/SHOULD/MAY language. Engineering sections explain how those requirements should be realized without turning any current product capability into an enterprise architecture dependency.

<!-- SOURCE-BLOCK HB10:42 END -->

<!-- SOURCE-BLOCK HB10:43 BEGIN -->

## 1.1 Intended Users

<!-- SOURCE-BLOCK HB10:43 END -->

<!-- SOURCE-BLOCK HB10:44 BEGIN -->

- Enterprise and solution architects

<!-- SOURCE-BLOCK HB10:44 END -->

<!-- SOURCE-BLOCK HB10:45 BEGIN -->

- Network and security architects

<!-- SOURCE-BLOCK HB10:45 END -->

<!-- SOURCE-BLOCK HB10:46 BEGIN -->

- Virtualization and private-cloud engineers

<!-- SOURCE-BLOCK HB10:46 END -->

<!-- SOURCE-BLOCK HB10:47 BEGIN -->

- Automation and Terraform engineers

<!-- SOURCE-BLOCK HB10:47 END -->

<!-- SOURCE-BLOCK HB10:48 BEGIN -->

- Security assessors and ISSIP practitioners

<!-- SOURCE-BLOCK HB10:48 END -->

<!-- SOURCE-BLOCK HB10:49 BEGIN -->

- Operations, SRE, incident response, and capacity teams

<!-- SOURCE-BLOCK HB10:49 END -->

<!-- SOURCE-BLOCK HB10:50 BEGIN -->

- Service owners and product managers

<!-- SOURCE-BLOCK HB10:50 END -->

<!-- SOURCE-BLOCK HB10:51 BEGIN -->

## 1.2 Design Constraints

<!-- SOURCE-BLOCK HB10:51 END -->

<!-- SOURCE-BLOCK HB10:52 BEGIN -->


<a id="source-table-52"></a>

| ARCH-001 | The hosting contract SHALL be vendor neutral and SHALL NOT require consumers to specify vendor-specific identifiers or topology objects. |
| --- | --- |

<!-- SOURCE-BLOCK HB10:52 END -->

<!-- SOURCE-BLOCK HB10:53 BEGIN -->


<a id="source-table-53"></a>

| ARCH-002 | Routine tenant and workload lifecycle operations SHOULD NOT require changes to physical leaf or spine configuration.<br>Rationale: This keeps high-cardinality tenant state out of the fabric and is essential for scalable zero-touch operations. |
| --- | --- |

<!-- SOURCE-BLOCK HB10:53 END -->

<!-- SOURCE-BLOCK HB10:54 BEGIN -->


<a id="source-table-54"></a>

| ARCH-003 | All inter-zone paths SHALL be explicit and SHALL traverse the applicable ZIP/security edge. |
| --- | --- |

<!-- SOURCE-BLOCK HB10:54 END -->

<!-- SOURCE-BLOCK HB10:55 BEGIN -->


<a id="source-table-55"></a>

| ARCH-004 | Management/OOB traffic SHALL be separated from tenant operational traffic and SHALL have independently controlled access paths. |
| --- | --- |

<!-- SOURCE-BLOCK HB10:55 END -->

[Previous chapter](03-part-i-foundations.md) · [Chapter index](README.md) · [Next chapter](2-normative-language-and-architectural-invariants.md)
