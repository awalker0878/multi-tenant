# 2. Work packages, dependencies and authority

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/03_Implementation/Implementation_Kit.docx) · [Chapter index](README.md)

> **Source:** IK — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: b16b8843bfbafd1b417d611903f5b8038f4794efd4f22c995bee1cb36f9ebb41 -->
<!-- SOURCE-BLOCK IK:25 BEGIN -->

<a id="IK_02"></a>

<!-- SOURCE-BLOCK IK:25 END -->

<!-- SOURCE-BLOCK IK:26 BEGIN -->

Maintain separate execution scopes even when one delivery workflow coordinates the whole environment. Handoffs pass only the identities, capacity and configuration facts the next owner needs.

<!-- SOURCE-BLOCK IK:26 END -->

<!-- SOURCE-BLOCK IK:27 BEGIN -->

Baseline and related records: [RA §20](../../architecture/reference/20-provisioning-model-and-infrastructure-work-packages.md#RA_s_020)  •  [PROV §1](../provisioning-strategy/1-provisioning-scopes-ownership-and-accepted-handoffs.md#PROV_s_001)  •  [WD §10](../../solutions/internal-protected-workload/10-resource-ownership-protection-and-change-receipts.md#WD14_S10)

<!-- SOURCE-BLOCK IK:27 END -->

<!-- SOURCE-BLOCK IK:28 BEGIN -->


<a id="source-table-28"></a>

| Package | Execute and observe | Accepted handoff |
| --- | --- | --- |
| P0 — bootstrap | Establish restricted administration, minimum time/name/trust and recoverable tooling. | Accountable temporary dependencies; usable recovery access and custody. |
| P1 — foundation | Commission the accepted hardware, OOB, fabric and attachment capacity. | As-built physical links, routing, MTU, fault behaviour and available slots. |
| P2 — platform | Install the chosen supported stack; configure eligible compute, storage and transport. | Exact tuple, native ownership, baseline and service limitations. |
| P3 — services | Establish security contexts, names, identity, keys, logging and protection. | Published consumption interfaces, return paths and protection/custody. |
| P4 — tenant/domain | Allocate entitled scope, addresses, domains, networks and mandatory policy. | Native identities, eligibility and boundaries under deny. |
| P5 — resources/activation | Create owned VMs/disks, bind services, verify and activate within authority. | Current test evidence, initial operational readiness and accepted live path. |
| P6 — lifecycle | Maintain, expand, recover, migrate or retire under the owning scopes. | Changed as-built records, requalification and retained-data obligations. |

<!-- SOURCE-BLOCK IK:28 END -->

<!-- SOURCE-BLOCK IK:29 BEGIN -->

<!-- SOURCE-BLOCK IK:29 END -->

<!-- SOURCE-BLOCK IK:30 BEGIN -->

P2 installation can depend on accepted P0 bootstrap services. Complete P2/P3 offered-service acceptance together before ordinary tenant allocation. Record and retire temporary trust deliberately; do not create a circular recovery dependency.

<!-- SOURCE-BLOCK IK:30 END -->

<!-- SOURCE-BLOCK IK:31 BEGIN -->

<!-- SOURCE-BLOCK IK:31 END -->

[Previous chapter](1-implementation-workplan-and-required-inputs.md) · [Chapter index](README.md) · [Next chapter](3-staging-bootstrap-and-physical-commissioning.md)
