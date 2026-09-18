# 8. Reliability, capacity and exit design

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/01_Architecture/HLD_and_Architecture_Review_Template.docx) · [Chapter index](README.md)

> **Source:** AT — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 911b87e6a36d903a12535d16d75f1875c0cefb6b72c462895f7c2559b556708c -->
<a id="AT_08"></a>

Working record for AK-06. Complete the responses and attach the referenced evidence or drawing; do not replace an unresolved item with an unsupported assumption.

Baseline and related records: [RA §14](../../architecture/reference/14-availability-multi-site-operation-and-recovery-topology.md#RA_s_014)  •  [RA §26](../../architecture/reference/26-operating-model-capacity-and-observability.md#RA_s_026)  •  [RA §27](../../architecture/reference/27-recovery-migration-and-retirement.md#RA_s_027)


<a id="source-table-78"></a>

| Record / decision | What to enter | Working response |
| --- | --- | --- |
| V08 failure/recovery view | Covered failure set, survivors, quorum, fencing and recovery site dependencies. | {{AT\_V08}} |
| Service measurement | Indicator, observation boundary/window and maintenance treatment. | {{AT\_SLO}} |
| Recovery measurement | RTO start/end, RPO consistency point and useful-data acceptance. | {{AT\_RECOVERY}} |
| Capacity strategy | Demand, shared resource bottlenecks, operational reserve and expansion triggers. | {{AT\_CAPACITY}} |
| Location/control | Primary/copy/log/diagnostic/control/admin/key restrictions and authorities. | {{AT\_LOCATION}} |
| Exit feasibility | Target options, conversion limits, key/identity dependencies and rehearsal evidence needed. | {{AT\_EXIT}} |

Reviewer: impact classification is not an uptime promise; every offered recovery promise has a corresponding qualification and initial-readiness condition.

Record status: Draft / In review / Accepted for stated scope / Returned for revision. Use the actual review record, not this prompt, as authority.

[Previous chapter](7-threat-sharing-and-responsibility-review.md) · [Chapter index](README.md) · [Next chapter](9-vendor-realization-and-provisioning-strategy.md)
