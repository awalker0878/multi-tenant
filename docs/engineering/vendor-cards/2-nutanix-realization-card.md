# 2. Nutanix realization card

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/02_Engineering/Vendor_Realization_Cards.docx) · [Chapter index](README.md)

> **Source:** VRC — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 5e453a432a4b6c5af7d75ba266945bdb9e01118757cbeec1e15d81f92be32ab0 -->
<a id="VC_02"></a>

Reference mapping: AHV/AOS with protected Prism/Flow administration, separate domain routing contexts, protected endpoint policy and independently owned edge and shared-service integrations.

Baseline and related records: [RA §16](../../architecture/reference/16-nutanix-hosting-stack-reference-realization.md#RA_s_016)  •  [VND §3](../platform-realizations/3-nutanix-component-path-and-lifecycle-realization.md#VND_s_003)  •  [WD §8](../../solutions/internal-protected-workload/8-mapping-the-schedules-into-each-vendor-stack.md#WD14_S08)


<a id="source-table-27"></a>

| Build concern | Specific engineering decision / receipt |
| --- | --- |
| Installation and management | Selected supported cluster/Prism/Flow installation, exact component releases, management path, cluster health and recovery dependencies. |
| Pools and data | Eligible AHV placement, AOS/controller sharing, storage classes, image baseline, encryption/protection and failure headroom. |
| Tenancy and policy | Project/RBAC entitlement distinct from VPC routing; provider-owned security categories/selectors and mandatory effective policy. |
| Domain/edge attachment | Native VPC/subnet/gateway objects and supported external handoff. No-NAT is conditional; shared connected subnet isolation must be proven. |
| Provisioning sequence | Installer-owned P2 foundation → address/attachment reservation → denied domain networks → edge/routes/policy → VM/disks → services and tests. |
| Acceptance / failure | Same-host/cross-host controls, native routing, return symmetry, lost task response, protected data, HA placement and isolated restore. |

The official provider repository publishes compatibility and resource-specific lifecycle notes. Use the exact supported combination and inspect replacement/update behaviour; a v2 resource name does not prove every needed operation. No provider release is selected by this kit. \[K05\]

External mechanism context: [K05 — Official Nutanix Terraform provider repository](https://github.com/nutanix/terraform-provider-nutanix)

Stop when the actual gateway/handoff mechanism, required policy authority or resource lifecycle is unsupported or unproven. Use a reviewed alternative or exclude the capability; do not weaken the boundary to complete the run.

[Previous chapter](1-common-scope-and-native-implementation-contract.md) · [Chapter index](README.md) · [Next chapter](3-vmware-and-nsx-realization-card.md)
