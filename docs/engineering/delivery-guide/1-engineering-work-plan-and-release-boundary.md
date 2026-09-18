# 1. Engineering work plan and release boundary

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/02_Engineering/Engineering_Kit.docx) · [Chapter index](README.md)

> **Source:** EK — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 0aeb8ee0a114d3ed23e97c684cc9812a0fa6ea5252e49f0c902132bf4e053a7d -->
<!-- SOURCE-BLOCK EK:17 BEGIN -->

<a id="EK_01"></a>

<!-- SOURCE-BLOCK EK:17 END -->

<!-- SOURCE-BLOCK EK:18 BEGIN -->

Engineering supplies exact parameters, native resource choices, compatibility evidence and reproducible build/verification instructions. It does not silently change the approved sharing model or service promise.

<!-- SOURCE-BLOCK EK:18 END -->

<!-- SOURCE-BLOCK EK:19 BEGIN -->

Baseline and related records: [RA §30](../../architecture/reference/30-implementation-handoff-and-delivery-sequence.md#RA_s_030)  •  [QUAL §2](../../assurance/site-qualification/2-site-low-level-design-and-dependency-schedule.md#QUAL_s_002)  •  [ET §1](../../templates/lld/1-design-identity-scope-and-baseline.md#ET_01)

<!-- SOURCE-BLOCK EK:19 END -->

<!-- SOURCE-BLOCK EK:20 BEGIN -->


<a id="source-table-20"></a>

| Engineering output | Required inputs | Buildable when |
| --- | --- | --- |
| Site and physical plan | Adopted site/cell scope, inventory, facility protections and failure model. | Every device/link has a role, endpoint, owner and supported configuration basis. |
| Logical/network/security plan | Domains, service flows, ZIP decisions and family requirements. | Every next hop, return path, enforcement point and rejected alternative is explainable. |
| Resource/service plan | Compute/data classes, identity/key/protection and recovery constraints. | Actual pool/backend/role/copy membership and measured capacities are explicit. |
| Tool and lifecycle plan | Exact products/APIs/providers and native installation ownership. | All required lifecycle operations have supported ownership and failure treatment. |
| Release/test pack | Current LLD, artifacts, MOP, test scope and expected outcomes. | Implementers can execute controlled steps and capture the required observations. |

<!-- SOURCE-BLOCK EK:20 END -->

<!-- SOURCE-BLOCK EK:21 BEGIN -->

<!-- SOURCE-BLOCK EK:21 END -->

<!-- SOURCE-BLOCK EK:22 BEGIN -->

Use EK-01–EK-09 as deliverable IDs. The actual site configuration, bill of materials and command/API artifacts are produced from approved values, never from documentation addresses. Unresolved site values remain explicit blockers at their relevant stage.

<!-- SOURCE-BLOCK EK:22 END -->

<!-- SOURCE-BLOCK EK:23 BEGIN -->

Engineering release is not platform qualification. A supported design still needs actual build results, boundary tests, performance and recovery evidence.

<!-- SOURCE-BLOCK EK:23 END -->

<!-- SOURCE-BLOCK EK:24 BEGIN -->

<!-- SOURCE-BLOCK EK:24 END -->

[Chapter index](README.md) · [Next chapter](2-site-equipment-and-physical-foundation.md)
