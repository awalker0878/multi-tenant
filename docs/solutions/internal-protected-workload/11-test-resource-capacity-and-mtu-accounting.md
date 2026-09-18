# 11. Test-resource, capacity and MTU accounting

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/07_Worked_Infrastructure_Design_and_Acceptance_v1_4.docx) · [Chapter index](README.md)

> **Source:** WD — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: e4a2e42888349b5967f7b3174c78e53171728b13e99e4c78bc3cfb53310f68db -->
<a id="WD14_S11"></a>

The permanent fixture has one endpoint per domain. That cannot alone prove isolation between two endpoints inside the same domain. Add one controlled temporary probe to a domain, test the applicable same-host and cross-host placements, then retire or move the probe through an authorized re-creation sequence. Peak test endpoint count is five for sequential testing; four simultaneous extra probes would make eight. Tests on disallowed co-residency use the actual permitted topology rather than forcing a forbidden host placement.

Illustrative requested guest capacity is four endpoints at 2 vCPU, 4 GiB memory and a 40 GiB boot disk each, plus a 100 GiB test data disk on each data endpoint: 8 vCPU, 16 GiB guest memory and 360 GiB requested virtual disk capacity. One sequential probe adds 2 vCPU, 4 GiB and 40 GiB: peak 10 vCPU, 20 GiB and 400 GiB. These are example fixture demands, not production sizes, host counts, physical storage requirements or qualified platform minima.

Provider services, managers, edges, replicas, snapshots, backup retention, rebuild/maintenance headroom and hypervisor overhead are additional. Reservation accounting must not count the same allocation again as consumption. Admission is the conjunction of all applicable resource limits; a spare domain attachment cannot compensate for insufficient inspected session or storage-rebuild capacity.

The MTU example uses a workload IP packet carried in an untagged inner Ethernet frame, basic VXLAN and UDP. For outer IPv4 without options, the additional outer-IP packet budget relative to the workload IP packet is 14 + 8 + 8 + 20 = 50 bytes. Outer IPv6 makes it 70 bytes. An inner VLAN tag adds another 4 bytes. Outer link framing is handled separately according to the equipment's MTU definition. The example is derived from packet fields, not a vendor setting. \[R14-06\]

Geneve options, IPsec, nested tunnels, outer extension headers or other encapsulations require their own budget. Do not reuse a fixed VXLAN value. Qualify the smallest effective MTU across every active and surviving path, including gateway, security edge and recovery connections.


<a id="source-table-121"></a>

| Illustrative case | Arithmetic | Consequence |
| --- | --- | --- |
| Four permanent endpoints | 4 × 2 vCPU; 4 × 4 GiB; 4 × 40 + 2 × 100 GiB disks | 8 vCPU, 16 GiB memory, 360 GiB requested virtual disks, before provider overhead and protection. |
| One temporary sequential probe | Permanent fixture + 2 vCPU + 4 GiB + 40 GiB | Peak 10 vCPU, 20 GiB memory, 400 GiB virtual disks. |
| 1450-byte workload IP; basic IPv4 VXLAN | 1450 + 50 = 1500-byte outer IP packet | Fits a 1500-byte outer IP limit only under these assumptions. |
| 1450-byte workload IP; IPv6 outer | 1450 + 70 = 1520 bytes | Does not fit the same 1500-byte outer IP limit. |
| 1500 outer IP limit; IPv6 VXLAN | 1500 − 70 = 1430-byte maximum workload IP packet | Illustrative bound; confirm actual encapsulation, tagging and product behavior. |
| 1450 workload; tagged inner Ethernet; IPv4 outer | 1450 + 50 + 4 = 1504 bytes | An unaccounted inner tag changes the result; do not silently drop or fragment. |

Related documents: [QUAL — Surviving capacity and admission](../../assurance/site-qualification/README.md#V14_QUAL_START)  \|  [NET — Layer-specific MTU method](../../engineering/fabric/README.md#V14_NET_START)  \|  [VND — Fixture and co-residency](../../engineering/platform-realizations/README.md#V14_VND_START)

[Previous chapter](10-resource-ownership-protection-and-change-receipts.md) · [Chapter index](README.md) · [Next chapter](12-failure-and-partition-decision-schedule.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0021 — Offer address families explicitly across the whole service path](../../adr/0021-offer-address-families-explicitly-across-the-whole-service-path.md)
- [ADR-0030 — Admit demand against every surviving-capacity bottleneck](../../adr/0030-admit-demand-against-every-surviving-capacity-bottleneck.md)

<!-- END GENERATED DECISION LINKS -->
