# 6. Inputs still required for an actual deployment

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/07_Quality/prior_v1_0/00_Delivery_Map.docx) · [Chapter index](README.md)

> **Source:** DEL10 — Delivery kits v1.0. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: e332c1b37e63439169adf8b105573577fa1ea61bf32f6c3ba383dd69d83a788b -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK DEL10:59 BEGIN -->

<a id="DEL_06"></a>

<!-- SOURCE-BLOCK DEL10:59 END -->

<!-- SOURCE-BLOCK DEL10:60 BEGIN -->

The kits are complete as reusable working material. An actual build still needs the following inputs from the responsible people and systems; no value is inferred from an example.

<!-- SOURCE-BLOCK DEL10:60 END -->

<!-- SOURCE-BLOCK DEL10:61 BEGIN -->

Baseline and related records: [GM §4](../../assurance/gap-map/4-open-decision-package-for-implementation.md#GM_s_004)  •  [WD §14](../../solutions/internal-protected-workload/14-remaining-decisions-and-release-boundaries.md#WD14_S14)

<!-- SOURCE-BLOCK DEL10:61 END -->

<!-- SOURCE-BLOCK DEL10:62 BEGIN -->


<a id="source-table-62"></a>

| Input | Owner to supply it | Blocks |
| --- | --- | --- |
| Named site, cells, equipment and actual physical failure groups | Site, facility and platform owners | G1 detailed physical commissioning |
| Approved zone/co-residency and management separation | Architecture and security authority | Affected host, storage and privileged paths |
| Exact hardware, firmware, software, API, provider and entitlement combination | Platform/network/service engineering | G2 support and capability qualification |
| Actual IP/DNS, routing, ZIP and service handoffs | Network/security/service owners | Dependent path construction and activation |
| Service targets, capacity, retention, keys and location constraints | Service/data/security owners | Advertising the offered service |
| Native automation and installation/configuration artifacts | Assigned technical owners | Execution of supported P0–P6 operations |
| Real observations, evidence and operating authority | Assurance, operations and designated approvers | G2, initial G4 and production G3 |

<!-- SOURCE-BLOCK DEL10:62 END -->

<!-- SOURCE-BLOCK DEL10:63 BEGIN -->

<!-- SOURCE-BLOCK DEL10:63 END -->

<!-- SOURCE-BLOCK DEL10:64 BEGIN -->

Scope special devices, bare metal, container hosting, public access, L2 stretch or cross-stack composite services separately. The base VM-oriented kit provides the interface and acceptance pattern, not unqualified implementations of these extensions.

<!-- SOURCE-BLOCK DEL10:64 END -->

<!-- SOURCE-BLOCK DEL10:65 BEGIN -->

Start by assigning the architecture owner, completing AT §1 and marking requirement applicability. Engineering can investigate options in parallel, but must not treat an unresolved architecture choice as an approved build parameter.

<!-- SOURCE-BLOCK DEL10:65 END -->

[Previous chapter](5-review-sequence-and-change-control.md) · [Chapter index](README.md)
