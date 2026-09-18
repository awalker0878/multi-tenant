# 4. Native realization and provisioning ownership

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/04_Shared/Worked_Delivery_Example.docx) · [Chapter index](README.md)

> **Source:** WDE — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: ae4ea65ea564fe848f214f5154ca4b67726eb6628d07a4b4f7714210e49ccd0d -->
<a id="EX_04"></a>

The architecture identifiers remain stable while the selected stack supplies native components and operation semantics.

Baseline and related records: [VC §2](../../engineering/vendor-cards/2-nutanix-realization-card.md#VC_02)  •  [VC §3](../../engineering/vendor-cards/3-vmware-and-nsx-realization-card.md#VC_03)  •  [VC §4](../../engineering/vendor-cards/4-openstack-realization-card.md#VC_04)  •  [WD §8](../internal-protected-workload/8-mapping-the-schedules-into-each-vendor-stack.md#WD14_S08)


<a id="source-table-44"></a>

| Owner / resource | Nutanix candidate | VMware/NSX or OpenStack candidate |
| --- | --- | --- |
| Platform domain routing | Separate qualified VPC/routing contexts; controlled external attachments. | NSX: independent Tier-1 and supported isolated upstream contexts. OpenStack: separate controlled Neutron routing/network scopes. |
| Mandatory endpoint policy | Qualified Flow enforcement and protected categories. | NSX: protected group/rule hierarchy. OpenStack: provider-owned effective policy and restricted mutation of ports/groups/attachments. |
| Compute / storage | Eligible AHV pools and AOS-backed data with explicit sharing and key/copy scope. | Eligible ESXi/datastore or Nova/Placement/Cinder configuration; actual co-residency and supported restore. |
| Security and services | Edge/service owners instantiate EC/SE and permitted flows; authoritative IPAM/DNS and protection owners supply their functions. | Same architectural responsibility; not assumed to be supplied by the vSphere, NSX or OpenStack provider alone. |
| Provisioning | Supported native bootstrap plus qualified resource API/provider operations. | Supported installation/lifecycle tools plus scoped Terraform/API ownership; no competing writes to controller-owned backends. |

The actual operation-coverage record must identify observe, create, update, adopt/import, replace, delete and unknown-outcome reconciliation. A candidate mechanism with only create support is not a fully managed service. The selected native commands and resource arguments remain engineering inputs.

Exact versions, licenses, hardware, gateway modes and enabled features remain unselected. In particular, verify the NSX parent mode/VRF compatibility recorded in KIT-TN-01 before accepting that candidate design.

[Previous chapter](3-forward-route-return-route-and-service-permission.md) · [Chapter index](README.md) · [Next chapter](5-commission-qualify-prepare-and-activate.md)
