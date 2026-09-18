# 2. Deliverable ownership and handoffs

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/07_Quality/prior_v1_0/00_Delivery_Map.docx) · [Chapter index](README.md)

> **Source:** DEL10 — Delivery kits v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: e332c1b37e63439169adf8b105573577fa1ea61bf32f6c3ba383dd69d83a788b -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK DEL10:25 BEGIN -->

<a id="DEL_02"></a>

<!-- SOURCE-BLOCK DEL10:25 END -->

<!-- SOURCE-BLOCK DEL10:26 BEGIN -->

The kit deliverable IDs identify working outputs; they do not renumber the 194 baseline requirements. Use the shared deliverable catalogue as the handoff checklist.

<!-- SOURCE-BLOCK DEL10:26 END -->

<!-- SOURCE-BLOCK DEL10:27 BEGIN -->

Baseline and related records: [AK §1](../../architecture/delivery-guide/1-architecture-work-plan-and-definition-of-done.md#AK_01)  •  [EK §1](../../engineering/delivery-guide/1-engineering-work-plan-and-release-boundary.md#EK_01)  •  [IK §1](../../implementation/delivery-guide/1-implementation-workplan-and-required-inputs.md#IK_01)

<!-- SOURCE-BLOCK DEL10:27 END -->

<!-- SOURCE-BLOCK DEL10:28 BEGIN -->

## Architecture

<!-- SOURCE-BLOCK DEL10:28 END -->

<!-- SOURCE-BLOCK DEL10:29 BEGIN -->

AK-01 Mandate, stakeholders and service envelope; AK-02 Requirement applicability and acceptance allocation; AK-03 High-level physical, logical and security views; AK-04 Architecture decisions and allowed variations; AK-05 Threat, co-residency and control responsibility; AK-06 Availability, recovery, capacity and location strategy; AK-07 Vendor realization and provisioning strategy; AK-08 Architecture review and engineering handoff.

<!-- SOURCE-BLOCK DEL10:29 END -->

<!-- SOURCE-BLOCK DEL10:30 BEGIN -->

## Engineering

<!-- SOURCE-BLOCK DEL10:30 END -->

<!-- SOURCE-BLOCK DEL10:31 BEGIN -->

EK-01 Site LLD and controlled design release; EK-02 Physical inventory, bill of materials and port/cable schedule; EK-03 Network, addressing, routes and ZIP paths; EK-04 Compute, storage and placement schedules; EK-05 Management, shared-service and trust interfaces; EK-06 Capacity, performance, MTU and failure calculations; EK-07 Exact stack and operation-level automation coverage; EK-08 Build, rollback and qualification design; EK-09 Engineering release and implementation handoff.

<!-- SOURCE-BLOCK DEL10:31 END -->

<!-- SOURCE-BLOCK DEL10:32 BEGIN -->

## Implementation

<!-- SOURCE-BLOCK DEL10:32 END -->

<!-- SOURCE-BLOCK DEL10:33 BEGIN -->

IK-01 Change scope, release freeze and execution authority; IK-02 Staging and installation readiness; IK-03 P0–P1 bootstrap and foundation receipts; IK-04 P2 native platform build receipts; IK-05 P3 shared-service and boundary receipts; IK-06 Restricted qualification fixture and test campaign; IK-07 G4 initial operational and recovery readiness; IK-08 P4–P5 tenant build and production activation; IK-09 As-built, defect and evidence records; IK-10 P6 maintenance, migration and retirement.

<!-- SOURCE-BLOCK DEL10:33 END -->

<!-- SOURCE-BLOCK DEL10:34 BEGIN -->


<a id="source-table-34"></a>

| Handoff | Sender must supply | Receiver must verify |
| --- | --- | --- |
| Architecture → engineering | Adopted scope, decisions, sharing matrix, requirements and service constraints. | No conflicting boundaries or unresolved decision that affects the proposed build. |
| Engineering → implementation | Controlled revision, site schedules, exact tuple, reviewed MOP and evidence plan. | No guessed addresses, default credentials, competing writers or unsupported required operation. |
| Implementation → operations | Actual topology, configuration, observed tests, support, recovery and retained obligations. | The delivered scope can be supported and recovered; required readiness existed before production activation. |

<!-- SOURCE-BLOCK DEL10:34 END -->

<!-- SOURCE-BLOCK DEL10:35 BEGIN -->

<!-- SOURCE-BLOCK DEL10:35 END -->

<!-- SOURCE-BLOCK DEL10:36 BEGIN -->

<!-- SOURCE-BLOCK DEL10:36 END -->

[Previous chapter](1-three-kits-one-controlled-delivery.md) · [Chapter index](README.md) · [Next chapter](3-acceptance-gates-and-restricted-qualification.md)
