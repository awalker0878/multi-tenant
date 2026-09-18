# 9. Operational handover, recovery, migration and retirement

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/03_Implementation/Implementation_Kit.docx) · [Chapter index](README.md)

> **Source:** IK — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: b16b8843bfbafd1b417d611903f5b8038f4794efd4f22c995bee1cb36f9ebb41 -->
<a id="IK_09"></a>

Use RB-08 and RB-09. Treat change, recovery and retirement as infrastructure lifecycle operations with data and security consequences.

Baseline and related records: [RA §27](../../architecture/reference/27-recovery-migration-and-retirement.md#RA_s_027)  •  [SVC §6](../../architecture/shared-services/6-failure-recovery-migration-and-failback-topology.md#SVC_s_006)  •  [QUAL §7](../../assurance/site-qualification/7-operating-accountability-handover-and-change.md#QUAL_s_007)  •  [IT §8](../../templates/implementation-mop/8-migration-retirement-and-retained-data.md#IT_08)


<a id="source-table-83"></a>

| Lifecycle outcome | Required work | Acceptance record |
| --- | --- | --- |
| Operational handover | Confirm support/escalation, actual as-built, telemetry, incident authority, credential custody, capacity limits and maintenance. | Operations accepts a specific service envelope with current evidence, not receipt of generic documentation. |
| Restore or site recovery | Establish authority and fence ambiguous writers; recover trust/catalogue/keys and foundations; restore isolated data and dependencies. | Measured consistency point and recovery time; useful data and required security verified before reconnection. |
| Cross-platform migration | Qualify target, transfer state through bounded approved access, verify device/driver/boot/key/data compatibility and final consistency. | Controlled cutover and feasibility of return after new writes; Terraform is not the data conversion engine. |
| Retirement | Reconcile consumers and holds, create required recovery/export first, withdraw live routes/grants and remove only owned eligible resources. | Remaining copies, keys, owners and disposition are explicit; sanitization receipt before reuse. |
| Continuing acceptance | Revisit actual service targets, exception expiry, support, resource headroom and periodic recovery after material change. | Current scope accepted or restricted; historical authorization is not rewritten. |

Kit completion means the working records and methods are available. Site completion requires filled values, actual execution evidence, independent review where required and decisions by the designated authorities.

[Previous chapter](8-interrupted-work-brownfield-adoption-and-change.md) · [Chapter index](README.md)
