# 4. VMware/NSX: commission transport, compute and edge roles

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/02_Engineering/Platform_Engineering_and_Build_Specifications.docx) · [Chapter index](README.md)

> **Source:** PBS — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 8c2dd9e86b4ea021922777a963534c6b52d85dff8ee398c3a12cc81287356643 -->
<!-- SOURCE-BLOCK PBS:50 BEGIN -->

<a id="PBS_04"></a>

<!-- SOURCE-BLOCK PBS:50 END -->

<!-- SOURCE-BLOCK PBS:51 BEGIN -->

The platform foundation identifies distributed forwarding, Edge-hosted service functions and external boundary enforcement separately.

<!-- SOURCE-BLOCK PBS:51 END -->

<!-- SOURCE-BLOCK PBS:52 BEGIN -->

Design basis and related records: [RA §17](../../architecture/reference/17-vmware-and-nsx-hosting-stack-reference-realization.md#RA_s_017)  •  [VND §4](../platform-realizations/4-vmware-nsx-isolated-upstream-routing-and-enforcement.md#VND_s_004)  •  [VC §3](../vendor-cards/3-vmware-and-nsx-realization-card.md#VC_03)

<!-- SOURCE-BLOCK PBS:52 END -->

<!-- SOURCE-BLOCK PBS:53 BEGIN -->


<a id="source-table-53"></a>

| Foundation | Required engineering release | Acceptance focus |
| --- | --- | --- |
| vCenter/ESXi and storage | Actual supported hosts, images, eligible pools, datastore policies and maintenance constraints. | Placement and restart remain eligible; data/key access is scoped and recoverable. |
| NSX management and transport | Manager placement, administrative roles, transport-node/zone membership, TEP and uplink networks. | Management separation, transport reachability and full-size path behaviour. |
| Routing and service nodes | Domain Tier-1, isolated upstream context, Edge placement, route advertisements and gateway mode. | Actual native/distributed routes and the intended external ZIP path. |
| Policy and operations | Provider-owned groups/rule hierarchy, protected changes, logs, backup and recovery. | Mandatory policy cannot be widened by tenant labels or lower-authority rules. |

<!-- SOURCE-BLOCK PBS:53 END -->

<!-- SOURCE-BLOCK PBS:54 BEGIN -->

<!-- SOURCE-BLOCK PBS:54 END -->

<!-- SOURCE-BLOCK PBS:55 BEGIN -->

Fresh mechanism check: Broadcom KB 442835 states that Tier-0 VRF gateways are not supported on an Active-Active Stateful parent Tier-0. It identifies Active-Active Stateless and Active-Standby alternatives for the stated use cases. Reconcile this constraint with the selected release, stateful services and availability requirement. The KB also warns that changing HA mode disrupts stateful contexts and routing; this is not an instruction to change a live gateway. \[D01\]

<!-- SOURCE-BLOCK PBS:55 END -->

<!-- SOURCE-BLOCK PBS:56 BEGIN -->

Verified mechanism source: [D01 — Broadcom KB 442835: Tier-0 VRF and parent HA mode](https://knowledge.broadcom.com/external/article/442835/cannot-add-tier0-vrf-gateway-to-a-tier0.html)

<!-- SOURCE-BLOCK PBS:56 END -->

<!-- SOURCE-BLOCK PBS:57 BEGIN -->

A shared parent or Edge cluster can be a common capacity/failure dependency without being a common routing authority. Record precisely what is shared. Select the stateful inspection location before choosing the HA mode; a topology that has enough throughput but bypasses required inspection is not eligible.

<!-- SOURCE-BLOCK PBS:57 END -->

<!-- SOURCE-BLOCK PBS:58 BEGIN -->

Stop when the actual gateway mode, isolation pattern or required stateful function is unsupported. A qualified alternative or excluded service capability is preferable to a misleading “equivalent” diagram.

<!-- SOURCE-BLOCK PBS:58 END -->

<!-- SOURCE-BLOCK PBS:59 BEGIN -->

Continue with: [NBD §7](../network-boundaries/7-release-the-network-design-under-an-explicit-failure-model.md#NBD_07)  •  [PBS §5](5-vmware-nsx-bind-domain-workload-and-policy-lifecycles.md#PBS_05)

<!-- SOURCE-BLOCK PBS:59 END -->

<!-- SOURCE-BLOCK PBS:60 BEGIN -->

<!-- SOURCE-BLOCK PBS:60 END -->

[Previous chapter](3-nutanix-realize-a-tenant-and-its-workload-domains.md) · [Chapter index](README.md) · [Next chapter](5-vmware-nsx-bind-domain-workload-and-policy-lifecycles.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0025 — Use isolated NSX upstream routing rather than a common unrestricted table](../../adr/0025-use-isolated-nsx-upstream-routing-rather-than-a-common-unrestricted-table.md)

<!-- END GENERATED DECISION LINKS -->
