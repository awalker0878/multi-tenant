# 52. Architecture Acceptance Criteria

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_0.docx) · [Chapter index](README.md)

> **Source:** HB10 — Draft v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 100c760003b9ff956ae369ece65c5ffe7736f6d481496d8df4c99dd6105d4190 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK HB10:395 BEGIN -->

<!-- SOURCE-BLOCK HB10:395 END -->

<!-- SOURCE-BLOCK HB10:396 BEGIN -->


<a id="source-table-396"></a>

| AC-01 | A normal tenant/WSD can be provisioned without modifying leaf or spine configuration. |
| --- | --- |

<!-- SOURCE-BLOCK HB10:396 END -->

<!-- SOURCE-BLOCK HB10:397 BEGIN -->


<a id="source-table-397"></a>

| AC-02 | Cross-tenant isolation is demonstrated automatically. |
| --- | --- |

<!-- SOURCE-BLOCK HB10:397 END -->

<!-- SOURCE-BLOCK HB10:398 BEGIN -->


<a id="source-table-398"></a>

| AC-03 | Inter-zone communication cannot bypass the declared security edge. |
| --- | --- |

<!-- SOURCE-BLOCK HB10:398 END -->

<!-- SOURCE-BLOCK HB10:399 BEGIN -->


<a id="source-table-399"></a>

| AC-04 | Management/OOB is unreachable from tenant workload paths. |
| --- | --- |

<!-- SOURCE-BLOCK HB10:399 END -->

<!-- SOURCE-BLOCK HB10:400 BEGIN -->


<a id="source-table-400"></a>

| AC-05 | Shared services are consumed through explicit bindings rather than broad shared-subnet access. |
| --- | --- |

<!-- SOURCE-BLOCK HB10:400 END -->

<!-- SOURCE-BLOCK HB10:401 BEGIN -->


<a id="source-table-401"></a>

| AC-06 | Workload owners cannot create arbitrary routes, BGP peers, or external network attachments. |
| --- | --- |

<!-- SOURCE-BLOCK HB10:401 END -->

<!-- SOURCE-BLOCK HB10:402 BEGIN -->


<a id="source-table-402"></a>

| AC-07 | IPv4 and IPv6 policy equivalence is tested where dual-stack is offered. |
| --- | --- |

<!-- SOURCE-BLOCK HB10:402 END -->

<!-- SOURCE-BLOCK HB10:403 BEGIN -->


<a id="source-table-403"></a>

| AC-08 | Public exposure requires an approved ingress path; Internet egress requires an approved egress profile. |
| --- | --- |

<!-- SOURCE-BLOCK HB10:403 END -->

<!-- SOURCE-BLOCK HB10:404 BEGIN -->


<a id="source-table-404"></a>

| AC-09 | Unsupported platform capabilities cause placement failure rather than silent downgrade. |
| --- | --- |

<!-- SOURCE-BLOCK HB10:404 END -->

<!-- SOURCE-BLOCK HB10:405 BEGIN -->


<a id="source-table-405"></a>

| AC-10 | Every Service Ready deployment produces evidence tied to source and policy versions. |
| --- | --- |

<!-- SOURCE-BLOCK HB10:405 END -->

<!-- SOURCE-BLOCK HB10:406 BEGIN -->


<a id="source-table-406"></a>

| AC-11 | Security-significant drift and expired exceptions affect compliance state. |
| --- | --- |

<!-- SOURCE-BLOCK HB10:406 END -->

<!-- SOURCE-BLOCK HB10:407 BEGIN -->


<a id="source-table-407"></a>

| AC-12 | Offboarding demonstrably removes routes, policies, service bindings and identities. |
| --- | --- |

<!-- SOURCE-BLOCK HB10:407 END -->

<!-- SOURCE-BLOCK HB10:408 BEGIN -->


<a id="source-table-408"></a>

| AC-13 | At least two different platform profiles can realize the same portable WSD semantics. |
| --- | --- |

<!-- SOURCE-BLOCK HB10:408 END -->

<!-- SOURCE-BLOCK HB10:409 BEGIN -->

<!-- SOURCE-BLOCK HB10:409 END -->

[Previous chapter](51-initial-reference-implementation.md) · [Chapter index](README.md) · [Next chapter](61-appendix-a-canonical-object-model.md)
