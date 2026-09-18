# 2. Isolated attachment units and bounded capacity

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/02_Fabric_Security_and_Interfaces_v1_4.docx) · [Chapter index](README.md)

> **Source:** NET — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 9c557d7d94dbdf24630994d2676aca3ddfa80e67c2910fb1a29ea4561c591dcf -->
<a id="__RefHeading___Toc5747_1525915568"></a>
<a id="NET_s_002"></a>

Parent architecture: [RA §4](../../architecture/reference/4-hosting-cells-resource-pools-and-failure-boundaries.md#RA_s_004)  •  [RA §5](../../architecture/reference/5-physical-fabric-and-platform-attachment.md#RA_s_005)  •  [RA §8](../../architecture/reference/8-zone-interfaces-routing-and-security-edge-topology.md#RA_s_008)  •  [RA §16](../../architecture/reference/16-nutanix-hosting-stack-reference-realization.md#RA_s_016)  •  [RA §17](../../architecture/reference/17-vmware-and-nsx-hosting-stack-reference-realization.md#RA_s_017)  •  [RA §18](../../architecture/reference/18-openstack-hosting-stack-reference-realization.md#RA_s_018)

An attachment unit is one allocated routing and enforcement identity connecting a domain instance to its approved boundary service. It includes the domain-facing association, the security-service-facing association, address-family policy, permitted prefixes, lifecycle owner and its actual redundant transport members. An attachment unit is not inherently one VLAN, one cable, one firewall port or one vendor object. The chosen realization may require several of those resources.

Use a separately isolated attachment as the baseline until sharing is proven. Sharing physical links is different from sharing a connected IP subnet. Where a shared segment exists, show how neighbour discovery, connected routes, gateway forwarding, NAT hairpin and source spoofing are constrained before a packet can reach another domain. A downstream firewall cannot protect traffic that never reaches it. \[[B2](07-references-parent-basis-and-external-context.md#NET_src_B2) §§8, 16–18\]


<a id="source-table-36"></a>

| Attachment record | Reference example | Site decision still needed |
| --- | --- | --- |
| Owner and purpose | A01O connects tenant-01 OZ instance D01O to its approved security service. | Native gateway/context, actual endpoint IDs and operating owner. |
| Routing scope | Only P01O and approved return/service prefixes; separate from D02O. | Allocated prefixes, route installation method and maximum-prefix value. |
| Boundary association | Relation Z01 joins D01O and D01R under joint approval. | Firewall/edge contexts and policy management model. |
| Transport and HA | At least the redundancy required by the selected service; no new uninspected route on failure. | Actual member links, nodes, HA mode and convergence/session objective. |
| Security identity | Tenant/domain/WSD attribution preserved across translation if present. | Native anti-spoofing, tags, interfaces and log correlation. |
| Lifecycle | Reserved → configured under deny → verified → allocated → drained → quarantined/reusable. | Reservation timeout, reuse condition and authoritative inventory. |

For the common fixture, four independent domain instances require four logical domain attachments: A01O, A01R, A02O and A02R. This is not a count of physical links or device instances. Two tenant OZ↔RZ relations are required. Shared services may require additional boundary associations; these are counted from their actual placement and cannot be hidden inside the four-domain number. Redundant members and management attachments are accounted for separately.


<a id="source-table-39"></a>

| Capacity layer | Accounting rule | Exhaustion behaviour |
| --- | --- | --- |
| Logical domain contexts | Available = accepted usable contexts − allocated − reserved − unavailable/retiring. | Queue or select another qualified cell; never merge tenant contexts. |
| HA transport members | Count physical/logical members needed per attachment in the selected failure model. | Do not offer a redundant service on a single surviving unqualified path. |
| Policy/session capacity | Measure policy objects, connections and inspected traffic under failure. | A free context does not justify accepting workload load beyond surviving capacity. |
| Physical attachment inventory | Precommission only supported contexts/ports/identifiers; retain ownership of spare slots. | Expansion is a P1/P3 foundation change, not a tenant workaround. |

Allocation reserves the whole required bundle, not merely the first free VLAN. Failed provisioning leaves the reservation owned while native task outcomes are reconciled. Reuse follows withdrawal of routes, sessions, addresses and policy plus the selected quarantine checks. Spare capacity is a service-design cost and should be measured against delivery latency and failure reserve, not presented as free scalability.

Related engineering: [Provisioning handoff contents](../../implementation/provisioning-strategy/1-provisioning-scopes-ownership-and-accepted-handoffs.md#PROV_s_001)  •  [Capacity admission example](../../assurance/site-qualification/3-capacity-service-envelopes-and-growth-triggers.md#QUAL_s_003)

[Previous chapter](1-transport-routing-and-overlay-ownership.md) · [Chapter index](README.md) · [Next chapter](3-worked-inter-zone-routing-and-enforcement-schedule.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0007 — Allocate isolated domain attachments and qualify sharing](../../adr/0007-allocate-isolated-domain-attachments-and-qualify-sharing.md)

<!-- END GENERATED DECISION LINKS -->
