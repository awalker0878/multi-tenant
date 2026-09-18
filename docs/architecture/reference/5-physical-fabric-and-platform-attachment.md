# 5. Physical fabric and platform attachment

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/00_Reference_Architecture_v1_4.docx) · [Chapter index](README.md)

> **Source:** RA — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: e50894d7f7b87cef50a283399b85925c8a96c5b9cd0428ce71ca0143d9be8d19 -->
<!-- SOURCE-BLOCK RA:103 BEGIN -->

<a id="__RefHeading___Toc3648_865363315"></a>
<a id="RA_s_005"></a>

<!-- SOURCE-BLOCK RA:103 END -->

<!-- SOURCE-BLOCK RA:104 BEGIN -->

## Selected physical design

<!-- SOURCE-BLOCK RA:104 END -->

<!-- SOURCE-BLOCK RA:105 BEGIN -->

Use routed leaf/spine connectivity at a large site, with each applicable leaf connected to the spine set and with qualified multipath forwarding. Dual-attached hosts and appliances use the supported host teaming and multihoming design. The switching control plane carries only the transport and physical-service state for which it is authoritative. Platform overlay tunnel endpoints must be reachable with the required MTU; tenant routing does not need to be imported into every transport switch.

<!-- SOURCE-BLOCK RA:105 END -->

<!-- SOURCE-BLOCK RA:106 BEGIN -->

![Physical transport and attachment roles within a site Two spines connect to workload leaves and service leaves. Workload leaves attach vendor compute pools. Storage and live-mobility transports are separately profiled. Service leaves attach security-edge and shared-service capacity. Separate OOB switches connect management interfaces. Lines represent physical role connectivity, not tenant route imports.](../../assets/diagrams/0c5a498541f71de57ad0.png)

<!-- SOURCE-BLOCK RA:106 END -->

<!-- SOURCE-BLOCK RA:107 BEGIN -->

<a id="fig_fabric"></a>

Figure 2. Physical transport and attachment roles within a site

<!-- SOURCE-BLOCK RA:107 END -->

<!-- SOURCE-BLOCK RA:108 BEGIN -->

## Underlay, fabric overlay and platform overlay

<!-- SOURCE-BLOCK RA:108 END -->

<!-- SOURCE-BLOCK RA:109 BEGIN -->

The underlay is routed IP transport. Fabric EVPN/VXLAN is optional where physical attachment or a specific switching service needs it. Nutanix, NSX and Neutron overlays remain separate platform realizations; using the same encapsulation family does not create a shared control plane or authorize exchanging their VNIs and route targets. The reference cross-vendor handoff is controlled IP routing through a security boundary, not direct federation of vendor overlays. EVPN signalling and overlay transport are distinct specifications and must be qualified as an implemented combination. \[[S21](34-appendix-d-sources-and-review-status.md#RA_src_S21); [S22](34-appendix-d-sources-and-review-status.md#RA_src_S22)\]

<!-- SOURCE-BLOCK RA:109 END -->

<!-- SOURCE-BLOCK RA:110 BEGIN -->

For a routed fabric, the provider selects the underlay ASN/address allocation, BGP neighbour policy, route limits, loopback reachability, ECMP behaviour, convergence targets and maintenance procedures. Import and export policies are explicit. No consumer can supply a BGP neighbour or a route target. The selected hardware/software profile must show how authentication, control-plane policing and unauthorized advertisement handling are enforced. \[[S20](34-appendix-d-sources-and-review-status.md#RA_src_S20)\]

<!-- SOURCE-BLOCK RA:110 END -->

<!-- SOURCE-BLOCK RA:111 BEGIN -->


<a id="source-table-111"></a>

| Attachment class | Reference handling | Commissioning proof |
| --- | --- | --- |
| Platform transport | Precommissioned subnets/links for platform tunnel endpoints; no per-workload fabric routing | Cross-host reachability, MTU/PMTU, multipath and link/leaf failure |
| Security-edge attachment | Bounded isolated interfaces or contexts connecting a domain to the security service | No connected-route, ARP/ND or alternative-gateway bypass |
| Storage and live mobility | Provider-owned endpoint membership and controlled transport; routed only where justified | Supported latency/loss, bandwidth under failure, non-workload accessibility |
| Physical workload | Dedicated approved VLAN/VRF or equivalent attachment with explicit gateway owner | Required boundary path, tenant membership and cleanup on reassignment |
| OOB | Dedicated management interfaces and independent transport where available | Administration remains possible for the defined production-fabric failure |

<!-- SOURCE-BLOCK RA:111 END -->

<!-- SOURCE-BLOCK RA:112 BEGIN -->

<!-- SOURCE-BLOCK RA:112 END -->

<!-- SOURCE-BLOCK RA:113 BEGIN -->

A physical VRF is justified when the fabric must provide a separate routing authority. Calling a function backup, migration or platform is neither a sufficient reason to create a VRF nor a reason to prohibit one. A storage VLAN that is not routed does not need an invented routing domain; a physical partner handoff may require one. Record the actual isolation objective and its enforcement rather than standardizing a list of functional VRF names.

<!-- SOURCE-BLOCK RA:113 END -->

<!-- SOURCE-BLOCK RA:114 BEGIN -->

MLAG and EVPN multihoming are different designs. Use a qualified combination and test peer-link or Ethernet-segment failure, split-brain, orphan ports and maintenance. Do not form a cross-vendor MLAG pair on the assumption that the feature names match. Vendor interoperation normally occurs at an explicit L3/BGP or other documented handoff. Nested overlays require an end-to-end encapsulation budget and observed effective MTU, not a blanket jumbo-frame setting.

<!-- SOURCE-BLOCK RA:114 END -->

<!-- SOURCE-BLOCK RA:115 BEGIN -->

Treat a domain attachment as an owned bundle of routing/enforcement identity and supported transport members, not automatically one VLAN or cable. Precommissioning bounds tenant changes only within available accepted capacity. NET §2 defines reservation and reuse conditions; NET §5 supplies the layer-specific MTU and multihoming evidence method. Actual identifiers, component limits and routing policies remain site inputs.

<!-- SOURCE-BLOCK RA:115 END -->

<!-- SOURCE-BLOCK RA:116 BEGIN -->

Related engineering: [NET §1 — Transport, routing and overlay ownership](../../engineering/fabric/1-transport-routing-and-overlay-ownership.md#NET_s_001)  •  [NET §2 — Isolated attachment units and bounded capacity](../../engineering/fabric/2-isolated-attachment-units-and-bounded-capacity.md#NET_s_002)  •  [NET §5 — MTU, performance and failure engineering](../../engineering/fabric/5-mtu-performance-and-failure-engineering.md#NET_s_005)

<!-- SOURCE-BLOCK RA:116 END -->

[Previous chapter](4-hosting-cells-resource-pools-and-failure-boundaries.md) · [Chapter index](README.md) · [Next chapter](6-management-platform-control-and-out-of-band-access.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0004 — Scale through commissioned hosting cells and capacity pools](../../adr/0004-scale-through-commissioned-hosting-cells-and-capacity-pools.md)
- [ADR-0005 — Keep vendor overlays local and connect through controlled handoffs](../../adr/0005-keep-vendor-overlays-local-and-connect-through-controlled-handoffs.md)
- [ADR-0007 — Allocate isolated domain attachments and qualify sharing](../../adr/0007-allocate-isolated-domain-attachments-and-qualify-sharing.md)
- [ADR-0012 — Distinguish persistent platform transports from temporary migration access](../../adr/0012-distinguish-persistent-platform-transports-from-temporary-migration-access.md)

<!-- END GENERATED DECISION LINKS -->
