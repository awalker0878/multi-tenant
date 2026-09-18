# 3. Addressing, routing, policy and attachment schedules

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/02_Engineering/Engineering_Kit.docx) · [Chapter index](README.md)

> **Source:** EK — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 0aeb8ee0a114d3ed23e97c684cc9812a0fa6ea5252e49f0c902132bf4e053a7d -->
<!-- SOURCE-BLOCK EK:33 BEGIN -->

<a id="EK_03"></a>

<!-- SOURCE-BLOCK EK:33 END -->

<!-- SOURCE-BLOCK EK:34 BEGIN -->

Keep three records distinct: address ownership, routing reachability and permitted communication. A correct prefix allocation does not prove a correct route, and a route does not authorize a flow.

<!-- SOURCE-BLOCK EK:34 END -->

<!-- SOURCE-BLOCK EK:35 BEGIN -->

Baseline and related records: [NET §1](../fabric/1-transport-routing-and-overlay-ownership.md#NET_s_001)  •  [NET §3](../fabric/3-worked-inter-zone-routing-and-enforcement-schedule.md#NET_s_003)  •  [NET §4](../fabric/4-address-naming-and-protocol-family-decisions.md#NET_s_004)  •  [WD §6](../../solutions/internal-protected-workload/6-worked-forwarding-and-return-route-schedule.md#WD14_S06)  •  [ET §3](../../templates/lld/3-networks-addresses-and-native-gateways.md#ET_03)

<!-- SOURCE-BLOCK EK:35 END -->

<!-- SOURCE-BLOCK EK:36 BEGIN -->


<a id="source-table-36"></a>

| Record | What the implementer must receive |
| --- | --- |
| Network and domain schedule | Owner, zone/domain instance, native context, family mode, actual prefix/gateway, IPAM authority and DHCP/DNS policy. |
| Route schedule | Routing owner, family, destination, next hop and egress interface, import/export origin, related boundary, return-route owner and prohibited alternatives. |
| Flow schedule | Initiator and target identity, protocol/service operation, port/type detail as needed, authentication, encryption, stateful replies, log policy and expiry. |
| Attachment inventory | Domain-to-edge and edge-to-service units separately counted; physical members and HA overhead additional; reuse/quarantine rules. |
| Boundary design | Every required ZIP function located; policy precedence, shared connected routes, native distributed routing, NAT/PBR and fault paths analyzed. |
| Service reply design | Origin-specific return routing or a supported mediation pattern; no broad default masking asymmetric enforcement. |

<!-- SOURCE-BLOCK EK:36 END -->

<!-- SOURCE-BLOCK EK:37 BEGIN -->

<!-- SOURCE-BLOCK EK:37 END -->

<!-- SOURCE-BLOCK EK:38 BEGIN -->

Record IPv4-only, IPv6-only or dual-stack as an offered capability. Include neighbour/discovery and required ICMPv6/PMTU behaviour, source validation, DNS transport and recovery paths for every enabled family. The WD address ranges remain documentation examples only.

<!-- SOURCE-BLOCK EK:38 END -->

<!-- SOURCE-BLOCK EK:39 BEGIN -->

Review by walking an allowed request and reply, unsolicited reverse initiation, same-domain traffic and a cross-tenant denial. Inspect actual forwarding candidates; a failed ping from a dead endpoint is not proof.

<!-- SOURCE-BLOCK EK:39 END -->

<!-- SOURCE-BLOCK EK:40 BEGIN -->

<!-- SOURCE-BLOCK EK:40 END -->

[Previous chapter](2-site-equipment-and-physical-foundation.md) · [Chapter index](README.md) · [Next chapter](4-compute-storage-and-protected-data.md)
