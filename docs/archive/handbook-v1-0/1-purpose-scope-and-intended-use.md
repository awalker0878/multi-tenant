# 1. Purpose, Scope, and Intended Use

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_0.docx) · [Chapter index](README.md)

> **Source:** HB10 — Draft v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 100c760003b9ff956ae369ece65c5ffe7736f6d481496d8df4c99dd6105d4190 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
The purpose of this handbook is to define a reusable hosting architecture for multi-tenant virtualized and cloud-like environments while preserving Government network-security-zone semantics and minimizing dependence on any one virtualization or networking product.

The handbook is intended to be both normative and practical. Architecture requirements use SHALL/SHOULD/MAY language. Engineering sections explain how those requirements should be realized without turning any current product capability into an enterprise architecture dependency.

## 1.1 Intended Users

- Enterprise and solution architects

- Network and security architects

- Virtualization and private-cloud engineers

- Automation and Terraform engineers

- Security assessors and ISSIP practitioners

- Operations, SRE, incident response, and capacity teams

- Service owners and product managers

## 1.2 Design Constraints


<a id="source-table-52"></a>

| ARCH-001 | The hosting contract SHALL be vendor neutral and SHALL NOT require consumers to specify vendor-specific identifiers or topology objects. |
| --- | --- |


<a id="source-table-53"></a>

| ARCH-002 | Routine tenant and workload lifecycle operations SHOULD NOT require changes to physical leaf or spine configuration.<br>Rationale: This keeps high-cardinality tenant state out of the fabric and is essential for scalable zero-touch operations. |
| --- | --- |


<a id="source-table-54"></a>

| ARCH-003 | All inter-zone paths SHALL be explicit and SHALL traverse the applicable ZIP/security edge. |
| --- | --- |


<a id="source-table-55"></a>

| ARCH-004 | Management/OOB traffic SHALL be separated from tenant operational traffic and SHALL have independently controlled access paths. |
| --- | --- |

[Previous chapter](03-part-i-foundations.md) · [Chapter index](README.md) · [Next chapter](2-normative-language-and-architectural-invariants.md)
