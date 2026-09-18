# 3. VMware and NSX realization card

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/02_Engineering/Vendor_Realization_Cards.docx) · [Chapter index](README.md)

> **Source:** VRC — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 5e453a432a4b6c5af7d75ba266945bdb9e01118757cbeec1e15d81f92be32ab0 -->
<!-- SOURCE-BLOCK VRC:33 BEGIN -->

<a id="VC_03"></a>

<!-- SOURCE-BLOCK VRC:33 END -->

<!-- SOURCE-BLOCK VRC:34 BEGIN -->

Reference mapping: protected vCenter/ESXi and NSX management, eligible compute/storage pools, independent domain routing and an explicitly isolated upstream path to the required ZIP.

<!-- SOURCE-BLOCK VRC:34 END -->

<!-- SOURCE-BLOCK VRC:35 BEGIN -->

Baseline and related records: [RA §17](../../architecture/reference/17-vmware-and-nsx-hosting-stack-reference-realization.md#RA_s_017)  •  [VND §4](../platform-realizations/4-vmware-nsx-isolated-upstream-routing-and-enforcement.md#VND_s_004)  •  [WD §8](../../solutions/internal-protected-workload/8-mapping-the-schedules-into-each-vendor-stack.md#WD14_S08)

<!-- SOURCE-BLOCK VRC:35 END -->

<!-- SOURCE-BLOCK VRC:36 BEGIN -->


<a id="source-table-36"></a>

| Build concern | Specific engineering decision / receipt |
| --- | --- |
| Installation and transport | Actual vCenter/ESXi/NSX versions and hardware compatibility; transport nodes/zones, Edge placement, TEP/uplink reachability and management. |
| Routing topology | Map Tier-1, distributed/service routing, Tier-0/VRF or approved alternative, advertisements, native routes and exact boundary next hops. |
| Stateful enforcement and HA | Locate mandatory DFW and boundary functions; choose supported HA mode, state synchronization, return symmetry and failure load. |
| Pools and data | Actual host eligibility/affinity, supported vMotion/restart, datastore/storage policy, images/virtual security devices and backup/key dependencies. |
| Provisioning sequence | P2 compute/storage/NSX transport → scope and isolated upstream capacity → denied segments/gateways → policy → VM/data → service and path checks. |
| Acceptance / failure | No unauthorized native/inter-VRF route; same-host rules, Edge/uplink loss, maintenance placement, support limits and useful restore. |

<!-- SOURCE-BLOCK VRC:36 END -->

<!-- SOURCE-BLOCK VRC:37 BEGIN -->

<!-- SOURCE-BLOCK VRC:37 END -->

<!-- SOURCE-BLOCK VRC:38 BEGIN -->

Technical review item KIT-TN-01: Broadcom KB 442835 describes Tier-0 VRF incompatibility with an active-active stateful parent Tier-0. Reconcile this limitation with the selected release and architecture before choosing HA mode; do not assume every VRF/stateful combination is supported. \[K09\]

<!-- SOURCE-BLOCK VRC:38 END -->

<!-- SOURCE-BLOCK VRC:39 BEGIN -->

External mechanism context: [K09 — Broadcom KB 442835 — Tier-0 VRF and active-active stateful HA](https://knowledge.broadcom.com/external/article/442835/cannot-add-tier0-vrf-gateway-to-a-tier0.html)

<!-- SOURCE-BLOCK VRC:39 END -->

<!-- SOURCE-BLOCK VRC:40 BEGIN -->

The frozen RA remains unchanged. This kit adds a support check, not a command to change a live gateway. An HA-mode change needs separate disruption, session and recovery analysis.

<!-- SOURCE-BLOCK VRC:40 END -->

<!-- SOURCE-BLOCK VRC:41 BEGIN -->

<!-- SOURCE-BLOCK VRC:41 END -->

[Previous chapter](2-nutanix-realization-card.md) · [Chapter index](README.md) · [Next chapter](4-openstack-realization-card.md)
