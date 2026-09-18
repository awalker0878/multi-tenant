# 2. Resource and boundary schedule

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/04_Shared/Worked_Delivery_Example.docx) · [Chapter index](README.md)

> **Source:** WDE — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: ae4ea65ea564fe848f214f5154ca4b67726eb6628d07a4b4f7714210e49ccd0d -->
<!-- SOURCE-BLOCK WDE:23 BEGIN -->

<a id="EX_02"></a>

<!-- SOURCE-BLOCK WDE:23 END -->

<!-- SOURCE-BLOCK WDE:24 BEGIN -->

The example selects one platform for the first campaign. Repeating it on another platform is a separate comparison, not a simultaneous three-platform deployment.

<!-- SOURCE-BLOCK WDE:24 END -->

<!-- SOURCE-BLOCK WDE:25 BEGIN -->

Baseline and related records: [WD §3](../internal-protected-workload/3-component-and-dependency-schedule.md#WD14_S03)  •  [WD §4](../internal-protected-workload/4-tenant-attachment-and-address-schedule.md#WD14_S04)  •  [WD §5](../internal-protected-workload/5-dedicated-handoff-inventory-and-route-ownership.md#WD14_S05)

<!-- SOURCE-BLOCK WDE:25 END -->

<!-- SOURCE-BLOCK WDE:26 BEGIN -->


<a id="source-table-26"></a>

| Domain / endpoint | Illustrative prefix and gateway | Boundary and owner |
| --- | --- | --- |
| D01O / processor-01 | 192.0.2.0/27; gateway .1; host .10 | Tenant-01; NG-D01O → A01O → EC-01. |
| D01R / data-01 | 192.0.2.32/27; gateway .33; host .42 | Tenant-01; NG-D01R → A01R → EC-01. |
| D02O / processor-02 | 192.0.2.64/27; gateway .65; host .74 | Tenant-02; NG-D02O → A02O → EC-02. |
| D02R / data-02 | 192.0.2.96/27; gateway .97; host .106 | Tenant-02; NG-D02R → A02R → EC-02. |
| Provider consumption | 203.0.113.128/27; SE-01 .129; SE-02 .130 | Service endpoints behind security contexts, not a shared native tenant-gateway segment. |

<!-- SOURCE-BLOCK WDE:26 END -->

<!-- SOURCE-BLOCK WDE:27 BEGIN -->

<!-- SOURCE-BLOCK WDE:27 END -->

<!-- SOURCE-BLOCK WDE:28 BEGIN -->


<a id="source-table-28"></a>

| Link | EC endpoint | Native gateway / service edge |
| --- | --- | --- |
| A01O · 198.51.100.0/30 | 198.51.100.1 | NG-D01O 198.51.100.2 |
| A01R · 198.51.100.4/30 | 198.51.100.5 | NG-D01R 198.51.100.6 |
| SH-01 · 198.51.100.16/30 | EC-01 198.51.100.17 | SE-01 198.51.100.18 |

<!-- SOURCE-BLOCK WDE:28 END -->

<!-- SOURCE-BLOCK WDE:29 BEGIN -->

<!-- SOURCE-BLOCK WDE:29 END -->

<!-- SOURCE-BLOCK WDE:30 BEGIN -->

All addresses are WD documentation examples. Replace them through authoritative site allocation. These link sizes and logical gateway addresses do not establish native product support or physical port counts.

<!-- SOURCE-BLOCK WDE:30 END -->

<!-- SOURCE-BLOCK WDE:31 BEGIN -->

Use EX\_Routes4, EX\_Routes6 and EX\_Flows in the engineering workbook for the full inherited reference schedules. Actual site schedules occupy separate blank working sheets, preventing example values from being mistaken for allocations.

<!-- SOURCE-BLOCK WDE:31 END -->

<!-- SOURCE-BLOCK WDE:32 BEGIN -->

<!-- SOURCE-BLOCK WDE:32 END -->

[Previous chapter](1-trace-one-decision-into-engineering-and-evidence.md) · [Chapter index](README.md) · [Next chapter](3-forward-route-return-route-and-service-permission.md)
