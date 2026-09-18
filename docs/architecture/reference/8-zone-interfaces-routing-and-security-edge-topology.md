# 8. Zone interfaces, routing and security-edge topology

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/00_Reference_Architecture_v1_4.docx) · [Chapter index](README.md)

> **Source:** RA — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: e50894d7f7b87cef50a283399b85925c8a96c5b9cd0428ce71ca0143d9be8d19 -->
<!-- SOURCE-BLOCK RA:140 BEGIN -->

<a id="__RefHeading___Toc3654_865363315"></a>
<a id="RA_s_008"></a>

<!-- SOURCE-BLOCK RA:140 END -->

<!-- SOURCE-BLOCK RA:141 BEGIN -->

The reference uses PAZ, OZ, RZ and HRZ for workload-capable internal zone classes, with MZ reserved for controlled administration. Public and Restricted Extranet Zone relationships are represented as external authorities. A ZIP is a controlled interface between two zones, not another workload zone. The internal/external representation is a local modelling decision aligned with the distinct authorities in the source guidance; it does not redefine the government zone vocabulary. \[[S01](34-appendix-d-sources-and-review-status.md#RA_src_S01); [S02](34-appendix-d-sources-and-review-status.md#RA_src_S02)\]

<!-- SOURCE-BLOCK RA:141 END -->

<!-- SOURCE-BLOCK RA:142 BEGIN -->

HRZ is modelled only as an optional higher-assurance extension, not an automatically available cloud service. ITSP.80.023 specifically limits cloud HRZ suitability; neither including HRZ in a schema nor placing it on dedicated hosts establishes approval. An on-premises realization and its applicable controls must be assessed on their own basis before this extension is offered. \[[S02](34-appendix-d-sources-and-review-status.md#RA_src_S02)\]

<!-- SOURCE-BLOCK RA:142 END -->

<!-- SOURCE-BLOCK RA:143 BEGIN -->

## Selected boundary pattern

<!-- SOURCE-BLOCK RA:143 END -->

<!-- SOURCE-BLOCK RA:144 BEGIN -->

Each independent domain has a native gateway and an isolated attachment toward the security-edge service. The edge hosts a logical boundary context with explicitly identified source and destination domains, routes, stateful policy, required inspection and logging. A physical security cluster can host several logical ZIPs. It cannot collapse their routing or administrative scopes into one permissive transit context. A multi-interface appliance may implement several pairwise ZIP relationships; the architectural two-zone relationship is not a physical two-port limitation.

<!-- SOURCE-BLOCK RA:144 END -->

<!-- SOURCE-BLOCK RA:145 BEGIN -->

![Reference inter-domain data path and the separate management path Traffic flows from an OZ network through its native gateway and isolated attachment into an authorized ZIP context, then through an independent RZ attachment and gateway to an RZ network. The return path follows the same qualified enforcement arrangement. A separate management path administers the gateways and edge; it is not workload transit.](../../assets/diagrams/b4f35bdf77bcab26b814.png)

<!-- SOURCE-BLOCK RA:145 END -->

<!-- SOURCE-BLOCK RA:146 BEGIN -->

<a id="fig_zip"></a>

Figure 4. Reference inter-domain data path and the separate management path

<!-- SOURCE-BLOCK RA:146 END -->

<!-- SOURCE-BLOCK RA:147 BEGIN -->


<a id="source-table-147"></a>

| Relationship | Reference treatment |
| --- | --- |
| Public ↔ PAZ | Declared public service through an external boundary; no direct attachment to internal workloads |
| PAZ ↔ OZ; OZ ↔ RZ | Separate approved ZIP relationships; default traffic remains denied |
| RZ ↔ HRZ extension | Not a base portable cloud service; requires explicit higher-assurance applicability and implementation approval |
| Partner/REZ ↔ approved internal domain | Agreement, authenticated endpoint and explicitly approved boundary; not automatic enterprise trust |
| Different domains with the same zone class | Independent isolation still applies; use a declared boundary or service relationship |
| MZ ↔ managed interface | Management-specific access boundary and privileged identity; never a workload transit shortcut |
| Other adjacency | Not enabled by the base pattern; adopt an explicit extension with complete path and authority analysis |

<!-- SOURCE-BLOCK RA:147 END -->

<!-- SOURCE-BLOCK RA:148 BEGIN -->

<!-- SOURCE-BLOCK RA:148 END -->

<!-- SOURCE-BLOCK RA:149 BEGIN -->

Routes establish reachability; security policy authorizes use of that reachability. Both must be correct. The provider owns allowed prefix sets, next-hop choices, default routes, route import/export and edge advertisements. In this document, Route Authority means that engineering responsibility and its controlled automation, not a requirement to develop a new routing compiler application. The delivered routing table must be explainable from the approved domain and service connectivity.

<!-- SOURCE-BLOCK RA:149 END -->

<!-- SOURCE-BLOCK RA:150 BEGIN -->

There is no default unrestricted transit VRF, common Tier-0 routing table, shared Neutron external segment or VPC external subnet connecting all independent domains. A connected route can bypass a downstream firewall before its policy is ever evaluated. Shared attachment designs are allowed only after their actual connected, neighbour, gateway, NAT and return paths preserve the boundary. Otherwise allocate dedicated isolated contexts from precommissioned capacity.

<!-- SOURCE-BLOCK RA:150 END -->

<!-- SOURCE-BLOCK RA:151 BEGIN -->

The security-edge design identifies state synchronization, active/standby or supported active/active behaviour, return-path symmetry, connection revocation, scale limits and fail-secure behaviour. Routes must not switch to an uninspected backup path when the edge fails. A distributed ZIP alternative must identify where every required function occurs, including same-host paths and administration. Neither a router nor a distributed-firewall licence alone qualifies it as a ZIP.

<!-- SOURCE-BLOCK RA:151 END -->

<!-- SOURCE-BLOCK RA:152 BEGIN -->

For every accepted boundary, record an explicit forward path, reply path, initiating party, allowed service, translation and unavailable-next-hop behaviour. Review native distributed and connected routes in addition to the visible firewall rules. The common two-tenant fixture in VND §1 and path schedule in NET §3 make these outcomes comparable across the three stacks without requiring identical topology.

<!-- SOURCE-BLOCK RA:152 END -->

<!-- SOURCE-BLOCK RA:153 BEGIN -->

Related engineering: [NET §2 — Isolated attachment units and bounded capacity](../../engineering/fabric/2-isolated-attachment-units-and-bounded-capacity.md#NET_s_002)  •  [NET §3 — Worked inter-zone routing and enforcement schedule](../../engineering/fabric/3-worked-inter-zone-routing-and-enforcement-schedule.md#NET_s_003)

<!-- SOURCE-BLOCK RA:153 END -->

[Previous chapter](7-tenant-environments-and-security-domain-placement.md) · [Chapter index](README.md) · [Next chapter](9-shared-services-ingress-and-controlled-egress.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0006 — Use an explicit governed ZIP for inter-domain trust transitions](../../adr/0006-use-an-explicit-governed-zip-for-inter-domain-trust-transitions.md)
- [ADR-0007 — Allocate isolated domain attachments and qualify sharing](../../adr/0007-allocate-isolated-domain-attachments-and-qualify-sharing.md)
- [ADR-0022 — Treat public access and egress as explicit service extensions](../../adr/0022-treat-public-access-and-egress-as-explicit-service-extensions.md)

<!-- END GENERATED DECISION LINKS -->
