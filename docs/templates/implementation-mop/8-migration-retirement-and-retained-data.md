# 8. Migration, retirement and retained data

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/03_Implementation/MOP_Test_and_Handover_Template.docx) · [Chapter index](README.md)

> **Source:** IT — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 9a7dd8df4a5abf6482f206cae2d074444ac6fa812bbe4bace970a4de059da370 -->
<!-- SOURCE-BLOCK IT:66 BEGIN -->

<a id="IT_08"></a>

<!-- SOURCE-BLOCK IT:66 END -->

<!-- SOURCE-BLOCK IT:67 BEGIN -->

Keep live-service retirement distinct from disposal of all retained data.

<!-- SOURCE-BLOCK IT:67 END -->

<!-- SOURCE-BLOCK IT:68 BEGIN -->

Baseline and related records: [IK §9](../../implementation/delivery-guide/9-operational-handover-recovery-migration-and-retirement.md#IK_09)  •  [WD §12](../../solutions/internal-protected-workload/12-failure-and-partition-decision-schedule.md#WD14_S12)

<!-- SOURCE-BLOCK IT:68 END -->

<!-- SOURCE-BLOCK IT:69 BEGIN -->


<a id="source-table-69"></a>

| Record / decision | What to enter | Working response |
| --- | --- | --- |
| Lifecycle scope | Change/migration/retirement ID, source/target owners, resources, data classification and dependencies. | {{IT\_LIFE\_SCOPE}} |
| Transfer and cutover | Supported image/data method, bounded paths, final consistency, writer ownership, acceptance and return feasibility. | {{IT\_CUTOVER}} |
| Retention and copies | Copy/replica/snapshot/backups, holds, owners, locations, necessary keys and remaining authorized access. | {{IT\_COPIES}} |
| Live cleanup | Withdraw exposures/routes/policies/names/grants, resolve shared resources, quarantine addresses and verify residuals. | {{IT\_LIVE\_CLEAN}} |
| Sanitization and reuse | Approved method, media/key scope, actual verification and receipt; record retained exceptions truthfully. | {{IT\_SANITIZE}} |
| Final acceptance | Data/operations/security disposition, continuing obligations, retained evidence and final service closure. | {{IT\_LIFE\_ACCEPT}} |

<!-- SOURCE-BLOCK IT:69 END -->

<!-- SOURCE-BLOCK IT:70 BEGIN -->

<!-- SOURCE-BLOCK IT:70 END -->

<!-- SOURCE-BLOCK IT:71 BEGIN -->

Blank fields and unissued decisions are blockers for the affected action. Record actual evidence and authority; examples elsewhere in the library do not populate these fields.

<!-- SOURCE-BLOCK IT:71 END -->

[Previous chapter](7-gate-decision-and-production-activation.md) · [Chapter index](README.md)
