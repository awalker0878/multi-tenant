# 18. OpenStack hosting-stack reference realization

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/00_Reference_Architecture_v1_4.docx) · [Chapter index](README.md)

> **Source:** RA — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: e50894d7f7b87cef50a283399b85925c8a96c5b9cd0428ce71ca0143d9be8d19 -->
<a id="__RefHeading___Toc3674_865363315"></a>
<a id="RA_s_018"></a>

## Selected platform pattern

The OpenStack reference selects a supported distribution with Keystone identity, Nova/Placement compute, Neutron networking and an explicitly chosen backend, Glance images and Cinder block storage. The illustrated networking backend is ML2/OVN. File, object, key, load-balancing and backup services are included only where the adopted stack supplies and qualifies them; OpenStack is not treated as a fixed identical product bundle.

OpenStack’s OVN documentation separates controller/database, compute and gateway roles and describes distributed east-west routing as distinct from external gateway traffic. This matters because sending an external path through a network node does not prove that traffic between two attached internal subnets will use that node. \[[S35](34-appendix-d-sources-and-review-status.md#RA_src_S35)\]

![OpenStack reference: project domains with explicit boundary attachments Keystone, Nova/Placement, Neutron and storage/image services form the protected control layer. Eligible KVM/OVS/OVN compute pools host tenant instances. Separate OZ and RZ logical routing contexts use isolated provider/external attachments toward a logical ZIP. Cinder and its selected backend supply authorized data resources. No assumption is made that a Neutron router itself supplies all ZIP functions.](../../assets/diagrams/aee0a3b446528b1d1513.png)

<a id="fig_openstack"></a>

Figure 7. OpenStack reference: project domains with explicit boundary attachments

## Compute, tenant and network separation

The proposed deployment separates protected service controllers and databases from tenant compute. Gateway capacity provides the approved external handoff; storage backend services have defined membership, credentials and replication paths. Host aggregates and Placement constraints implement eligible pools with the required zone/tenant restrictions. Availability zones describe offered failure/placement groupings only when backed by actual independent resources. Nova documentation requires explicit scheduler and aggregate configuration for tenant isolation; a group name alone is not an isolation control. \[[S37](34-appendix-d-sources-and-review-status.md#RA_src_S37)\]

Keystone projects provide administrative scope. Each independent Security Domain Instance receives a separate Neutron routing/network context and a controlled external attachment. The reference does not connect OZ and RZ subnets through one unrestricted Neutron router and call the result an inspected boundary. Approved inter-domain traffic leaves its isolated context, crosses the provider ZIP, and returns to the destination context. Native distributed routes and any provider-network connections are included in bypass analysis.

Security groups are port-level allow policies; the default group normally permits egress, and multiple groups are additive. Port-security and additional address-pair controls affect the anti-spoofing boundary. The reference removes unapproved default egress while preserving required bootstrap services and protects mandatory policy from tenant override. Tenant roles cannot freely disable port security, attach arbitrary provider networks or create floating-address paths outside the approved exposure service. \[[S36](34-appendix-d-sources-and-review-status.md#RA_src_S36)\]


<a id="source-table-275"></a>

| Build responsibility | Commissioned platform resources | Tenant/domain realization |
| --- | --- | --- |
| Control | Distribution, service databases/messaging, identity, image, scheduler and API policy | Project/role scope and quotas within the approved service envelope |
| Compute | Eligible hosts, enforced scheduling/aggregates, image and virtual-hardware classes | Instances/flavours, affinity and owned volume attachments |
| Networking | Chosen Neutron backend, transport, provider bridges and gateway capacity | Networks, subnets, ports, isolated routers/attachments and approved groups |
| Data | Cinder backend classes and separate file/object/protection services as offered | Owned data objects, access scope, encryption and backup association |
| Security boundary | Provider-managed ZIP capacity and restrictions on alternative paths | Explicit domain-to-domain or external service policy and routes |

## Provisioning and operating sequence

Use the selected distribution’s supported deployment and lifecycle tooling to build the control plane, compute services, networking backend and storage integration. Terraform then provisions supported service resources through qualified APIs; it is not presumed to install or upgrade the entire distribution. Project scope and quotas precede network/port and volume allocation. Baseline policy and isolated boundary attachments precede endpoint activation. Metadata, DHCP/DNS and necessary identity access are explicitly included so a deny baseline does not accidentally prevent secure initialization.

A provider-owned policy or enforcement layer is required where tenant-editable security groups cannot guarantee the mandatory baseline. Direct edits to backend OVS/OVN objects must not compete with Neutron ownership. Distributed floating-IP or direct provider-network paths are disabled for the base internal service unless specifically qualified. The chosen behaviour is recorded, not inferred from generic OpenStack documentation.

Acceptance includes project and port authority, default-group normalization, internal distributed routing, gateway/HA failure, additional NIC/address-pair behaviour, policy persistence after relocation, Cinder attachment isolation, backend/key dependencies and complete deletion. Queues, databases, OVN control and storage quorum are shared dependencies that must be represented in the failure model. Replacing the Neutron backend is an architecture-impacting change, not merely a Terraform provider update.

Related engineering: [VND §5 — OpenStack: selected services, backend and mandatory policy](../../engineering/platform-realizations/5-openstack-selected-services-backend-and-mandatory-policy.md#VND_s_005)

[Previous chapter](17-vmware-and-nsx-hosting-stack-reference-realization.md) · [Chapter index](README.md) · [Next chapter](19-physical-workloads-and-future-platform-extensions.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0023 — Protect mandatory policy and identity selectors from tenant mutation](../../adr/0023-protect-mandatory-policy-and-identity-selectors-from-tenant-mutation.md)
- [ADR-0026 — Choose and own the actual OpenStack backend and domain boundaries](../../adr/0026-choose-and-own-the-actual-openstack-backend-and-domain-boundaries.md)

<!-- END GENERATED DECISION LINKS -->
