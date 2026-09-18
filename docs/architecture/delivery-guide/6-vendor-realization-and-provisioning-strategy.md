# 6. Vendor realization and provisioning strategy

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/01_Architecture/Architecture_Kit.docx) · [Chapter index](README.md)

> **Source:** AK — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: f0cd99f187d5f883e0f752e07de20f8878bef02fa1d0b36817674ef59bfd9802 -->
<!-- SOURCE-BLOCK AK:60 BEGIN -->

<a id="AK_06"></a>

<!-- SOURCE-BLOCK AK:60 END -->

<!-- SOURCE-BLOCK AK:61 BEGIN -->

Describe the native realization before deciding the automation structure. Select an owned work package for every resource family and a supported execution mechanism for each lifecycle operation.

<!-- SOURCE-BLOCK AK:61 END -->

<!-- SOURCE-BLOCK AK:62 BEGIN -->

Baseline and related records: [RA §15](../reference/15-cross-vendor-realization-model.md#RA_s_015)  •  [RA §20](../reference/20-provisioning-model-and-infrastructure-work-packages.md#RA_s_020)  •  [RA §24](../reference/24-terraform-across-the-vendor-stacks.md#RA_s_024)  •  [AT §9](../../templates/hld/9-vendor-realization-and-provisioning-strategy.md#AT_09)

<!-- SOURCE-BLOCK AK:62 END -->

<!-- SOURCE-BLOCK AK:63 BEGIN -->


<a id="source-table-63"></a>

| Realization | Architectural responsibilities to retain |
| --- | --- |
| Nutanix | AHV/AOS and Prism/Flow responsibilities; distinct project/RBAC, VPC routing, protected selectors, external handoff and data/protection scope. |
| VMware/NSX | ESXi/vCenter placement and data integration; distributed versus service routing; Tier-1 and isolated upstream/Edge path; provider policy hierarchy. |
| OpenStack | Distribution/controller responsibilities; Keystone/Nova/Placement/Neutron/Cinder; chosen backend; provider-owned baseline network mutation. |
| Common infrastructure | Fabric and OOB, ZIP/security contexts, IPAM/DNS, identity/keys, logging, images and backup remain independently owned integrations. |

<!-- SOURCE-BLOCK AK:63 END -->

<!-- SOURCE-BLOCK AK:64 BEGIN -->

<!-- SOURCE-BLOCK AK:64 END -->

<!-- SOURCE-BLOCK AK:65 BEGIN -->

## P0–P6 as infrastructure work

<!-- SOURCE-BLOCK AK:65 END -->

<!-- SOURCE-BLOCK AK:66 BEGIN -->

P0 establishes trusted bootstrap; P1 commissions physical transport and recovery access; P2 installs native platforms; P3 establishes shared services and security boundaries; P4 allocates tenant/domain infrastructure; P5 creates workload resources and controlled service activation; P6 maintains, recovers, migrates and retires.

<!-- SOURCE-BLOCK AK:66 END -->

<!-- SOURCE-BLOCK AK:67 BEGIN -->

Terraform manages supported resources through qualified APIs. Platform installers, firmware tooling, backup products and other service mechanisms retain their native lifecycle responsibilities. An unsupported provider operation needs a named alternative and accepted handoff; it is not solved by an empty module.

<!-- SOURCE-BLOCK AK:67 END -->

<!-- SOURCE-BLOCK AK:68 BEGIN -->

Baseline and related records: [VC §1](../../engineering/vendor-cards/1-common-scope-and-native-implementation-contract.md#VC_01)  •  [IK §2](../../implementation/delivery-guide/2-work-packages-dependencies-and-authority.md#IK_02)

<!-- SOURCE-BLOCK AK:68 END -->

<!-- SOURCE-BLOCK AK:69 BEGIN -->

<!-- SOURCE-BLOCK AK:69 END -->

[Previous chapter](5-service-resilience-capacity-and-portability.md) · [Chapter index](README.md) · [Next chapter](7-decisions-risk-and-review.md)
