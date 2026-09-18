# Vendor-stack realizations and reference environment

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/03_Vendor_Stack_Realizations_v1_4.docx)

> **Source:** VND — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 73be32b98783bd7857be8a00928c6894bf16f6bc98c8eb016058d3cf75b9d86b -->

## Chapters

- [1. One reference environment, three native realizations](1-one-reference-environment-three-native-realizations.md)
- [2. Physical placement and the sharing decision](2-physical-placement-and-the-sharing-decision.md)
- [3. Nutanix: component, path and lifecycle realization](3-nutanix-component-path-and-lifecycle-realization.md)
- [4. VMware/NSX: isolated upstream routing and enforcement](4-vmware-nsx-isolated-upstream-routing-and-enforcement.md)
- [5. OpenStack: selected services, backend and mandatory policy](5-openstack-selected-services-backend-and-mandatory-policy.md)
- [6. Portable, composite and migrated service choices](6-portable-composite-and-migrated-service-choices.md)
- [7. Implementation tuple and decision package](7-implementation-tuple-and-decision-package.md)
- [References — Parent basis and external context](08-references-parent-basis-and-external-context.md)
- [v1.4 — Connected infrastructure design and acceptance](09-v1-4-connected-infrastructure-design-and-acceptance.md)

## Source front matter
<!-- SOURCE-BLOCK VND:0 BEGIN -->

<a id="V14_VND_START"></a>

INFRASTRUCTURE ARCHITECTURE  /  VND

<!-- SOURCE-BLOCK VND:0 END -->

<!-- SOURCE-BLOCK VND:1 BEGIN -->

v1.4 linked worked design: [WD — resources, paths, build receipts and acceptance](../../solutions/internal-protected-workload/README.md#V14_WD_START)

<!-- SOURCE-BLOCK VND:1 END -->

<!-- SOURCE-BLOCK VND:2 BEGIN -->

## Portable Multi-Tenant<br>Secure Hosting

<!-- SOURCE-BLOCK VND:2 END -->

<!-- SOURCE-BLOCK VND:3 BEGIN -->

*Vendor-Stack Realizations and Common Reference Environment*

<!-- SOURCE-BLOCK VND:3 END -->

<!-- SOURCE-BLOCK VND:4 BEGIN -->

Draft v1.4  \|  16 September 2026

<!-- SOURCE-BLOCK VND:4 END -->

<!-- SOURCE-BLOCK VND:5 BEGIN -->

A common two-tenant reference environment and its native component, routing, data and lifecycle realization on Nutanix, VMware/NSX and OpenStack.

<!-- SOURCE-BLOCK VND:5 END -->

<!-- SOURCE-BLOCK VND:6 BEGIN -->


<a id="source-table-6"></a>

| Document control | Record |
| --- | --- |
| Document ID / parent | VND — supplement to RA v1.4 |
| Status | Proposed reference design and engineering guidance; adoption and qualification remain separate. |
| Baseline | Draft v1.2 infrastructure architecture, with retained v1.2 requirements and verification catalogues. |
| Audience | Infrastructure, security, network, platform, storage, service and operations owners; provisioning engineers. |
| Authority | Applicable external obligations and adopted controls prevail; supplements cannot silently weaken the parent. |
| Release boundary | Documentation and local document checks only. No live infrastructure deployment, qualification or authorization asserted. |

<!-- SOURCE-BLOCK VND:6 END -->

<!-- SOURCE-BLOCK VND:7 BEGIN -->

<!-- SOURCE-BLOCK VND:7 END -->

<!-- SOURCE-BLOCK VND:8 BEGIN -->

Start here: [Parent architecture — RA](../../architecture/reference/1-purpose-scope-and-architectural-authority.md#RA_s_001)  •  [Document family and gap map — GM](../../assurance/gap-map/1-document-family-scope-and-precedence.md#GM_s_001)

<!-- SOURCE-BLOCK VND:8 END -->

<!-- SOURCE-BLOCK VND:9 BEGIN -->

Keep the eight Word files together after extracting the release package. Cross-document links use sibling filenames and stable bookmarks. START\_HERE.html provides an additional navigation index.

<!-- SOURCE-BLOCK VND:9 END -->

<!-- SOURCE-BLOCK VND:10 BEGIN -->

<!-- SOURCE-BLOCK VND:10 END -->

<a id="VND_contents"></a>

<!-- SOURCE-BLOCK VND:21 BEGIN -->

<!-- SOURCE-BLOCK VND:21 END -->

<!-- SOURCE-BLOCK VND:22 BEGIN -->

Use the contents and named section links to navigate. After later edits, update Word fields and verify pagination before release.

<!-- SOURCE-BLOCK VND:22 END -->

<!-- SOURCE-BLOCK VND:23 BEGIN -->

<!-- SOURCE-BLOCK VND:23 END -->
