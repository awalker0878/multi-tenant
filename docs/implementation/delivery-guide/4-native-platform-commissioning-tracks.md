# 4. Native platform commissioning tracks

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/03_Implementation/Implementation_Kit.docx) · [Chapter index](README.md)

> **Source:** IK — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: b16b8843bfbafd1b417d611903f5b8038f4794efd4f22c995bee1cb36f9ebb41 -->
<a id="IK_04"></a>

Use the selected vendor track, not all three stacks simultaneously by default. The same reference service is repeated on the next stack to establish a separate portability claim.

Baseline and related records: [VC §2](../../engineering/vendor-cards/2-nutanix-realization-card.md#VC_02)  •  [VC §3](../../engineering/vendor-cards/3-vmware-and-nsx-realization-card.md#VC_03)  •  [VC §4](../../engineering/vendor-cards/4-openstack-realization-card.md#VC_04)  •  [RA §22](../../architecture/reference/22-vendor-platform-and-shared-service-commissioning.md#RA_s_022)


<a id="source-table-42"></a>

| Track | Native installation and preparation | Required observations |
| --- | --- | --- |
| Nutanix / RB-02 | Supported AHV/AOS and Prism installation; chosen Flow networking/security; eligible host/controller/storage scope and isolated external handoffs. | Actual VPC/external routing and policy; same-host enforcement; no shared-connected bypass; storage, key and controller dependencies. |
| VMware/NSX / RB-03 | Supported vCenter/ESXi and storage; NSX management, transport/Edge topology, independent domain and upstream contexts. | Actual distributed and service-router paths; gateway mode compatibility; no unauthorized route propagation; DFW ownership and Edge failure behaviour. |
| OpenStack / RB-04 | Selected distribution services, databases/messaging, Keystone/Nova/Placement, Neutron backend, Glance/Cinder and offered services. | Scheduler constraints; provider-owned mandatory network mutation; additive group behaviour; distributed paths, gateway and storage dependencies. |

## Common platform receipt

Record product, API, provider and installer versions; firmware/drivers and hardware; enabled features and entitlements; control and storage placement; resource identity and authoritative writer; accepted management and data paths; actual tests; limitations; and supported upgrade/recovery approach.

Terraform starts at the supported resource API boundary. A native installer can remain the owner of platform installation, upgrades or controller-managed objects. Do not import or directly edit backend objects owned by another control system merely to make every step appear to be Terraform.

A documented vendor feature is not a qualified tuple. KIT-TN-01 adds an explicit NSX parent-gateway mode compatibility check; apply it to the selected release before choosing a Tier-0 VRF realization.

External mechanism context: [K05 — Official Nutanix Terraform provider repository](https://github.com/nutanix/terraform-provider-nutanix)  •  [K06 — OpenStack Neutron networking concepts](https://docs.openstack.org/neutron/latest/admin/intro-os-networking.html)  •  [K07 — OpenStack OVN reference architecture](https://docs.openstack.org/neutron/latest/admin/ovn/refarch/refarch.html)  •  [K08 — OpenStack Nova host aggregates](https://docs.openstack.org/nova/latest/admin/aggregates.html)  •  [K09 — Broadcom KB 442835 — Tier-0 VRF and active-active stateful HA](https://knowledge.broadcom.com/external/article/442835/cannot-add-tier0-vrf-gateway-to-a-tier0.html)

[Previous chapter](3-staging-bootstrap-and-physical-commissioning.md) · [Chapter index](README.md) · [Next chapter](5-shared-security-services-and-protection.md)
