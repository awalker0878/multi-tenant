# 6. Resolve the actual inputs before execution

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/00_Delivery_Map.docx) · [Chapter index](README.md)

> **Source:** DEL — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: d8c2790ff7bb408283a9156a369cc6c4394131e7d44bfd130bfa27e7d82b5783 -->
<a id="DEL_06"></a>

The kit develops the method and expected infrastructure outcomes. Actual site facts remain the responsibility of the named project and infrastructure owners.

Design basis and related records: [GM §4](../../assurance/gap-map/4-open-decision-package-for-implementation.md#GM_s_004)  •  [WD §14](../../solutions/internal-protected-workload/14-remaining-decisions-and-release-boundaries.md#WD14_S14)  •  [ET §1](../../templates/lld/1-design-identity-scope-and-baseline.md#ET_01)


<a id="source-table-66"></a>

| Required input | Responsible role | Dependent decision |
| --- | --- | --- |
| Site, cells and physical dependencies | Site/facility/platform owners. | Actual inventory, power/rack/link groups and accepted commissioning. |
| Sharing, management and selected obligations | Architecture and security authorities. | Eligible compute/storage/control and recovery boundaries. |
| Exact supported implementation | Platform/network/service engineering. | Hardware, firmware, releases, features, licences and native operation support. |
| Actual addressing and interfaces | Network/edge/service owners. | IPAM, routes, policy, reply paths and single configuration ownership. |
| Service, capacity and data constraints | Service/data/operations owners. | Performance, failure model, retention, location, RTO/RPO and support. |
| Native execution artifacts and real evidence | Implementers, assurance and designated approvers. | Reviewed MOP, actual observation, scoped qualification, readiness and activation. |

Unknown values do not become vendor defaults. Assign a blocking gate and an owner. Engineering exploration and safeguarded qualification preparation can continue in parallel where authorized, but production construction and activation cannot depend on unaccepted boundaries or support assumptions.

Native configuration, installation and data-movement artifacts are separate build deliverables. This release does not invent a universal Terraform implementation or turn reference addresses into a deployable network. Physical work uses qualified personnel and accepted site/manufacturer procedures.

Continue with: [PBS §9](../../engineering/platform-build/9-release-a-native-build-package-that-can-be-independently-reviewed.md#PBS_09)  •  [OPS §8](../../operations/recovery-transition/8-accept-operational-responsibility-for-the-delivered-scope.md#OPS_08)

[Previous chapter](5-review-the-design-through-realistic-change-and-failure.md) · [Chapter index](README.md) · [Next chapter](7-navigate-the-developed-document-family.md)
