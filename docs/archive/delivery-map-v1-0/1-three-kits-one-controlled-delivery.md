# 1. Three kits, one controlled delivery

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/07_Quality/prior_v1_0/00_Delivery_Map.docx) · [Chapter index](README.md)

> **Source:** DEL10 — Delivery kits v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: e332c1b37e63439169adf8b105573577fa1ea61bf32f6c3ba383dd69d83a788b -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK DEL10:15 BEGIN -->

<a id="DEL_01"></a>

<!-- SOURCE-BLOCK DEL10:15 END -->

<!-- SOURCE-BLOCK DEL10:16 BEGIN -->

These kits extend the v1.4 library without changing its eight baseline documents. The kit version is independent of the reference-architecture version. A proposed delivery record does not amend an adopted architectural requirement.

<!-- SOURCE-BLOCK DEL10:16 END -->

<!-- SOURCE-BLOCK DEL10:17 BEGIN -->

Baseline and related records: [RA §1](../../architecture/reference/1-purpose-scope-and-architectural-authority.md#RA_s_001)  •  [RA §30](../../architecture/reference/30-implementation-handoff-and-delivery-sequence.md#RA_s_030)  •  [WD §9](../../solutions/internal-protected-workload/9-build-sequence-with-explicit-acceptance-dependencies.md#WD14_S09)

<!-- SOURCE-BLOCK DEL10:17 END -->

<!-- SOURCE-BLOCK DEL10:18 BEGIN -->


<a id="source-table-18"></a>

| Kit | Primary question | Exit artifact |
| --- | --- | --- |
| Architecture | What is required, why, where are the boundaries, and what may be shared? | Reviewed high-level design (HLD), decisions, service envelope, selected controls and engineering handoff. |
| Engineering | Exactly how will this site and selected stack realize the approved design? | Reviewed low-level design (LLD), resource/path schedules, calculations, support tuple and build/test package. |
| Implementation | How will the approved configuration be established, verified, activated and operated? | Executed method of procedure (MOP), observed test/evidence records, as-built configuration and accepted handover. |

<!-- SOURCE-BLOCK DEL10:18 END -->

<!-- SOURCE-BLOCK DEL10:19 BEGIN -->

<!-- SOURCE-BLOCK DEL10:19 END -->

<!-- SOURCE-BLOCK DEL10:20 BEGIN -->

## How the work connects

<!-- SOURCE-BLOCK DEL10:20 END -->

<!-- SOURCE-BLOCK DEL10:21 BEGIN -->

Carry a stable requirement or decision ID into the engineering schedule, then into a work-package step, a verification assertion and the resulting evidence. Retain actual resource IDs only in the controlled engineering and as-built records. A diagram must use the same component and interface identities as the schedules.

<!-- SOURCE-BLOCK DEL10:21 END -->

<!-- SOURCE-BLOCK DEL10:22 BEGIN -->

A normal first delivery selects one hosting stack, plus all required physical, security and shared-service integrations. Repeat the same service outcomes on the other stacks for separate portability qualification. A simultaneous split-stack deployment is a different, explicitly designed service.

<!-- SOURCE-BLOCK DEL10:22 END -->

<!-- SOURCE-BLOCK DEL10:23 BEGIN -->

Included scope: architecture, detailed engineering, commissioning, tenant delivery, qualification, recovery, operations and retirement. Excluded: fabricated site approvals, guessed native configuration, live deployment, and a mandatory custom controller.

<!-- SOURCE-BLOCK DEL10:23 END -->

<!-- SOURCE-BLOCK DEL10:24 BEGIN -->

<!-- SOURCE-BLOCK DEL10:24 END -->

[Chapter index](README.md) · [Next chapter](2-deliverable-ownership-and-handoffs.md)
