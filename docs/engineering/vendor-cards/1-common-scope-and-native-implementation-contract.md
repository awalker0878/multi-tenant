# 1. Common scope and native implementation contract

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/02_Engineering/Vendor_Realization_Cards.docx) · [Chapter index](README.md)

> **Source:** VRC — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 5e453a432a4b6c5af7d75ba266945bdb9e01118757cbeec1e15d81f92be32ab0 -->
<!-- SOURCE-BLOCK VRC:16 BEGIN -->

<a id="VC_01"></a>

<!-- SOURCE-BLOCK VRC:16 END -->

<!-- SOURCE-BLOCK VRC:17 BEGIN -->

The common WD fixture is the comparison baseline: tenant-01 and tenant-02, domains D01O/D01R/D02O/D02R, four permanent endpoints, two tenant boundary contexts and explicit shared-service handoffs. A temporary probe is needed for same-domain tests.

<!-- SOURCE-BLOCK VRC:17 END -->

<!-- SOURCE-BLOCK VRC:18 BEGIN -->

Baseline and related records: [VND §1](../platform-realizations/1-one-reference-environment-three-native-realizations.md#VND_s_001)  •  [WD §2](../../solutions/internal-protected-workload/2-reference-decisions-and-infrastructure-boundaries.md#WD14_S02)  •  [WD §11](../../solutions/internal-protected-workload/11-test-resource-capacity-and-mtu-accounting.md#WD14_S11)

<!-- SOURCE-BLOCK VRC:18 END -->

<!-- SOURCE-BLOCK VRC:19 BEGIN -->


<a id="source-table-19"></a>

| Invariant | Native realization must show |
| --- | --- |
| Independent authority | Tenant administration, domain routing, mandatory policy and management scope are separate and enforced. |
| ZIP-controlled transitions | All required forward/reply paths use qualified boundary functions; native paths do not silently bypass them. |
| Shared-service consumption | Exact clients and endpoints, origin-specific reply, backend entitlement and administrative exclusion. |
| Resource eligibility | Compute, storage, copies and recovery remain inside approved sharing/location boundaries. |
| Lifecycle ownership | Install/commission, allocate, update, adopt, replace, delete and interrupted-operation repair have one owner. |
| Equivalent outcome | Same acceptance semantics and observed evidence, not matching native IDs or identical topology. |

<!-- SOURCE-BLOCK VRC:19 END -->

<!-- SOURCE-BLOCK VRC:20 BEGIN -->

<!-- SOURCE-BLOCK VRC:20 END -->

<!-- SOURCE-BLOCK VRC:21 BEGIN -->

Do not install three stacks just to make the first stack qualify. Prove one controlled realization, then repeat the required comparison and representative image/data recovery on a second target. Treat a composite cross-stack WSD as an explicit additional design.

<!-- SOURCE-BLOCK VRC:21 END -->

<!-- SOURCE-BLOCK VRC:22 BEGIN -->

Common prerequisites: adopted design; approved test scope; actual platform tuple; accepted foundation and required bootstrap; scoped identities; capacity and restore material; current native configuration artifacts.

<!-- SOURCE-BLOCK VRC:22 END -->

<!-- SOURCE-BLOCK VRC:23 BEGIN -->

<!-- SOURCE-BLOCK VRC:23 END -->

[Chapter index](README.md) · [Next chapter](2-nutanix-realization-card.md)
