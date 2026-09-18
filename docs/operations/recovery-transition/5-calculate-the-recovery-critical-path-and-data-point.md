# 5. Calculate the recovery critical path and data point

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/03_Implementation/Operations_Recovery_and_Transition_Playbook.docx) · [Chapter index](README.md)

> **Source:** OPS — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: d935614ed1639f56859dfe29bc226af4cfced35bafeb7d544440577ddaa95a09 -->
<!-- SOURCE-BLOCK OPS:54 BEGIN -->

<a id="OPS_05"></a>

<!-- SOURCE-BLOCK OPS:54 END -->

<!-- SOURCE-BLOCK OPS:55 BEGIN -->

The following schedule is a local planning example. It is not measured performance, an approved target or a prediction for any vendor platform.

<!-- SOURCE-BLOCK OPS:55 END -->

<!-- SOURCE-BLOCK OPS:56 BEGIN -->

Design basis and related records: [QUAL §4](../../assurance/site-qualification/4-service-parameter-and-requirement-decisions.md#QUAL_s_004)  •  [SVC §6](../../architecture/shared-services/6-failure-recovery-migration-and-failback-topology.md#SVC_s_006)  •  [EK §6](../../engineering/delivery-guide/6-capacity-mtu-performance-and-failure-analysis.md#EK_06)

<!-- SOURCE-BLOCK OPS:56 END -->

<!-- SOURCE-BLOCK OPS:57 BEGIN -->


<a id="source-table-57"></a>

| Example activity | Minutes | Dependency / elapsed finish |
| --- | --- | --- |
| Detect and declare | 10 | Start 0 → finish 10 |
| Select recovery authority | 5 | After detection → finish 15 |
| Recover minimum trust / bootstrap | 25 | After decision → finish 40 |
| Network foundation / storage foundation | 20 / 40 | Illustratively parallel after bootstrap → finish 60 / 80 |
| Restore service data | 35 | After both foundations → finish 115 |
| Validate security and useful data | 20 | After restore → finish 135 |
| Controlled access cutover | 5 | After validation → finish 140 |

<!-- SOURCE-BLOCK OPS:57 END -->

<!-- SOURCE-BLOCK OPS:58 BEGIN -->

<!-- SOURCE-BLOCK OPS:58 END -->

<!-- SOURCE-BLOCK OPS:59 BEGIN -->

With those dependencies, elapsed recovery is 10 + 5 + 25 + max(20, 40) + 35 + 20 + 5 = 140 minutes. Against an illustrative 180-minute target, planning margin is 40 minutes. Do not add both parallel branches or assume independence when they share people, storage, credentials or network recovery. If the two foundation tasks must run serially, the same example becomes 160 minutes with 20 minutes of margin.

<!-- SOURCE-BLOCK OPS:59 END -->

<!-- SOURCE-BLOCK OPS:60 BEGIN -->

Include decision, queue, transfer, validation and exposure time when they fall inside the agreed RTO boundary. The actual service defines the start and end events. Rehearsal evidence determines feasibility; the calculation only reveals assumptions and dependencies.

<!-- SOURCE-BLOCK OPS:60 END -->

<!-- SOURCE-BLOCK OPS:61 BEGIN -->

## RPO is a data-state measurement

<!-- SOURCE-BLOCK OPS:61 END -->

<!-- SOURCE-BLOCK OPS:62 BEGIN -->

If service loss occurs at 12:00 and the latest verified recoverable consistency point is 11:45, the recovered-data age is 15 minutes. A job that finished at 11:55 does not prove an 11:55 data point. Record capture/transaction consistency, replication lag, copy integrity and the actual accepted state. These timestamps are illustrative.

<!-- SOURCE-BLOCK OPS:62 END -->

<!-- SOURCE-BLOCK OPS:63 BEGIN -->

A recovery target can be met while an availability objective is breached. Report both; RTO is not an automatic exclusion from service downtime.

<!-- SOURCE-BLOCK OPS:63 END -->

<!-- SOURCE-BLOCK OPS:64 BEGIN -->

Continue with: [QCP §5](../../assurance/qualification-campaign/5-separate-safe-failure-service-continuity-and-recovery.md#QCP_05)  •  [OPS §8](8-accept-operational-responsibility-for-the-delivered-scope.md#OPS_08)

<!-- SOURCE-BLOCK OPS:64 END -->

<!-- SOURCE-BLOCK OPS:65 BEGIN -->

<!-- SOURCE-BLOCK OPS:65 END -->

[Previous chapter](4-recover-the-service-in-dependency-order.md) · [Chapter index](README.md) · [Next chapter](6-migrate-and-fail-back-without-conflicting-writers.md)
