# 5. Service resilience, capacity and portability

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/01_Architecture/Architecture_Kit.docx) · [Chapter index](README.md)

> **Source:** AK — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: f0cd99f187d5f883e0f752e07de20f8878bef02fa1d0b36817674ef59bfd9802 -->
<!-- SOURCE-BLOCK AK:52 BEGIN -->

<a id="AK_05"></a>

<!-- SOURCE-BLOCK AK:52 END -->

<!-- SOURCE-BLOCK AK:53 BEGIN -->

Specify the service promise before calculating equipment. The engineering team then proves feasibility using the actual component combination and a common failure/load basis.

<!-- SOURCE-BLOCK AK:53 END -->

<!-- SOURCE-BLOCK AK:54 BEGIN -->

Baseline and related records: [RA §14](../reference/14-availability-multi-site-operation-and-recovery-topology.md#RA_s_014)  •  [RA §26](../reference/26-operating-model-capacity-and-observability.md#RA_s_026)  •  [RA §27](../reference/27-recovery-migration-and-retirement.md#RA_s_027)  •  [AT §8](../../templates/hld/8-reliability-capacity-and-exit-design.md#AT_08)

<!-- SOURCE-BLOCK AK:54 END -->

<!-- SOURCE-BLOCK AK:55 BEGIN -->


<a id="source-table-55"></a>

| Architectural decision | Engineering evidence it drives |
| --- | --- |
| Covered failure set | Enumerated nodes/racks/links/partitions and common dependencies; available survivor capacity under each case. |
| Service indicator and error treatment | Explicit measurement boundary, success criterion, window, maintenance accounting and alert owner. |
| Recovery objective | RTO start/end, recoverable consistency point for RPO, key/catalogue dependencies and isolated acceptance. |
| Data/control location and access | Locations of primary data, copies, logs, diagnostics, managers, support and keys, separately recorded. |
| Capacity on demand | Commissioned service-class capacity, reservations, expansion lead time and blocking bottlenecks—not merely free cores. |
| Portability and exit | Alternative-platform build, disk/data conversion limits, identity/key rebinding, support/skills and observed recovery. |

<!-- SOURCE-BLOCK AK:55 END -->

<!-- SOURCE-BLOCK AK:56 BEGIN -->

<!-- SOURCE-BLOCK AK:56 END -->

<!-- SOURCE-BLOCK AK:57 BEGIN -->

Portability has distinct claims: equivalent deployment, simultaneous composite use and migration of workload/data state. Qualify the specific claim. The same logical request on two platforms does not prove safe live migration or identical backup formats.

<!-- SOURCE-BLOCK AK:57 END -->

<!-- SOURCE-BLOCK AK:58 BEGIN -->

Decision quality check: the architecture states what must survive and recover, while the LLD names the actual resources that provide it. Missing evidence results in an excluded or unqualified service capability, not an invented guarantee.

<!-- SOURCE-BLOCK AK:58 END -->

<!-- SOURCE-BLOCK AK:59 BEGIN -->

<!-- SOURCE-BLOCK AK:59 END -->

[Previous chapter](4-security-management-and-co-residency-decisions.md) · [Chapter index](README.md) · [Next chapter](6-vendor-realization-and-provisioning-strategy.md)
