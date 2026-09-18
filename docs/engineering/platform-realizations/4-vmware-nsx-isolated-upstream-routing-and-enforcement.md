# 4. VMware/NSX: isolated upstream routing and enforcement

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/03_Vendor_Stack_Realizations_v1_4.docx) · [Chapter index](README.md)

> **Source:** VND — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 73be32b98783bd7857be8a00928c6894bf16f6bc98c8eb016058d3cf75b9d86b -->
<!-- SOURCE-BLOCK VND:56 BEGIN -->

<a id="__RefHeading___Toc4814_865363315"></a>
<a id="VND_s_004"></a>

<!-- SOURCE-BLOCK VND:56 END -->

<!-- SOURCE-BLOCK VND:57 BEGIN -->

Parent architecture: [RA §17](../../architecture/reference/17-vmware-and-nsx-hosting-stack-reference-realization.md#RA_s_017)  •  [RA §22](../../architecture/reference/22-vendor-platform-and-shared-service-commissioning.md#RA_s_022)  •  [RA §24](../../architecture/reference/24-terraform-across-the-vendor-stacks.md#RA_s_024)

<!-- SOURCE-BLOCK VND:57 END -->

<!-- SOURCE-BLOCK VND:58 BEGIN -->

![VMware/NSX reference realization inherited from the parent architecture Protected vCenter and NSX administration controls eligible ESXi pools; independent Tier-1 and isolated upstream contexts connect OZ and RZ through a provider ZIP; datastores and protection are separately governed.](../../assets/diagrams/c40f78550c8e0f59dbbc.png)

<!-- SOURCE-BLOCK VND:58 END -->

<!-- SOURCE-BLOCK VND:59 BEGIN -->

<a id="fig_nsx"></a>

Figure 2. VMware/NSX reference realization inherited from the parent architecture

<!-- SOURCE-BLOCK VND:59 END -->

<!-- SOURCE-BLOCK VND:60 BEGIN -->

The proposed realization separates vCenter/ESXi compute and storage management from NSX networking/security and the provider security-edge service. A tenant domain uses a qualified routing context, such as a Tier-1, and an independently isolated upstream handoff, such as an available Tier-0 VRF design. A shared parent gateway or Edge cluster remains a shared failure/control dependency rather than permission to route between all domains. \[[B2](08-references-parent-basis-and-external-context.md#VND_src_B2) §17\]

<!-- SOURCE-BLOCK VND:60 END -->

<!-- SOURCE-BLOCK VND:61 BEGIN -->


<a id="source-table-61"></a>

| Architectural element | Candidate native realization | Required restriction |
| --- | --- | --- |
| Tenant administration | Entitled inventory/roles and NSX project scope where used. | Project or inventory visibility does not grant global routing or provider policy control. |
| Domain network | Segments and Tier-1/routing context for each independent instance. | No unrestricted native joining of OZ/RZ networks. |
| Upstream isolation | Supported Tier-0 VRF or another qualified isolated routing handoff. | No unapproved inter-VRF route leaking or shared connected bypass. |
| Workload policy | Provider-owned groups/tags and distributed policy hierarchy. | Same-host enforcement and resistance to lower-priority tenant overrides. |
| Boundary service | Actual Edge/service-router and external security-edge functions identified. | A conceptual Tier-1/Edge symbol does not prove stateful inspection. |
| Compute/data | Eligible ESXi pools, placement rules and qualified datastore/protection services. | Host restart, migration and copy operations preserve the accepted sharing and key scope. |

<!-- SOURCE-BLOCK VND:61 END -->

<!-- SOURCE-BLOCK VND:62 BEGIN -->

<!-- SOURCE-BLOCK VND:62 END -->

<!-- SOURCE-BLOCK VND:63 BEGIN -->

The site routing schedule identifies the actual distributed routing functions, service-router placement, route advertisements, upstream interfaces, prefix ownership and return paths. Traffic must not be able to use a common upstream table to reach another domain before the intended firewall. Native gateway or distributed enforcement may implement an alternative ZIP only when the complete required function, authority and failure analysis is accepted. \[[B2](08-references-parent-basis-and-external-context.md#VND_src_B2) §17\]

<!-- SOURCE-BLOCK VND:63 END -->

<!-- SOURCE-BLOCK VND:64 BEGIN -->

The official Tier-0 VRF documentation was available through an indexed excerpt, while full-page retrieval remained restricted in the review available for this release. The candidate isolation concept is retained, but release-specific feature combinations, limits, licensing and supported provider resources are not asserted as verified. Current vendor-backed design confirmation is an open G13/G32 item, not a documentation gap closed by redrawing the diagram. \[[S33](08-references-parent-basis-and-external-context.md#VND_src_S33)\]

<!-- SOURCE-BLOCK VND:64 END -->

<!-- SOURCE-BLOCK VND:65 BEGIN -->


<a id="source-table-65"></a>

| Sequence | Owned work | Completion signal |
| --- | --- | --- |
| Commission compute/storage | vCenter/ESXi, eligible host groups/clusters, datastore policy and images. | Accepted control, placement, storage/key and recovery dependencies. |
| Commission NSX and edge | Transport nodes/zones, Edge/uplink capacity and supported isolated upstream pattern. | Actual path and gateway limits tested; baseline policy owner assigned. |
| Allocate domains | Tenant scope, segments/Tier-1 associations and isolated attachment capacity. | No unauthorized connected/distributed/inter-VRF path; endpoints under deny. |
| Create and activate endpoints | vSphere VM/data changes coordinated with NSX/edge/service changes. | Current endpoint policy, route, identity, backup and live-path verification. |
| Maintain/recover | vMotion/HA/restart only within eligible pools; qualified Edge failover and target restore. | Actual failure, session, placement and datastore/key results. |

<!-- SOURCE-BLOCK VND:65 END -->

<!-- SOURCE-BLOCK VND:66 BEGIN -->

<!-- SOURCE-BLOCK VND:66 END -->

<!-- SOURCE-BLOCK VND:67 BEGIN -->

Do not make Terraform state boundaries synonymous with vendor products. Separate authority/lifecycle where needed; one deployment can involve a compute resource owner, NSX network owner, shared edge owner and protection owner. Document who may observe or change each native object and the safe handoff when a shared Edge or routing context is maintained.

<!-- SOURCE-BLOCK VND:67 END -->

<!-- SOURCE-BLOCK VND:68 BEGIN -->

Related engineering: [Stateful boundary schedule](../fabric/3-worked-inter-zone-routing-and-enforcement-schedule.md#NET_s_003)  •  [Authority-specific work packages](../../implementation/provisioning-strategy/1-provisioning-scopes-ownership-and-accepted-handoffs.md#PROV_s_001)  •  [Qualification evidence](../../assurance/site-qualification/5-qualification-stages-applicability-and-evidence.md#QUAL_s_005)

<!-- SOURCE-BLOCK VND:68 END -->

[Previous chapter](3-nutanix-component-path-and-lifecycle-realization.md) · [Chapter index](README.md) · [Next chapter](5-openstack-selected-services-backend-and-mandatory-policy.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0025 — Use isolated NSX upstream routing rather than a common unrestricted table](../../adr/0025-use-isolated-nsx-upstream-routing-rather-than-a-common-unrestricted-table.md)

<!-- END GENERATED DECISION LINKS -->
