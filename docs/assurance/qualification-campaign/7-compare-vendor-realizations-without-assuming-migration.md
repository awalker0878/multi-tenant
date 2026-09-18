# 7. Compare vendor realizations without assuming migration

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/03_Implementation/Qualification_Campaign_and_Evidence_Procedures.docx) · [Chapter index](README.md)

> **Source:** QCP — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 910b84a7b1772f27a456df31a09a96878a72e0f66c8f38cb7e5daaf79254007c -->
<a id="QCP_07"></a>

The architecture is portable when the required outcomes can be realized and operated on another eligible implementation. Transfer of existing data and workload state is a separate claim.

Design basis and related records: [RA §15](../../architecture/reference/15-cross-vendor-realization-model.md#RA_s_015)  •  [RA §27](../../architecture/reference/27-recovery-migration-and-retirement.md#RA_s_027)  •  [VC §1](../../engineering/vendor-cards/1-common-scope-and-native-implementation-contract.md#VC_01)  •  [OPS §6](../../operations/recovery-transition/6-migrate-and-fail-back-without-conflicting-writers.md#OPS_06)


<a id="source-table-78"></a>

| Comparison dimension | Hold constant | Allow to differ and verify |
| --- | --- | --- |
| Service requirements | Tenant authority, zones, approved operations, resource/protection needs and recovery scope. | Native projects, VPCs, routers, segments and gateway arrangements. |
| Security outcome | Denied cross-tenant/management access; explicit boundary and service entitlement. | Distributed versus centralized enforcement locations, with required functions fully evidenced. |
| Resource behaviour | Eligible placement, owned data, image baseline, support and service limits. | Virtual hardware, storage implementation and supported lifecycle mechanisms. |
| Operating acceptance | Monitoring, owner, restore, maintenance and retirement obligations. | Native logs, task models, capture/restore tooling and operational procedures. |
| Exit / transfer | Integrity, consistency, authorized target, identity/keys and controlled cutover. | Conversion method, downtime and supported format/driver changes; no assumed live migration. |

Use the same logical fixture and acceptance assertions for the second stack, then record every material difference. A product-specific extension remains visible with its effect on exit. The target cannot pass by silently dropping inspection, dedicated placement, data protection or another mandatory outcome.

For a representative transfer rehearsal, capture source state, target preparation, final consistency point, transfer integrity, recovered-service tests and authority for the writer switch. Measure effort, elapsed interruption and remaining dependencies. Successful creation of an empty target VM is not evidence that the source workload has been migrated.

Do not require all three stacks to exist for first-stack qualification. A simultaneous composite service across stacks has an additional latency, dependency and failure design.

Continue with: [PBS §9](../../engineering/platform-build/9-release-a-native-build-package-that-can-be-independently-reviewed.md#PBS_09)  •  [QCP §8](8-close-defects-and-issue-a-scoped-campaign-disposition.md#QCP_08)

[Previous chapter](6-build-an-evidence-packet-a-reviewer-can-challenge.md) · [Chapter index](README.md) · [Next chapter](8-close-defects-and-issue-a-scoped-campaign-disposition.md)
