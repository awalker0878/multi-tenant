# 44. Change and Exception Management

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_0.docx) · [Chapter index](README.md)

> **Source:** HB10 — Draft v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 100c760003b9ff956ae369ece65c5ffe7736f6d481496d8df4c99dd6105d4190 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK HB10:331 BEGIN -->

<!-- SOURCE-BLOCK HB10:331 END -->

<!-- SOURCE-BLOCK HB10:332 BEGIN -->

Architecture exceptions are explicit objects, not comments hidden in Terraform. Every exception has scope, owner, rationale, compensating controls, approval and expiry. Expired exceptions automatically affect compliance state.

<!-- SOURCE-BLOCK HB10:332 END -->

<!-- SOURCE-BLOCK HB10:333 BEGIN -->


<a id="source-table-333"></a>

| kind: SecurityException<br>metadata:<br>  id: EX-000123<br>scope:<br>  tenant: tenant-001<br>  wsd: legacy-app<br>requirement: IPAM-002<br>justification: overlapping address space during migration<br>compensatingControls:<br>  - dedicated NAT boundary<br>  - enhanced logging<br>expires: 2027-01-31<br>status: approved<br> |
| --- |

<!-- SOURCE-BLOCK HB10:333 END -->

<!-- SOURCE-BLOCK HB10:334 BEGIN -->


<a id="source-table-334"></a>

| EXC-001 | Every exception SHALL have an accountable risk owner and expiry or review date. |
| --- | --- |

<!-- SOURCE-BLOCK HB10:334 END -->

<!-- SOURCE-BLOCK HB10:335 BEGIN -->


<a id="source-table-335"></a>

| EXC-002 | The control plane SHALL surface expired exceptions as non-compliant state rather than allowing them to become permanent undocumented architecture. |
| --- | --- |

<!-- SOURCE-BLOCK HB10:335 END -->

[Previous chapter](43-incident-response-and-containment.md) · [Chapter index](README.md) · [Next chapter](45-lifecycle-and-offboarding.md)
