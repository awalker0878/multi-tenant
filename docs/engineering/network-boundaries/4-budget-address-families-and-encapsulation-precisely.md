# 4. Budget address families and encapsulation precisely

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/02_Engineering/Network_and_Boundary_Detailed_Engineering.docx) · [Chapter index](README.md)

> **Source:** NBD — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 7a86351d7f4be320e48d3112485bbab4b0f5b4a79cd0e420a823c793a708733a -->
<!-- SOURCE-BLOCK NBD:49 BEGIN -->

<a id="NBD_04"></a>

<!-- SOURCE-BLOCK NBD:49 END -->

<!-- SOURCE-BLOCK NBD:50 BEGIN -->

An offered family must work along the entire path, including service consumption and recovery. The MTU budget must describe which packet or frame a product limit measures.

<!-- SOURCE-BLOCK NBD:50 END -->

<!-- SOURCE-BLOCK NBD:51 BEGIN -->

Design basis and related records: [NET §5](../fabric/5-mtu-performance-and-failure-engineering.md#NET_s_005)  •  [WD §11](../../solutions/internal-protected-workload/11-test-resource-capacity-and-mtu-accounting.md#WD14_S11)  •  [EK §6](../delivery-guide/6-capacity-mtu-performance-and-failure-analysis.md#EK_06)

<!-- SOURCE-BLOCK NBD:51 END -->

<!-- SOURCE-BLOCK NBD:52 BEGIN -->

Keep IPv4-only, IPv6-only and dual-stack as distinct engineering choices. Do not assign a fictitious IPv4 prefix to an IPv6-only service or assume an IPv4-only dependency is reachable. Any family translation is a separately engineered dependency with explicit enforcement, name resolution and recovery behaviour.

<!-- SOURCE-BLOCK NBD:52 END -->

<!-- SOURCE-BLOCK NBD:53 BEGIN -->


<a id="source-table-53"></a>

| Basic VXLAN example | Bytes | Interpretation |
| --- | --- | --- |
| Workload IP packet | 1500 | Local example input, not a universal service target. |
| Inner Ethernet header + VXLAN + UDP | 14 + 8 + 8 = 30 | No inner VLAN tag, options or additional encapsulation in this example. |
| Outer IPv4 IP header | 20 | Outer IP packet: 1500 + 30 + 20 = 1550 bytes. |
| Outer IPv6 IP header | 40 | Outer IP packet: 1500 + 30 + 40 = 1570 bytes. |
| Outer link-frame overhead | Additional | Do not compare these IP totals directly with a frame limit that includes outer Ethernet, tags or FCS. |

<!-- SOURCE-BLOCK NBD:53 END -->

<!-- SOURCE-BLOCK NBD:54 BEGIN -->

<!-- SOURCE-BLOCK NBD:54 END -->

<!-- SOURCE-BLOCK NBD:55 BEGIN -->

RFC 7348 supplies the VXLAN packet-format context for this arithmetic. It does not select a vendor MTU setting or qualify the path. Geneve options, inner tags, encryption and nested encapsulation require separate budgets; use the actual configured combination rather than reusing the numbers above. \[D06\]

<!-- SOURCE-BLOCK NBD:55 END -->

<!-- SOURCE-BLOCK NBD:56 BEGIN -->

Verified mechanism source: [D06 — RFC 7348: VXLAN packet format](https://www.rfc-editor.org/info/rfc7348/)

<!-- SOURCE-BLOCK NBD:56 END -->

<!-- SOURCE-BLOCK NBD:57 BEGIN -->

For each normal and surviving path, compare the packet budget with its smallest supported limit and observe required PMTU feedback. The commissioning plan also checks permitted ICMPv6, router advertisement/neighbor controls and local-link management exclusion. A transport ping with small packets does not prove workload-sized packets survive a security edge or recovery path.

<!-- SOURCE-BLOCK NBD:57 END -->

<!-- SOURCE-BLOCK NBD:58 BEGIN -->

Continue with: [QCP §3](../../assurance/qualification-campaign/3-observe-network-paths-and-boundary-enforcement.md#QCP_03)  •  [NBD §7](7-release-the-network-design-under-an-explicit-failure-model.md#NBD_07)

<!-- SOURCE-BLOCK NBD:58 END -->

<!-- SOURCE-BLOCK NBD:59 BEGIN -->

<!-- SOURCE-BLOCK NBD:59 END -->

[Previous chapter](3-make-service-replies-choose-the-originating-context.md) · [Chapter index](README.md) · [Next chapter](5-keep-fabric-authority-separate-from-tenant-routing.md)
