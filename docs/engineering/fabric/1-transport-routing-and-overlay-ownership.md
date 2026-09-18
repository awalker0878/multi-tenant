# 1. Transport, routing and overlay ownership

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/02_Fabric_Security_and_Interfaces_v1_4.docx) · [Chapter index](README.md)

> **Source:** NET — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 9c557d7d94dbdf24630994d2676aca3ddfa80e67c2910fb1a29ea4561c591dcf -->
<!-- SOURCE-BLOCK NET:23 BEGIN -->

<a id="__RefHeading___Toc5745_1525915568"></a>
<a id="NET_s_001"></a>

<!-- SOURCE-BLOCK NET:23 END -->

<!-- SOURCE-BLOCK NET:24 BEGIN -->

Parent architecture: [RA §3](../../architecture/reference/3-system-context-and-physical-hosting-topology.md#RA_s_003)  •  [RA §5](../../architecture/reference/5-physical-fabric-and-platform-attachment.md#RA_s_005)  •  [RA §8](../../architecture/reference/8-zone-interfaces-routing-and-security-edge-topology.md#RA_s_008)  •  [RA §15](../../architecture/reference/15-cross-vendor-realization-model.md#RA_s_015)

<!-- SOURCE-BLOCK NET:24 END -->

<!-- SOURCE-BLOCK NET:25 BEGIN -->

The physical fabric connects platform transport endpoints and controlled service attachments. It does not become the default router between every tenant network. A platform overlay carries workload traffic inside its own realization; the security-edge service controls transitions between independently administered domains. These three responsibilities remain separate even where the same switches carry their packets. This supplement elaborates the selected parent design rather than selecting a switch manufacturer. \[[B2](07-references-parent-basis-and-external-context.md#NET_src_B2) §§3, 5, 8, 15\]

<!-- SOURCE-BLOCK NET:25 END -->

<!-- SOURCE-BLOCK NET:26 BEGIN -->

Maintain three route schedules: transport reachability, domain reachability, and approved service/external reachability. The fabric owner controls the first. The domain and security-edge owners coordinate the second and third through isolated handoffs. A service prefix may be routable without every host behind that prefix being authorized; the effective access policy remains independently constrained. Conversely, an allow rule is unusable without an appropriate forward and return route.

<!-- SOURCE-BLOCK NET:26 END -->

<!-- SOURCE-BLOCK NET:27 BEGIN -->


<a id="source-table-27"></a>

| Routing scope | Permitted content and owner | Excluded shortcut |
| --- | --- | --- |
| Transport | Provider loopbacks, tunnel-endpoint and approved attachment transport; network owner. | Importing all tenant prefixes solely to make troubleshooting convenient. |
| Domain-local | Networks belonging to one approved Security Domain Instance; platform owner. | Attaching OZ and RZ networks to one unrestricted native router. |
| Boundary | Explicit adjacent-domain prefixes and approved service/external routes; edge owner. | One common connected segment or default route that bypasses the ZIP. |
| Management | Named administrative targets and authorized executors; management owner. | Workload access to management addresses or unrestricted MZ-to-MZ transit. |
| Storage/mobility | Provider endpoint membership and permitted infrastructure paths; platform/storage owners. | A guest bridging onto storage replication or live-mobility transport. |

<!-- SOURCE-BLOCK NET:27 END -->

<!-- SOURCE-BLOCK NET:28 BEGIN -->

<!-- SOURCE-BLOCK NET:28 END -->

<!-- SOURCE-BLOCK NET:29 BEGIN -->

A default route may be part of a qualified native attachment, but its only next hop must lead to the authorized security treatment. The architecture does not assume that absence of a default route is the only safe design. Review more-specific connected, static, learned and policy-routed paths because they can defeat an apparently correct default. On inter-vendor handoffs, document the actual routing protocol, neighbour, accepted/advertised prefixes and next-hop resolution; native overlay identifiers are not a cross-platform contract.

<!-- SOURCE-BLOCK NET:29 END -->

<!-- SOURCE-BLOCK NET:30 BEGIN -->

The site engineer selects an underlay and multihoming design supported by the complete hardware/software combination. Record the routing process, ASN allocation, permitted peers, import/export policy, route scale, administrative protection and maintenance withdrawal. Do not assume a cross-vendor MLAG pair, universal EVPN feature parity or that a transport-only VLAN is itself a security zone.

<!-- SOURCE-BLOCK NET:30 END -->

<!-- SOURCE-BLOCK NET:31 BEGIN -->

Related engineering: [Common two-tenant reference environment](../platform-realizations/1-one-reference-environment-three-native-realizations.md#VND_s_001)  •  [Site and failure-domain schedule](../../assurance/site-qualification/2-site-low-level-design-and-dependency-schedule.md#QUAL_s_002)

<!-- SOURCE-BLOCK NET:31 END -->

[Chapter index](README.md) · [Next chapter](2-isolated-attachment-units-and-bounded-capacity.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0005 — Keep vendor overlays local and connect through controlled handoffs](../../adr/0005-keep-vendor-overlays-local-and-connect-through-controlled-handoffs.md)

<!-- END GENERATED DECISION LINKS -->
