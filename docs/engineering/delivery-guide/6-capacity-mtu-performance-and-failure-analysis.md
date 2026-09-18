# 6. Capacity, MTU, performance and failure analysis

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/02_Engineering/Engineering_Kit.docx) · [Chapter index](README.md)

> **Source:** EK — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 0aeb8ee0a114d3ed23e97c684cc9812a0fa6ea5252e49f0c902132bf4e053a7d -->
<a id="EK_06"></a>

The engineering workbook contains labelled calculators and a separate worked fixture. Inputs are editable; derived values are formulas. Unknown real capacity remains unknown rather than silently becoming zero or a guessed safe default.

Baseline and related records: [QUAL §3](../../assurance/site-qualification/3-capacity-service-envelopes-and-growth-triggers.md#QUAL_s_003)  •  [WD §11](../../solutions/internal-protected-workload/11-test-resource-capacity-and-mtu-accounting.md#WD14_S11)  •  [NET §5](../fabric/5-mtu-performance-and-failure-engineering.md#NET_s_005)  •  [ET §7](../../templates/lld/7-capacity-mtu-and-failure-calculations.md#ET_07)


<a id="source-table-61"></a>

| Calculation | Basis and review requirement |
| --- | --- |
| Surviving service capacity | Measured sustainable capacity remaining after the covered failure, minus operational reserve and existing committed demand. Test all limiting units independently. |
| New demand | Workload plus required temporary test resources and provider overhead. Account for existing commitment once; do not add usage already included in that commitment. |
| Headroom and growth | New demand must fit every applicable bottleneck. Record lead time and forecast trigger; a free host cannot compensate for exhausted inspected sessions. |
| Storage | Capacity/performance under protection overhead, rebuild, copies and retention; specify raw versus usable units and evidence. |
| MTU | Workload packet plus actual inner framing, encapsulation, outer headers and options; compare against the smallest active/surviving path limit. |
| Recovery timing | RTO dependency sequence and decision/cutover time; RPO from the recoverable consistency point; constraints remain enforced. |

The WD fixture has four permanent endpoints and one sequential temporary probe: 10 vCPU, 20 GiB guest memory and 400 GiB requested virtual disks at peak. These are not host minima or physical-storage totals. Provider, edge, management, copies and failure reserves are additional.

The basic VXLAN arithmetic in WD is one encapsulation case, not a universal tunnel allowance. Record inner tags, outer family, Geneve/options, IPsec or nested encapsulation separately. Link-frame MTU and outer-IP MTU may be reported differently by products.

[Previous chapter](5-management-and-shared-service-interfaces.md) · [Chapter index](README.md) · [Next chapter](7-supported-stack-and-provisioning-operation-coverage.md)
