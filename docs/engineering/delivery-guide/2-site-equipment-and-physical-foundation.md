# 2. Site, equipment and physical foundation

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/02_Engineering/Engineering_Kit.docx) · [Chapter index](README.md)

> **Source:** EK — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 0aeb8ee0a114d3ed23e97c684cc9812a0fa6ea5252e49f0c902132bf4e053a7d -->
<!-- SOURCE-BLOCK EK:25 BEGIN -->

<a id="EK_02"></a>

<!-- SOURCE-BLOCK EK:25 END -->

<!-- SOURCE-BLOCK EK:26 BEGIN -->

The physical design supplies the inventory behind the logical diagrams. Shared power, rack, uplink, storage or management dependencies must be visible before redundancy is claimed.

<!-- SOURCE-BLOCK EK:26 END -->

<!-- SOURCE-BLOCK EK:27 BEGIN -->

Baseline and related records: [RA §3](../../architecture/reference/3-system-context-and-physical-hosting-topology.md#RA_s_003)  •  [RA §4](../../architecture/reference/4-hosting-cells-resource-pools-and-failure-boundaries.md#RA_s_004)  •  [RA §5](../../architecture/reference/5-physical-fabric-and-platform-attachment.md#RA_s_005)  •  [ET §2](../../templates/lld/2-physical-inventory-facility-and-port-schedule.md#ET_02)

<!-- SOURCE-BLOCK EK:27 END -->

<!-- SOURCE-BLOCK EK:28 BEGIN -->


<a id="source-table-28"></a>

| Schedule | Required fields / engineering checks |
| --- | --- |
| Equipment and bill of materials | Asset role, model/quantity, CPU/memory/storage/NIC, firmware, rails/optics/cables, support/entitlement, spare policy and procurement assumption. |
| Rack and facility allocation | Rack/U position, power-feed assignment, load/cooling capacity, access restrictions, dependency group and facility acceptance reference. |
| Ports and cables | Link ID; both devices and ports; medium/speed/length; optic compatibility; host team or LAG; VLAN/transport role; labeling and test record. |
| Fabric and borders | Topology, loopbacks/link addresses, ASNs, neighbour/import/export policy, ECMP, optional EVPN RD/RT/VNI authority and external handoff. |
| OOB and management | Independent access path, actual switches/interfaces, permitted targets, privileged path and recovery dependency. |
| Staging and support | Trusted firmware/images, secured initial configuration, asset matching, diagnostic handling and manufacturer-specific install/replacement method. |

<!-- SOURCE-BLOCK EK:28 END -->

<!-- SOURCE-BLOCK EK:29 BEGIN -->

<!-- SOURCE-BLOCK EK:29 END -->

<!-- SOURCE-BLOCK EK:30 BEGIN -->

Choose qualified MLAG, EVPN multihoming or another supported host attachment pattern. Document peer-link/keepalive or Ethernet-segment behaviour, orphan endpoints, split-brain containment and supported drain/reload order. Do not equate matching feature names with interoperability.

<!-- SOURCE-BLOCK EK:30 END -->

<!-- SOURCE-BLOCK EK:31 BEGIN -->

Physical installation and electrical/facility work are performed by qualified personnel following site and manufacturer procedures. This kit records approvals, labels and acceptance; it does not replace lifting, electrical, optical or equipment safety instructions.

<!-- SOURCE-BLOCK EK:31 END -->

<!-- SOURCE-BLOCK EK:32 BEGIN -->

<!-- SOURCE-BLOCK EK:32 END -->

[Previous chapter](1-engineering-work-plan-and-release-boundary.md) · [Chapter index](README.md) · [Next chapter](3-addressing-routing-policy-and-attachment-schedules.md)
