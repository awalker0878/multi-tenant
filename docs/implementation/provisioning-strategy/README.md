# Cross-stack provisioning and commissioning strategy

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/04_Provisioning_and_Commissioning_v1_4.docx)

> **Source:** PROV — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 483df77cff70166fbdfdf711135efa3beeecc8fe1015a58290cbebff5b80bdfd -->

## Chapters

- [1. Provisioning scopes, ownership and accepted handoffs](1-provisioning-scopes-ownership-and-accepted-handoffs.md)
- [2. Day-0 and steady-state commissioning without circular dependencies](2-day-0-and-steady-state-commissioning-without-circular-dependencies.md)
- [3. Terraform, native tools and operation-level support](3-terraform-native-tools-and-operation-level-support.md)
- [4. End-to-end fixture provisioning and safe activation](4-end-to-end-fixture-provisioning-and-safe-activation.md)
- [5. Concurrency, ownership and failed execution](5-concurrency-ownership-and-failed-execution.md)
- [6. Brownfield adoption, growth and retirement](6-brownfield-adoption-growth-and-retirement.md)
- [References — Parent basis and external context](07-references-parent-basis-and-external-context.md)
- [v1.4 — Connected infrastructure design and acceptance](08-v1-4-connected-infrastructure-design-and-acceptance.md)

## Source front matter
<a id="V14_PROV_START"></a>

INFRASTRUCTURE ARCHITECTURE  /  PROV

v1.4 linked worked design: [WD — resources, paths, build receipts and acceptance](../../solutions/internal-protected-workload/README.md#V14_WD_START)

## Portable Multi-Tenant<br>Secure Hosting

*Cross-Stack Provisioning and Commissioning Strategy*

Draft v1.4  \|  16 September 2026

The infrastructure sequence, authority boundaries and tool responsibilities that establish foundations, allocate tenants, activate workloads and safely manage change.


<a id="source-table-6"></a>

| Document control | Record |
| --- | --- |
| Document ID / parent | PROV — supplement to RA v1.4 |
| Status | Proposed reference design and engineering guidance; adoption and qualification remain separate. |
| Baseline | Draft v1.2 infrastructure architecture, with retained v1.2 requirements and verification catalogues. |
| Audience | Infrastructure, security, network, platform, storage, service and operations owners; provisioning engineers. |
| Authority | Applicable external obligations and adopted controls prevail; supplements cannot silently weaken the parent. |
| Release boundary | Documentation and local document checks only. No live infrastructure deployment, qualification or authorization asserted. |

Start here: [Parent architecture — RA](../../architecture/reference/1-purpose-scope-and-architectural-authority.md#RA_s_001)  •  [Document family and gap map — GM](../../assurance/gap-map/1-document-family-scope-and-precedence.md#GM_s_001)

Keep the eight Word files together after extracting the release package. Cross-document links use sibling filenames and stable bookmarks. START\_HERE.html provides an additional navigation index.

<a id="PROV_contents"></a>

Use the contents and named section links to navigate. After later edits, update Word fields and verify pagination before release.
