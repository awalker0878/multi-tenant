# 4. OpenStack realization card

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/02_Engineering/Vendor_Realization_Cards.docx) · [Chapter index](README.md)

> **Source:** VRC — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 5e453a432a4b6c5af7d75ba266945bdb9e01118757cbeec1e15d81f92be32ab0 -->
<!-- SOURCE-BLOCK VRC:42 BEGIN -->

<a id="VC_04"></a>

<!-- SOURCE-BLOCK VRC:42 END -->

<!-- SOURCE-BLOCK VRC:43 BEGIN -->

Reference mapping: selected OpenStack distribution; protected Keystone/control services; Nova/Placement compute; Neutron with a named backend; Glance/Cinder and separately selected data/protection services.

<!-- SOURCE-BLOCK VRC:43 END -->

<!-- SOURCE-BLOCK VRC:44 BEGIN -->

Baseline and related records: [RA §18](../../architecture/reference/18-openstack-hosting-stack-reference-realization.md#RA_s_018)  •  [VND §5](../platform-realizations/5-openstack-selected-services-backend-and-mandatory-policy.md#VND_s_005)  •  [WD §8](../../solutions/internal-protected-workload/8-mapping-the-schedules-into-each-vendor-stack.md#WD14_S08)

<!-- SOURCE-BLOCK VRC:44 END -->

<!-- SOURCE-BLOCK VRC:45 BEGIN -->


<a id="source-table-45"></a>

| Build concern | Specific engineering decision / receipt |
| --- | --- |
| Distribution and control | Service/database/messaging versions, certificates, API policy, installer/upgrade owner and controller recovery. |
| Compute and data | Eligible host aggregates/traits/flavours with actual enforcement; images, boot/drivers, Cinder types/backends, storage credentials and protection. |
| Network backend | Selected ML2/OVN or qualified alternative; controller/gateway/compute roles, mappings, distributed routes and external/provider attachments. |
| Mandatory authority | Provider owns baseline security groups, port security, permitted address pairs and external mutation. Direct tenant editing is a qualified extension. |
| Provisioning sequence | Supported distribution build → scoped project/quotas → denied networks/ports/routers and edge → instances/volumes → services and tests. |
| Acceptance / failure | Effective additive policy, extra NIC/provider routes, metadata/DHCP, gateway/control loss, relocation, storage isolation and stale port/router cleanup. |

<!-- SOURCE-BLOCK VRC:45 END -->

<!-- SOURCE-BLOCK VRC:46 BEGIN -->

<!-- SOURCE-BLOCK VRC:46 END -->

<!-- SOURCE-BLOCK VRC:47 BEGIN -->

Neutron describes security groups as additive allow controls; do not treat several groups as a provider deny hierarchy. OVN distributed routing must be included in path analysis, and Nova placement controls must be configured rather than inferred from an aggregate name. \[K06–K08\]

<!-- SOURCE-BLOCK VRC:47 END -->

<!-- SOURCE-BLOCK VRC:48 BEGIN -->

External mechanism context: [K06 — OpenStack Neutron networking concepts](https://docs.openstack.org/neutron/latest/admin/intro-os-networking.html)  •  [K07 — OpenStack OVN reference architecture](https://docs.openstack.org/neutron/latest/admin/ovn/refarch/refarch.html)  •  [K08 — OpenStack Nova host aggregates](https://docs.openstack.org/nova/latest/admin/aggregates.html)

<!-- SOURCE-BLOCK VRC:48 END -->

<!-- SOURCE-BLOCK VRC:49 BEGIN -->

Do not compete with Neutron by directly managing the same backend OVN objects. If the selected API/policy combination cannot protect the required baseline, the corresponding delegated capability is not offered.

<!-- SOURCE-BLOCK VRC:49 END -->

<!-- SOURCE-BLOCK VRC:50 BEGIN -->

<!-- SOURCE-BLOCK VRC:50 END -->

[Previous chapter](3-vmware-and-nsx-realization-card.md) · [Chapter index](README.md) · [Next chapter](5-physical-fabric-and-oob-realization-card.md)
