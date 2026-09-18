# 7. Threat, sharing and responsibility review

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/01_Architecture/HLD_and_Architecture_Review_Template.docx) · [Chapter index](README.md)

> **Source:** AT — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 911b87e6a36d903a12535d16d75f1875c0cefb6b72c462895f7c2559b556708c -->
<!-- SOURCE-BLOCK AT:67 BEGIN -->

<a id="AT_07"></a>

<!-- SOURCE-BLOCK AT:67 END -->

<!-- SOURCE-BLOCK AT:68 BEGIN -->

Working record for AK-05. Complete the responses and attach the referenced evidence or drawing; do not replace an unresolved item with an unsupported assumption.

<!-- SOURCE-BLOCK AT:68 END -->

<!-- SOURCE-BLOCK AT:69 BEGIN -->

Baseline and related records: [RA §6](../../architecture/reference/6-management-platform-control-and-out-of-band-access.md#RA_s_006)  •  [RA §7](../../architecture/reference/7-tenant-environments-and-security-domain-placement.md#RA_s_007)  •  [QUAL §6](../../assurance/site-qualification/6-control-inheritance-assurance-and-organizational-interfaces.md#QUAL_s_006)

<!-- SOURCE-BLOCK AT:69 END -->

<!-- SOURCE-BLOCK AT:70 BEGIN -->


<a id="source-table-70"></a>

| Record / decision | What to enter | Working response |
| --- | --- | --- |
| Threat/failure assumptions | Compromised workload/admin/host/service, misconfiguration, outage and partition scope. | {{AT\_THREATS}} |
| Co-residency matrix | Allowed sharing per host, cluster, storage, edge, management, backup and keys. | {{AT\_SHARING}} |
| Mandatory enforcement | Control location, owner and behaviour during failure/change. | {{AT\_ENFORCEMENT}} |
| Residual risk | Remaining risk, affected service and actual accepting authority/conditions. | {{AT\_RESIDUAL}} |
| Inherited controls | Source service, evidence scope/time and inherited versus tenant obligation. | {{AT\_INHERIT}} |
| Sensitive lifecycle | Support access, diagnostics, copies, retention and disposition authority. | {{AT\_LIFECYCLE}} |

<!-- SOURCE-BLOCK AT:70 END -->

<!-- SOURCE-BLOCK AT:71 BEGIN -->

<!-- SOURCE-BLOCK AT:71 END -->

<!-- SOURCE-BLOCK AT:72 BEGIN -->

Reviewer: a label or logical segmentation claim is not proof of physical independence or protection against privileged compromise.

<!-- SOURCE-BLOCK AT:72 END -->

<!-- SOURCE-BLOCK AT:73 BEGIN -->

Record status: Draft / In review / Accepted for stated scope / Returned for revision. Use the actual review record, not this prompt, as authority.

<!-- SOURCE-BLOCK AT:73 END -->

<!-- SOURCE-BLOCK AT:74 BEGIN -->

<!-- SOURCE-BLOCK AT:74 END -->

[Previous chapter](6-architecture-decision-record.md) · [Chapter index](README.md) · [Next chapter](8-reliability-capacity-and-exit-design.md)
