# 5. MTU, performance and failure engineering

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/02_Fabric_Security_and_Interfaces_v1_4.docx) · [Chapter index](README.md)

> **Source:** NET — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 9c557d7d94dbdf24630994d2676aca3ddfa80e67c2910fb1a29ea4561c591dcf -->
<!-- SOURCE-BLOCK NET:63 BEGIN -->

<a id="__RefHeading___Toc5753_1525915568"></a>
<a id="NET_s_005"></a>

<!-- SOURCE-BLOCK NET:63 END -->

<!-- SOURCE-BLOCK NET:64 BEGIN -->

WD §11 demonstrates layer-consistent MTU arithmetic. A 1450-byte guest IP packet plus the stated basic IPv4 VXLAN fields yields a 1500-byte outer IP packet; the IPv6 outer example yields 1520 bytes. These are declared packet-format assumptions, not a vendor configuration recommendation or a universal Geneve overhead.

<!-- SOURCE-BLOCK NET:64 END -->

<!-- SOURCE-BLOCK NET:65 BEGIN -->

Parent architecture: [RA §5](../../architecture/reference/5-physical-fabric-and-platform-attachment.md#RA_s_005)  •  [RA §10](../../architecture/reference/10-addressing-name-services-and-end-to-end-traffic.md#RA_s_010)  •  [RA §14](../../architecture/reference/14-availability-multi-site-operation-and-recovery-topology.md#RA_s_014)

<!-- SOURCE-BLOCK NET:65 END -->

<!-- SOURCE-BLOCK NET:66 BEGIN -->

Build the MTU budget from the actual path rather than selecting one jumbo-frame number. State whether each limit refers to an IP packet, Ethernet payload or complete frame. For every link, identify all encapsulation layers present on that link, optional fields and implementation headroom. A tunnel packet that is decapsulated before the next hop does not carry that overhead on the entire end-to-end path.

<!-- SOURCE-BLOCK NET:66 END -->

<!-- SOURCE-BLOCK NET:67 BEGIN -->

For a declared workload IP MTU M, each segment carrying the encapsulated packet must support M plus the applicable overhead measured using the same layer convention. The accepted M is bounded by the smallest effective segment limit after those overheads. A second overlay, security tunnel or service insertion may add different overhead on only part of the path. Do not assume a universal VXLAN or Geneve overhead covers every implementation. \[[B2](07-references-parent-basis-and-external-context.md#NET_src_B2) §§5, 10\]

<!-- SOURCE-BLOCK NET:67 END -->

<!-- SOURCE-BLOCK NET:68 BEGIN -->


<a id="source-table-68"></a>

| Budget row | Record | Acceptance |
| --- | --- | --- |
| Guest to native switch | Configured guest MTU, virtual NIC and segment limit. | Guest can send the advertised packet size. |
| Native tunnel across fabric | Outer addressing and encapsulations; NIC offload and transport limits. | All ECMP paths and redundant members support the chosen size. |
| Gateway to ZIP | Decapsulation/re-encapsulation point and security appliance interface limit. | No hidden lower-MTU handoff or inspection black hole. |
| Inter-site path | Carrier/service MTU, additional encryption and actual route. | Recovery/replication path supports the agreed packet profile. |
| Control feedback | Permitted path-MTU signalling or documented supported alternative. | Required operation works without blanket control-message denial. |

<!-- SOURCE-BLOCK NET:68 END -->

<!-- SOURCE-BLOCK NET:69 BEGIN -->

<!-- SOURCE-BLOCK NET:69 END -->

<!-- SOURCE-BLOCK NET:70 BEGIN -->

Capacity qualification includes latency, sustained throughput, packets per second, session establishment, inspection, log export and convergence. Test at the same time as the accepted failure condition where that is part of the service promise. Separate established-session survival from new-session success and from the eventual recovery interval. Report the workload mix and packet sizes so results can be interpreted.

<!-- SOURCE-BLOCK NET:70 END -->

<!-- SOURCE-BLOCK NET:71 BEGIN -->


<a id="source-table-71"></a>

| Fault case | Infrastructure concern | Safe result |
| --- | --- | --- |
| Single uplink or leaf | Redundant attachment and ECMP convergence. | No loop or uninspected path; measured interruption meets the selected objective. |
| MLAG peer/keepalive or EVPN member | Split-brain, orphan ports, duplicate forwarding and native fail actions. | Only the qualified forwarding ownership survives. |
| Gateway or security member | State, routes, next-hop health and return ownership. | No permissive fallback; capacity remains within measured survivor envelope. |
| Storage/rebuild contention | Shared network and storage reserve under recovery load. | Advertised service remains feasible or explicitly degrades; no unauthorized placement. |

<!-- SOURCE-BLOCK NET:71 END -->

<!-- SOURCE-BLOCK NET:72 BEGIN -->

<!-- SOURCE-BLOCK NET:72 END -->

<!-- SOURCE-BLOCK NET:73 BEGIN -->

Related engineering: [Unit-aware capacity model](../../assurance/site-qualification/3-capacity-service-envelopes-and-growth-triggers.md#QUAL_s_003)  •  [Qualification applicability](../../assurance/site-qualification/5-qualification-stages-applicability-and-evidence.md#QUAL_s_005)

<!-- SOURCE-BLOCK NET:73 END -->

[Previous chapter](4-address-naming-and-protocol-family-decisions.md) · [Chapter index](README.md) · [Next chapter](6-management-paths-and-interface-handover.md)
