# 2. Site low-level design and dependency schedule

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/06_Site_Design_Qualification_and_Operations_v1_4.docx) · [Chapter index](README.md)

> **Source:** QUAL — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 783edbba45483d0d3c3b966765589762698836320237906a0f9a60080574af37 -->
<a id="__RefHeading___Toc10035_1525915568"></a>
<a id="QUAL_s_002"></a>

Parent architecture: [RA §3](../../architecture/reference/3-system-context-and-physical-hosting-topology.md#RA_s_003)  •  [RA §4](../../architecture/reference/4-hosting-cells-resource-pools-and-failure-boundaries.md#RA_s_004)  •  [RA §5](../../architecture/reference/5-physical-fabric-and-platform-attachment.md#RA_s_005)  •  [RA §6](../../architecture/reference/6-management-platform-control-and-out-of-band-access.md#RA_s_006)  •  [RA §14](../../architecture/reference/14-availability-multi-site-operation-and-recovery-topology.md#RA_s_014)  •  [RA §30](../../architecture/reference/30-implementation-handoff-and-delivery-sequence.md#RA_s_030)

A buildable site design resolves actual components and relationships rather than filling example IP addresses into a diagram. Record hardware and software inventories, component roles, physical fault groups, logical authorities, interface IDs, capacity, management ownership and recovery dependency. The parent topology symbols are functional roles, not assumed counts or independent failure domains. \[[B2](09-references-parent-basis-and-external-context.md#QUAL_src_B2) §§3–6, 14, 30\]


<a id="source-table-36"></a>

| Site design record | Minimum populated fields | Acceptance owner |
| --- | --- | --- |
| Site/cell inventory | Site and cell IDs; actual devices/hosts; supported versions; rack, power and uplink fault groups. | Site/platform architect. |
| Physical/network design | Port roles, peer/member links, ASN/prefix policy, VLAN/VNI/RT allocations where used, MTU and native gateway ownership. | Network engineering. |
| Security and management topology | Domain authorities, ZIP contexts, administrative source/target paths, OOB dependency and accepted sharing. | Security/management owners. |
| Vendor realization | Exact native domain/endpoint/storage resources; management/control placement; supported API/provider/installer operations. | Selected platform owner. |
| Service dependency map | DNS/time/identity/key/log/protection endpoints and their management/backends; common fault and privilege dependencies. | Shared-service owners. |
| Data and recovery schedule | Owned data/copies, keys, consistency, retention, fencing, target eligibility and restoring order. | Data/protection/continuity owners. |
| As-built and evidence references | Actual configuration and resource identities, approved changes, tests, variations and operating restrictions. | Operations and assurance owners. |

For every claim of redundancy, enumerate the common components that can defeat it. Two VMs can share a host; two hosts can share power or a storage controller; two sites can share the sole identity/KMS or security management dependency. Conversely, a shared fabric can be acceptable when the service’s stated failure scope and isolation controls account for it. The design must disclose the dependency rather than mandate physical duplication of every component.


<a id="source-table-39"></a>

| Claim to evaluate | Evidence needed | Consequence if unresolved |
| --- | --- | --- |
| Host-failure tolerance | Eligible survivor inventory, reservations and observed restart/evacuation with placement controls. | Do not advertise the host-failure service objective. |
| Rack/link independence | Actual power/uplink mapping and selected multihoming failure results. | Treat the common rack/uplink as one failure domain. |
| Storage independence | Backend/controller/media and copy placement, quorum and recovery path. | Separate datastores or names alone do not establish independence. |
| Management recovery | Surviving OOB/privileged access, protected configuration and trust material. | Control recovery remains blocked even if workload disks survive. |
| Site recovery | Independent usable target, trust/key/catalogue access, routed connectivity and writer exclusion. | A replication job alone is not a complete recovery service. |

A site-specific design record remains open until values are supplied and the appropriate owner accepts them. The supplied decision CSV gives the question, required evidence and gate, rather than presenting fabricated environment values as approved. Additional rows are added for genuine local requirements; they do not silently amend the parent’s security semantics.

Related engineering: [Interface ownership](../../engineering/fabric/6-management-paths-and-interface-handover.md#NET_s_006)  •  [Sharing decisions](../../engineering/platform-realizations/2-physical-placement-and-the-sharing-decision.md#VND_s_002)  •  [Recovery dependencies](../../architecture/shared-services/6-failure-recovery-migration-and-failback-topology.md#SVC_s_006)

[Previous chapter](1-from-proposed-architecture-to-accepted-service.md) · [Chapter index](README.md) · [Next chapter](3-capacity-service-envelopes-and-growth-triggers.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0011 — Default to site-local domains and routed recovery](../../adr/0011-default-to-site-local-domains-and-routed-recovery.md)

<!-- END GENERATED DECISION LINKS -->
