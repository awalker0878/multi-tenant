# 7. Tenant environments and security-domain placement

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/00_Reference_Architecture_v1_4.docx) · [Chapter index](README.md)

> **Source:** RA — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: e50894d7f7b87cef50a283399b85925c8a96c5b9cd0428ce71ca0143d9be8d19 -->
<a id="__RefHeading___Toc3652_865363315"></a>
<a id="RA_s_007"></a>

A tenant environment is an administrative allocation of hosting services. It contains one or more Workload Security Domains (WSDs), which group resources with a common service owner, lifecycle and security/recovery requirements. The WSD is a useful architectural deployment boundary; it is not an application microservice, a mandatory custom API type or necessarily one Terraform state.

A logical Security Domain establishes one zone class and security authority. A Security Domain Instance realizes that domain in a site/platform routing and enforcement context. A network belongs to one instance. A WSD can require several domains, for example an Operations Zone for an internal processing tier and a Restricted Zone for its protected data tier. A second tenant receives independent domains even when its zone labels are identical.

![Logical tenancy and zone boundaries, independent of vendor topology Tenant A and Tenant B each have separate OZ and RZ domain instances. Approved OZ to RZ connectivity passes through a separately governed ZIP for that tenant. No connection exists between tenants by default. Both tenants may use qualified provider services through individual bindings without sharing routing authority.](../../assets/diagrams/14b1c598defd5f5fda87.png)

<a id="fig_tenancy"></a>

Figure 3. Logical tenancy and zone boundaries, independent of vendor topology


<a id="source-table-133"></a>

| Architectural allocation | Scope | Lifecycle relationship |
| --- | --- | --- |
| Tenant | Administrative ownership, roles, entitlements and quotas | Longer-lived than an individual workload; does not own provider foundations |
| WSD | Compute/storage/network requirements and operational acceptance | Created, changed, recovered and retired as a bounded service environment |
| Logical Security Domain | Zone class, authority, allowed sharing and routing policy | May outlive a WSD when explicitly shared |
| Domain Instance | Site/platform realization of the domain | Recreated at another site or stack without redefining its security purpose |
| Network and resource attachment | Endpoint membership in one instance with approved identity | Cannot be attached across authorities merely by changing a label or adding a NIC |

## Sharing and physical placement

Retain the v1.1 zone-specific host-pool baseline. Cross-zone co-residency is not enabled simply because the platform can create isolated virtual networks. The Cyber Centre virtualization guidance strongly recommends against hosting VMs from different network security zones on the same physical hardware. The adopting authority must explicitly assess any alternative, including shared controllers, HCI storage, host compromise and recovery placement. \[[S03](34-appendix-d-sources-and-review-status.md#RA_src_S03)\]

Compatible tenants may share a qualified pool only under the approved domain/zone sharing decision; matching an RZ label is not itself that decision. Enhanced isolation can add dedicated routing and security contexts. Physical dedication is defined separately for hosts, storage, edge, management, backup and key custody. A dedicated host with a shared management plane is not an independently administered platform.

Within a shared domain instance, deny unapproved WSD-to-WSD and tier-to-tier traffic. Mandatory rules and provider-controlled identity attributes take precedence over tenant policy. The same rule applies to same-host, same-subnet and cross-host traffic. Scheduler evacuation, recovery and live mobility must preserve placement and policy constraints; lack of eligible surviving capacity cannot be resolved by weakening them.

Related engineering: [VND §1 — One reference environment, three native realizations](../../engineering/platform-realizations/1-one-reference-environment-three-native-realizations.md#VND_s_001)  •  [VND §2 — Physical placement and the sharing decision](../../engineering/platform-realizations/2-physical-placement-and-the-sharing-decision.md#VND_s_002)

[Previous chapter](6-management-platform-control-and-out-of-band-access.md) · [Chapter index](README.md) · [Next chapter](8-zone-interfaces-routing-and-security-edge-topology.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0008 — Preserve zone-aware host placement and disclose every shared layer](../../adr/0008-preserve-zone-aware-host-placement-and-disclose-every-shared-layer.md)
- [ADR-0018 — Separate tenant administration, WSD lifecycle and domain realization](../../adr/0018-separate-tenant-administration-wsd-lifecycle-and-domain-realization.md)
- [ADR-0023 — Protect mandatory policy and identity selectors from tenant mutation](../../adr/0023-protect-mandatory-policy-and-identity-selectors-from-tenant-mutation.md)

<!-- END GENERATED DECISION LINKS -->
