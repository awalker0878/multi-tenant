# 23. Nutanix Implementation Profile

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_0.docx) · [Chapter index](README.md)

> **Source:** HB10 — Draft v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 100c760003b9ff956ae369ece65c5ffe7736f6d481496d8df4c99dd6105d4190 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK HB10:200 BEGIN -->

<!-- SOURCE-BLOCK HB10:200 END -->

<!-- SOURCE-BLOCK HB10:201 BEGIN -->

Nutanix AHV with Flow networking/security is a natural implementation target because VPCs provide isolated IP environments with routed overlay subnets and the current Terraform provider exposes v2 resources for VPCs, subnets, routes/PBR, security policies and related constructs. The enterprise abstraction remains the Security Domain Instance; the VPC is the Nutanix realization.

<!-- SOURCE-BLOCK HB10:201 END -->

<!-- SOURCE-BLOCK HB10:202 BEGIN -->


<a id="source-table-202"></a>

| Portable Concept | Nutanix Realization | Guidance |
| --- | --- | --- |
| Tenant Namespace | Project/RBAC/categories and service metadata | Administrative isolation; do not equate project with zone. |
| Security Domain Instance | VPC | Default mapping for overlay-based tenant zone instance. |
| Workload Network | Overlay subnet | Address from IPAM; VNI is implementation detail. |
| Workload Identity | Categories / metadata | Provider-owned security scopes for mandatory controls. |
| Microsegmentation | Flow Network Security policy | Default deny between WSD/tier identities where required. |
| Zone edge | External subnet + routing/PBR as applicable | Connect toward security edge, not directly to a lower-trust domain. |
| Flow intention | Compiled network-security policy and/or ZIP policy | Native policy inside domain; ZIP policy between domains. |

<!-- SOURCE-BLOCK HB10:202 END -->

<!-- SOURCE-BLOCK HB10:203 BEGIN -->

## 23.1 Nutanix Edge Attachment Strategy

<!-- SOURCE-BLOCK HB10:203 END -->

<!-- SOURCE-BLOCK HB10:204 BEGIN -->

Pre-provision platform edge attachment capacity during platform commissioning rather than creating a switch VLAN for every tenant VPC. Multiple VPCs may use standardized edge attachment networks where platform support and assurance permit. Higher-assurance WSDs can receive dedicated attachment contexts. The operational objective is that normal tenant creation causes no switch change.

<!-- SOURCE-BLOCK HB10:204 END -->

<!-- SOURCE-BLOCK HB10:205 BEGIN -->


<a id="source-table-205"></a>

| NUT-001 | New Nutanix automation SHOULD use current supported v2/v4-backed provider resources where those resources satisfy the requirement; legacy resources require an explicit compatibility rationale. |
| --- | --- |

<!-- SOURCE-BLOCK HB10:205 END -->

<!-- SOURCE-BLOCK HB10:206 BEGIN -->


<a id="source-table-206"></a>

| NUT-002 | Nutanix VPC internal routing SHALL NOT be used to bypass a required inter-zone ZIP. |
| --- | --- |

<!-- SOURCE-BLOCK HB10:206 END -->

<!-- SOURCE-BLOCK HB10:207 BEGIN -->


<a id="source-table-207"></a>

| NUT-003 | Provider-managed categories/metadata used for security SHALL be protected from tenant modification. |
| --- | --- |

<!-- SOURCE-BLOCK HB10:207 END -->

[Previous chapter](22-portability-and-platform-conformance.md) · [Chapter index](README.md) · [Next chapter](24-vmware-nsx-implementation-profile.md)
