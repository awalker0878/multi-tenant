# 3. Nutanix: component, path and lifecycle realization

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/03_Vendor_Stack_Realizations_v1_4.docx) · [Chapter index](README.md)

> **Source:** VND — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 73be32b98783bd7857be8a00928c6894bf16f6bc98c8eb016058d3cf75b9d86b -->
<!-- SOURCE-BLOCK VND:43 BEGIN -->

<a id="__RefHeading___Toc4812_865363315"></a>
<a id="VND_s_003"></a>

<!-- SOURCE-BLOCK VND:43 END -->

<!-- SOURCE-BLOCK VND:44 BEGIN -->

Parent architecture: [RA §16](../../architecture/reference/16-nutanix-hosting-stack-reference-realization.md#RA_s_016)  •  [RA §22](../../architecture/reference/22-vendor-platform-and-shared-service-commissioning.md#RA_s_022)  •  [RA §24](../../architecture/reference/24-terraform-across-the-vendor-stacks.md#RA_s_024)

<!-- SOURCE-BLOCK VND:44 END -->

<!-- SOURCE-BLOCK VND:45 BEGIN -->

![Nutanix reference realization inherited from the parent architecture Protected Prism and Flow administration controls eligible AHV pools; separate OZ and RZ VPC handoffs connect through the provider ZIP; AOS storage dependencies are separate from guest traffic.](../../assets/diagrams/b2134c7c52bf8e5beca5.png)

<!-- SOURCE-BLOCK VND:45 END -->

<!-- SOURCE-BLOCK VND:46 BEGIN -->

<a id="fig_nutanix"></a>

Figure 1. Nutanix reference realization inherited from the parent architecture

<!-- SOURCE-BLOCK VND:46 END -->

<!-- SOURCE-BLOCK VND:47 BEGIN -->

The proposed Nutanix realization uses AHV compute, AOS storage and Prism-based administration with selected Flow networking/security functions. Tenant administrative scope, provider-owned security categories, VPC routing and workload policy are distinct responsibilities. A VPC per independent domain instance supplies a candidate routing separation mechanism; it does not prove shared-attachment or host/storage isolation on its own. \[[B2](08-references-parent-basis-and-external-context.md#VND_src_B2) §16\]

<!-- SOURCE-BLOCK VND:47 END -->

<!-- SOURCE-BLOCK VND:48 BEGIN -->


<a id="source-table-48"></a>

| Architectural element | Candidate native realization | Commissioned versus allocated |
| --- | --- | --- |
| Management and eligible capacity | Prism, required Flow control and AHV/AOS cluster resources with accepted placement policy. | Commissioned by supported platform tooling; tenant workflow consumes eligible capacity. |
| D01O/D01R/D02O/D02R | Four independently controlled VPC/routing contexts with appropriate overlay subnets. | Allocated within the accepted networking service; exact object scope is release-specific. |
| A01O…A02R | Isolated external handoffs toward the security service. | Underlying attachment capacity commissioned; slots assigned and owned per domain. |
| Z01/Z02 | Provider ZIP associations, routes and permitted service flows. | Edge service commissioned independently; domain relationships applied under edge authority. |
| Endpoint identity and policy | Protected categories/selectors and qualified Flow policy. | Provider baseline precedes endpoint attachment; tenant labels cannot override it. |
| Owned data and protection | VM disk/data objects, storage policy and supported protection integration. | Storage/protection classes commissioned; allocations and recoverable copies owned per WSD. |

<!-- SOURCE-BLOCK VND:48 END -->

<!-- SOURCE-BLOCK VND:49 BEGIN -->

<!-- SOURCE-BLOCK VND:49 END -->

<!-- SOURCE-BLOCK VND:50 BEGIN -->

For PATH-01, traffic leaves the source overlay through its native VPC gateway and isolated handoff, crosses Z01, and returns through the destination’s isolated handoff and gateway. Review return routes and any translation. The parent prefers a supported no-NAT internal handoff for unique addresses; NAT is an explicitly chosen alternative. The historic vendor NAT/no-NAT article explains the concept but is not a current compatibility matrix or source of current scale limits. \[[B2](08-references-parent-basis-and-external-context.md#VND_src_B2) §16; [S31](08-references-parent-basis-and-external-context.md#VND_src_S31)\]

<!-- SOURCE-BLOCK VND:50 END -->

<!-- SOURCE-BLOCK VND:51 BEGIN -->

AOS virtual-disk access is mediated by the virtualization/storage stack, not assumed to traverse the guest’s inter-zone IP firewall. The design must therefore verify the actual disk attachment, controller/storage access and copy permissions. Guest file/object access, where offered, uses the normal IP service path plus tenant data authorization. Include controller, management and replication co-residency in the adopted sharing decision.

<!-- SOURCE-BLOCK VND:51 END -->

<!-- SOURCE-BLOCK VND:52 BEGIN -->


<a id="source-table-52"></a>

| Build/change stage | Required result | Evidence or unresolved qualification |
| --- | --- | --- |
| Platform commissioning | Supported cluster/control/Flow enablement; eligible pools and storage/protection service. | Actual hardware, AOS/Prism/Flow/API/provider tuple and licences remain site inputs. |
| Domain allocation | Identity scope, address and attachment reservation; VPC/subnets and policy under deny. | Readiness and connected/native paths inspected before use. |
| Boundary/endpoint activation | Matching edge policy/routes, owned VM/data attachments and necessary services. | Positive/negative paths, correct source identity and service-side entitlement. |
| Change/recovery/retirement | Observe asynchronous task outcome; preserve placement, copies and shared resources. | Import/update/delete/restore support and failure reconciliation tested per operation. |

<!-- SOURCE-BLOCK VND:52 END -->

<!-- SOURCE-BLOCK VND:53 BEGIN -->

<!-- SOURCE-BLOCK VND:53 END -->

<!-- SOURCE-BLOCK VND:54 BEGIN -->

Unresolved implementation questions include the selected release’s VPC/attachment and IPv6 coverage, effective mandatory-policy precedence, external-network isolation, API task/readiness semantics and provider operation coverage. Resolve each against current official product material and the installed environment. The source family establishes a candidate mechanism, not permission to fill unsupported gaps with unobserved scripts.

<!-- SOURCE-BLOCK VND:54 END -->

<!-- SOURCE-BLOCK VND:55 BEGIN -->

Related engineering: [Operation coverage record](../../implementation/provisioning-strategy/3-terraform-native-tools-and-operation-level-support.md#PROV_s_003)  •  [Attachment accounting](../fabric/2-isolated-attachment-units-and-bounded-capacity.md#NET_s_002)  •  [Data-path and copy controls](../../architecture/shared-services/4-storage-copies-and-retained-data-ownership.md#SVC_s_004)

<!-- SOURCE-BLOCK VND:55 END -->

[Previous chapter](2-physical-placement-and-the-sharing-decision.md) · [Chapter index](README.md) · [Next chapter](4-vmware-nsx-isolated-upstream-routing-and-enforcement.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0024 — Use independent Nutanix VPC domain realizations with qualified handoffs](../../adr/0024-use-independent-nutanix-vpc-domain-realizations-with-qualified-handoffs.md)

<!-- END GENERATED DECISION LINKS -->
