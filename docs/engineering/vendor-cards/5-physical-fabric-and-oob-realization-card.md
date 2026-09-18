# 5. Physical fabric and OOB realization card

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/02_Engineering/Vendor_Realization_Cards.docx) · [Chapter index](README.md)

> **Source:** VRC — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 5e453a432a4b6c5af7d75ba266945bdb9e01118757cbeec1e15d81f92be32ab0 -->
<a id="VC_05"></a>

Reference mapping: provider-owned routed transport, qualified host/appliance attachment, optional EVPN/VXLAN where needed, and separately protected hardware recovery and management.

Baseline and related records: [RA §5](../../architecture/reference/5-physical-fabric-and-platform-attachment.md#RA_s_005)  •  [RA §6](../../architecture/reference/6-management-platform-control-and-out-of-band-access.md#RA_s_006)  •  [NET §1](../fabric/1-transport-routing-and-overlay-ownership.md#NET_s_001)  •  [NET §5](../fabric/5-mtu-performance-and-failure-engineering.md#NET_s_005)


<a id="source-table-54"></a>

| Build concern | Specific engineering decision / receipt |
| --- | --- |
| Inventory and ports | Actual switch/network OS/NIC/optic/firmware compatibility, port map, power/failure grouping and staging identity. |
| Underlay | Link/loopback allocations, permitted peers/ASNs, explicit import/export, ECMP, control-plane protection and maximum-prefix handling. |
| Optional fabric overlay | RD/RT/VNI authority, gateway location, supported route types, BUM/ARP/ND and explicit route-import restrictions. |
| Multihoming | Chosen MLAG or EVPN mechanism, peer/ES dependencies, orphan and split-brain behaviour; no assumed cross-vendor MLAG pair. |
| Platform/edge transport | Owned tunnel endpoint networks, dedicated/qualified handoffs, actual encapsulation and minimum surviving MTU. |
| Commission and recover | Supported network configuration owner, safe staged change, snapshots, constrained management, fault/recovery observations and accepted G1 receipt. |

Use a site-specific network-OS annex after hardware selection. A Dell OS10 or other switch implementation must supply its actual provider or native configuration coverage and release-specific commands. The kit does not assert an unverified universal Terraform switch provider.

Physical placement and cabling execution use approved facility/manufacturer procedures and qualified personnel. Do not infer physical independence from two logical links terminating on the same failure dependency.

[Previous chapter](4-openstack-realization-card.md) · [Chapter index](README.md) · [Next chapter](6-shared-services-and-security-edge-realization-card.md)
