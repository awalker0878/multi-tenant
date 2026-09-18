# 6. OpenStack: commission a distribution, not a generic label

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/02_Engineering/Platform_Engineering_and_Build_Specifications.docx) · [Chapter index](README.md)

> **Source:** PBS — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 8c2dd9e86b4ea021922777a963534c6b52d85dff8ee398c3a12cc81287356643 -->
<a id="PBS_06"></a>

The selected distribution, backend and enabled services define the real hosting platform. A generic provider cannot make missing services or unsupported capabilities exist.

Design basis and related records: [RA §18](../../architecture/reference/18-openstack-hosting-stack-reference-realization.md#RA_s_018)  •  [VND §5](../platform-realizations/5-openstack-selected-services-backend-and-mandatory-policy.md#VND_s_005)  •  [VC §4](../vendor-cards/4-openstack-realization-card.md#VC_04)


<a id="source-table-75"></a>

| Foundation scope | Build specification | Qualification boundary |
| --- | --- | --- |
| Control and service dependencies | Keystone and selected APIs, databases/messaging, certificates, privileged access and installer ownership. | Control/service health, authority boundaries and recoverability of actual dependencies. |
| Nova and Placement | Eligible hosts, placement policy, aggregates/traits, image/virtual-device classes and resource reserve. | Actual scheduler decisions before and after restart, evacuation or maintenance. |
| Neutron backend | Named ML2/OVN or approved alternative, compute/controller/gateway roles, transport and provider mappings. | Distributed routes, external handoff and all enabled direct-attachment alternatives. |
| Glance/Cinder and data services | Approved images, owned volumes, storage types/backends and selected keys/protection. | Foreign attachment denied, eligible placement, retained copies and useful restore. |

For the OVN reference pattern, OpenStack documents distributed east-west forwarding separately from external gateway handling. A gateway on an external path is therefore not proof that every internal routed flow visits that gateway. Include distributed and provider-network candidates in boundary analysis. \[D07\]

Verified mechanism source: [D07 — OpenStack Neutron OVN reference architecture](https://docs.openstack.org/neutron/latest/admin/ovn/refarch/refarch.html)

Nova’s host-aggregate guidance requires actual scheduler/Placement configuration for the selected isolation model. An aggregate or availability-zone label alone is not enforcement or physical independence. Bind the design to the named configuration and observation that rejects ineligible placement. \[D08\]

Verified mechanism source: [D08 — OpenStack Nova host aggregates](https://docs.openstack.org/nova/latest/admin/aggregates.html)

The accepted handoff names the exact distribution services and versions, backend, enabled extensions, API policy, controller ownership and tested operating limits. Do not directly manage controller-owned OVS/OVN backend objects with a second tool. A backend replacement is an architecture-impacting change with a new failure and policy analysis.

Continue with: [PBS §7](7-openstack-protect-mandatory-network-mutation.md#PBS_07)  •  [QCP §4](../../assurance/qualification-campaign/4-observe-identity-storage-and-protocol-completeness.md#QCP_04)

[Previous chapter](5-vmware-nsx-bind-domain-workload-and-policy-lifecycles.md) · [Chapter index](README.md) · [Next chapter](7-openstack-protect-mandatory-network-mutation.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0026 — Choose and own the actual OpenStack backend and domain boundaries](../../adr/0026-choose-and-own-the-actual-openstack-backend-and-domain-boundaries.md)

<!-- END GENERATED DECISION LINKS -->
