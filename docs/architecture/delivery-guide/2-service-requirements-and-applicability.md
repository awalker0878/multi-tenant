# 2. Service requirements and applicability

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/01_Architecture/Architecture_Kit.docx) · [Chapter index](README.md)

> **Source:** AK — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: f0cd99f187d5f883e0f752e07de20f8878bef02fa1d0b36817674ef59bfd9802 -->
<a id="AK_02"></a>

Start with the required service and information context, then select topology and capability. Keep security categorization separate from uptime, recovery objectives and performance.

Baseline and related records: [RA §2](../reference/2-design-drivers-and-selected-reference-pattern.md#RA_s_002)  •  [RA §14](../reference/14-availability-multi-site-operation-and-recovery-topology.md#RA_s_014)  •  [AT §2](../../templates/hld/2-requirements-and-applicability.md#AT_02)


<a id="source-table-29"></a>

| Requirement group | Decisions to record |
| --- | --- |
| Service and ownership | Service/data/security owners, tenants, workloads, operating support model and excluded responsibilities. |
| Security and placement | Independent confidentiality, integrity and availability impact; zone authority; allowed sharing; location/access and key custody. |
| Resource and connectivity | Compute profiles, block/file/object needs, identity dependencies, allowed flows, external services and exposure. |
| Reliability | Measurement endpoint/window, interruption treatment, failure set, RTO/RPO scope, consistency and restoration acceptance. |
| Lifecycle | Growth, maintenance, migration/exit, support horizon, retention, disposal and operating ownership. |
| Evidence and applicability | Each selected requirement maps to its design home, control owner, verification method and exception policy. |

The workbook preserves all 194 inherited requirement statements as reference text. It does not automatically adopt them for a new project. For each row choose applicable, not applicable with rationale, or unresolved; retain the exact source identifier and edition when assigning selected controls.

The current ITSP.10.033 introduction explicitly supersedes ITSG-33 Annex 3A. Keep any legacy assessment linkage version-aware; do not infer that matching control numbers establish equivalence. \[K02\]

External mechanism context: [K02 — ITSP.10.033 foreword, overview and introduction](https://www.cyber.gc.ca/en/guidance/cyber-security-privacy-risk-management/itsp10033/foreword-overview-introduction)

Acceptance test: no offered service depends on a mandatory requirement whose owner, applicability or implementation boundary is still unknown.

[Previous chapter](1-architecture-work-plan-and-definition-of-done.md) · [Chapter index](README.md) · [Next chapter](3-required-architecture-views.md)
