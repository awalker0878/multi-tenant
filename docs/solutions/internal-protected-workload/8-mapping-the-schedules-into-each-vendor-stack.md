# 8. Mapping the schedules into each vendor stack

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/07_Worked_Infrastructure_Design_and_Acceptance_v1_4.docx) · [Chapter index](README.md)

> **Source:** WD — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: e4a2e42888349b5967f7b3174c78e53171728b13e99e4c78bc3cfb53310f68db -->
<a id="WD14_S08"></a>

The address and route schedules are architectural invariants. A native gateway can implement them through supported static routing, dynamic routing, policy routing or an equivalent qualified construction. The implementation record must show which method is selected; a Terraform resource name is not a substitute for that topology.

On Nutanix, VPC ownership, external subnet attachment, Flow policy and AHV/AOS placement are distinct controls. A shared external subnet is not presumed isolated; use the dedicated handoff pattern until the actual source, connected-route, NAT and return-path behavior is demonstrated. The no-NAT preference remains conditional on the selected supported release.

On VMware/NSX, identify the distributed router, service router, Tier-1 and isolated upstream context actually implementing each next hop. A Tier-0 VRF or another supported isolated construction can be a candidate. No claim about release-specific feature support, scale or licensing follows from the diagram. Verify both native route propagation and the path through stateful enforcement.

On OpenStack, each independent domain uses its own controlled Neutron routing/network context. The provider owns the baseline security groups, port-security settings, permitted address pairs, external attachments and applicable role policy for the base service. Neutron owns its backend objects; raw conflicting OVN changes are not an acceptable enforcement layer. Delegated tenant mutation remains an extension because security-group allows are additive. \[R14-05\]

Where the installed platform cannot represent an essential operation or path, choose a documented qualified alternative or exclude the affected service. Do not preserve a portability claim by silently weakening the security or recovery requirement.


<a id="source-table-94"></a>

| Schedule item | Nutanix candidate | VMware / OpenStack candidate |
| --- | --- | --- |
| Four domain routing scopes | Four qualified VPC/routing instances and corresponding native subnets. | NSX: four independent domain routing scopes; OpenStack: four controlled router/network scopes. |
| Dedicated domain handoffs | Supported isolated VPC external attachments; no-NAT only when qualified. | NSX: isolated upstream/Edge handoffs; OpenStack: controlled external/provider attachments. |
| Tenant administrative rights | Entitled project/RBAC scope; protected categories and baseline policy. | vSphere/NSX scoped roles; Keystone roles with provider-owned baseline network mutation. |
| Endpoint enforcement | Qualified Flow mechanism on same-host and cross-host paths. | NSX mandatory DFW hierarchy; OpenStack provider-managed effective policy and attachment authority. |
| Compute and disk realization | Eligible AHV pools and AOS/storage policy with actual copy/key ownership. | Eligible ESXi/datastores or Nova/Placement/Cinder backends, with the same required outcome. |
| Shared services and ZIPs | Separate service owners provision EC/SE, IPAM/DNS, trust and protection. | Identical ownership requirement; not automatically created by the selected hosting provider. |

Related documents: [VND — Detailed vendor realization and source limitations](../../engineering/platform-realizations/README.md#V14_VND_START)  \|  [PROV — Operation-level tool ownership](../../implementation/provisioning-strategy/README.md#V14_PROV_START)

[Previous chapter](7-service-permissions-and-non-ip-storage-paths.md) · [Chapter index](README.md) · [Next chapter](9-build-sequence-with-explicit-acceptance-dependencies.md)
