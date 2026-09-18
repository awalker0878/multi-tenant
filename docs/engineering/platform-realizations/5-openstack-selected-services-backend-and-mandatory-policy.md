# 5. OpenStack: selected services, backend and mandatory policy

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/03_Vendor_Stack_Realizations_v1_4.docx) · [Chapter index](README.md)

> **Source:** VND — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 73be32b98783bd7857be8a00928c6894bf16f6bc98c8eb016058d3cf75b9d86b -->
<a id="__RefHeading___Toc4816_865363315"></a>
<a id="VND_s_005"></a>

Selected base authority model: provider-owned identities mutate the mandatory network baseline, security groups used for that baseline, port-security settings, permitted address pairs and external attachments. Ordinary tenant direct mutation of those controls is not enabled by the base service. Existing approved request tooling may coordinate changes. Bounded direct delegation is an extension requiring effective-policy and alternate-path qualification; additive allow groups are not a mandatory deny hierarchy.

Parent architecture: [RA §18](../../architecture/reference/18-openstack-hosting-stack-reference-realization.md#RA_s_018)  •  [RA §22](../../architecture/reference/22-vendor-platform-and-shared-service-commissioning.md#RA_s_022)  •  [RA §24](../../architecture/reference/24-terraform-across-the-vendor-stacks.md#RA_s_024)

![OpenStack reference realization inherited from the parent architecture Protected Keystone, Nova, Placement and Neutron control services manage eligible KVM/OVN pools; independent routing handoffs connect through the provider ZIP; Glance, Cinder and other data services have separate authority.](../../assets/diagrams/aee0a3b446528b1d1513.png)

<a id="fig_openstack"></a>

Figure 3. OpenStack reference realization inherited from the parent architecture

The reference selects a distribution with Keystone, Nova/Placement, Neutron, Glance and Cinder and illustrates ML2/OVN as its networking backend. These are an architectural candidate, not a claim that all distributions install the same service set. The official OVN reference separates control, compute and gateway roles and distinguishes distributed routing from external gateway traffic. The site must identify the actual release/backend/extensions and their failure dependencies. \[[B2](08-references-parent-basis-and-external-context.md#VND_src_B2) §18; [S35](08-references-parent-basis-and-external-context.md#VND_src_S35)\]


<a id="source-table-75"></a>

| Architectural element | Candidate native realization | Qualification focus |
| --- | --- | --- |
| Administrative scope | Keystone projects, scoped roles and controlled API policy. | A tenant cannot administer provider networks or another project. |
| Eligible compute | Nova/Placement and configured host/aggregate scheduling constraints. | Aggregate names alone do not enforce tenant/zone placement; verify configured filters/constraints. |
| Domain network and route | Separate Neutron networks/subnets/ports and routing contexts, realized by the chosen backend. | OZ and RZ must not be joined by an unrestricted native router. |
| External handoff | Controlled provider/external attachment and selected OVN gateway placement. | No floating-address, direct provider-network or shared connected bypass. |
| Mandatory endpoint policy | Qualified provider-controlled baseline plus entitled tenant policy. | Security-group changes must not override mandatory isolation. |
| Storage and images | Glance, Cinder and selected storage/key/protection backends. | Ownership, allowed attachment/copy, consistency and recovery are independent of network reachability. |

Neutron security-group policy is allow-based and groups are additive; ordinary defaults can permit egress. The reviewed official networking documentation supports treating these defaults as something to normalize, not as proof of the parent’s mandatory deny baseline. The implementation must identify a durable provider-owned enforcement or authority mechanism and test that tenant changes cannot expand the protected baseline. Direct competing edits to Neutron-owned backend objects are not an acceptable substitute. \[[S36](08-references-parent-basis-and-external-context.md#VND_src_S36)\]

For the common fixture, each domain has its own authorized routing context and isolated external handoff. Enumerate native logical routes, distributed paths and gateway/external paths. Sending some traffic through a gateway chassis does not prove that traffic between two subnets on a native logical router traverses that chassis or the ZIP. Include metadata, DHCP/DNS and narrow image/identity initialization requirements without creating general provider-network access.


<a id="source-table-79"></a>

| Lifecycle stage | Supported execution owner | Required result |
| --- | --- | --- |
| Control-plane installation and upgrade | Selected distribution installer/lifecycle tooling. | Accepted databases, messaging, control/network/storage services and protected management. |
| Tenant/project foundations | Scoped service APIs/providers under assigned authority. | Correct roles, quotas and eligible compute/storage/network service classes. |
| Network and boundary allocation | Neutron owner coordinated with separate security-edge owner. | Denied initial ports/networks, isolated routes/attachments and provider baseline. |
| Instance/volume creation | Nova/Cinder and image/protection integrations. | Correct owner, placement, image, volume and service attachments. |
| Observe/update/delete/recover | Authoritative service owner, not competing raw backend automation. | Asynchronous ports/routers/volumes reconcile; no stale routes or orphan grants. |

The open implementation decisions are the exact distribution and service versions, configured scheduling isolation, Neutron backend/extension support, mandatory-policy protection, address-family support, external gateway topology, Cinder/key/backup integration and provider operation coverage. Qualification must also include control database/messaging/OVN and storage quorum dependencies; a healthy API endpoint alone does not establish a resilient hosting service.

Related engineering: [Native operation coverage](../../implementation/provisioning-strategy/3-terraform-native-tools-and-operation-level-support.md#PROV_s_003)  •  [Address-family acceptance](../fabric/4-address-naming-and-protocol-family-decisions.md#NET_s_004)  •  [Platform-aware backup and restore](../../architecture/shared-services/5-backup-capture-independent-protection-and-isolated-restore.md#SVC_s_005)

[Previous chapter](4-vmware-nsx-isolated-upstream-routing-and-enforcement.md) · [Chapter index](README.md) · [Next chapter](6-portable-composite-and-migrated-service-choices.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0026 — Choose and own the actual OpenStack backend and domain boundaries](../../adr/0026-choose-and-own-the-actual-openstack-backend-and-domain-boundaries.md)

<!-- END GENERATED DECISION LINKS -->
