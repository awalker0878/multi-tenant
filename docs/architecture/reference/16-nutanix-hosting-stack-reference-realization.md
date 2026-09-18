# 16. Nutanix hosting-stack reference realization

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/00_Reference_Architecture_v1_4.docx) · [Chapter index](README.md)

> **Source:** RA — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: e50894d7f7b87cef50a283399b85925c8a96c5b9cd0428ce71ca0143d9be8d19 -->
<a id="__RefHeading___Toc3670_865363315"></a>
<a id="RA_s_016"></a>

## Component placement

The Nutanix pattern uses AHV compute with AOS storage services and Prism-based administration. Selected Flow networking and security functions supply tenant virtual networking and workload controls. Vendor guidance distinguishes VPC external connectivity from overlay workload networks, and describes NAT and no-NAT external attachment options. Their exact limits and current implementation depend on the selected release. \[[S17](34-appendix-d-sources-and-review-status.md#RA_src_S17); [S31](34-appendix-d-sources-and-review-status.md#RA_src_S31); [S32](34-appendix-d-sources-and-review-status.md#RA_src_S32)\]

The proposed site layout places Prism and required control services in the protected management environment, with recovery placement compatible with the product. Workload AHV resources are allocated to eligible zone/co-residency pools. AOS/controller membership, management, storage transport and guest placement are assessed together. Security-edge capacity is a provider service with independent administrative authority and the required failure isolation; it is not created anew as an unmanaged guest appliance for every tenant.

![Nutanix reference: VPC domains with controlled external security handoffs Prism and Flow management control AHV pools and native network policy over management paths. An OZ VPC and an RZ VPC have separate overlay subnets and isolated external attachments. Their only approved data path passes through a provider ZIP/security-edge context. AOS/controller storage paths remain provider infrastructure rather than guest transit.](../../assets/diagrams/b2134c7c52bf8e5beca5.png)

<a id="fig_nutanix"></a>

Figure 5. Nutanix reference: VPC domains with controlled external security handoffs

## Domain and data-path realization

Use a separate VPC or equivalently qualified routing context for each independent Security Domain Instance. Do not put OZ and RZ networks in one generally routed VPC and assume a diagrammed firewall will intercept native routing. Provider-controlled categories identify tenant, WSD, domain and approved role for policy; they are distinct from project/RBAC entitlement and from a routing boundary.

Within one domain, approved traffic can use the native overlay and mandatory endpoint controls. Between domains, the path is source subnet/gateway, isolated external attachment, the declared security-edge context, destination attachment/gateway and destination subnet. The reverse path is qualified for the selected NAT, no-NAT and routing behaviour. A common connected external subnet is not accepted merely because the VPCs have different names.

The selected default for unique-address internal service is a routed no-NAT handoff where the actual stack supports it and qualification preserves source identity and isolation. NAT remains an explicit option for overlapping address transition or a specific service requirement. A dedicated attachment context is the safe baseline when isolation of a shared external network has not been demonstrated. Precommission isolated attachment slots so routine VPC allocation does not require a new physical VLAN at every request; pool exhaustion triggers a foundation expansion.


<a id="source-table-241"></a>

| Build responsibility | Commission once per approved capacity boundary | Allocate or change for the tenant/domain |
| --- | --- | --- |
| Platform | Supported cluster and management deployment; Flow enablement; host/storage/transport baseline | VMs, images/templates and resource policies within entitled pools |
| Tenancy | Provider IAM, protected categories and approved policy framework | Tenant scope, entitlements and immutable security associations |
| Networking | Platform transport and bounded isolated external-attachment capacity | VPC, overlay networks, approved gateway/route association and endpoint membership |
| Security edge | Resilient provider edge and logical-context capacity | Pairwise ZIP relationship, explicit prefixes and permitted flows |
| Data services | Storage/protection classes, keys and backup infrastructure | Owned storage, protection assignment, service bindings and recovery records |

## Provisioning order and operational limits

The platform installer or supported bootstrap process first establishes cluster and management services. Terraform starts where a supported management API and protected execution path exist. The provisioning workflow then resolves tenant identity and host eligibility, reserves addresses and attachment capacity, creates the VPC/subnets under deny, establishes the matching edge context and routes, applies required security selectors/policy, and creates compute/storage attachments. Approved service connectivity is activated only after realized-state and path checks.

Nutanix platform resources and shared firewall/IPAM/DNS/backup resources have separate owners, identities and state boundaries even when they contribute to one deployment. Provider v2/v4-backed resource coverage is reviewed against the actual AOS, Prism and Flow combination; a resource name does not prove support for an operation or release. Unsupported bootstrap, policy or protection operations remain declared integration work, not hidden shell commands labelled as complete Terraform provisioning.

Acceptance includes same-host segmentation, shared-attachment bypass, policy selector tampering, route/NAT symmetry, storage isolation, management loss, host evacuation and restore. It also verifies that supported update and delete operations remove obsolete native objects. Existing traffic during Prism or Flow management loss is measured on the selected tuple; the architecture does not promise uninterrupted operation merely because control is conceptually separate from forwarding.

Related engineering: [VND §3 — Nutanix: component, path and lifecycle realization](../../engineering/platform-realizations/3-nutanix-component-path-and-lifecycle-realization.md#VND_s_003)

[Previous chapter](15-cross-vendor-realization-model.md) · [Chapter index](README.md) · [Next chapter](17-vmware-and-nsx-hosting-stack-reference-realization.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0024 — Use independent Nutanix VPC domain realizations with qualified handoffs](../../adr/0024-use-independent-nutanix-vpc-domain-realizations-with-qualified-handoffs.md)

<!-- END GENERATED DECISION LINKS -->
