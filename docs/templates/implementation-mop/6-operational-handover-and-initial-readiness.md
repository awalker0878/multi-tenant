# 6. Operational handover and initial readiness

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/03_Implementation/MOP_Test_and_Handover_Template.docx) · [Chapter index](README.md)

> **Source:** IT — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 9a7dd8df4a5abf6482f206cae2d074444ac6fa812bbe4bace970a4de059da370 -->
<a id="IT_06"></a>

Complete the applicable initial readiness before production G3. A later exercise cannot retroactively supply missing initial readiness.

Baseline and related records: [IK §7](../../implementation/delivery-guide/7-tenant-provisioning-and-controlled-production-activation.md#IK_07)  •  [QUAL §7](../../assurance/site-qualification/7-operating-accountability-handover-and-change.md#QUAL_s_007)


<a id="source-table-55"></a>

| Record / decision | What to enter | Working response |
| --- | --- | --- |
| Service ownership | Named operations/service/data/security owners, escalation, on-call and supplier support route. | {{IT\_OPS\_OWNER}} |
| As-built and service limits | Accepted topology/configuration, supported versions, capacity/failure envelope, actual SLO/RTO/RPO and exceptions. | {{IT\_SERVICE}} |
| Monitoring and incidents | Event/health coverage, alert recipients, loss handling, containment and explicit release authority. | {{IT\_MONITORING}} |
| Trust and protection | Custody references, tested access, keys/catalogue, required restore evidence, holds and retention responsibilities. | {{IT\_CUSTODY}} |
| Maintenance and continuity | Approved patch/change process, compatible recovery methods, scheduling constraints and runbook location. | {{IT\_MAINT}} |
| Initial readiness decision | Actual G4 initial authority, scope, reviewed evidence, conditions, validity and signature reference. | {{IT\_G4}} |

Blank fields and unissued decisions are blockers for the affected action. Record actual evidence and authority; examples elsewhere in the library do not populate these fields.

[Previous chapter](5-recovery-exercise-and-data-acceptance.md) · [Chapter index](README.md) · [Next chapter](7-gate-decision-and-production-activation.md)
