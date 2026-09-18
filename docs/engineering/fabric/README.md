# Fabric, security boundaries and infrastructure interfaces

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/02_Fabric_Security_and_Interfaces_v1_4.docx)

> **Source:** NET — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 9c557d7d94dbdf24630994d2676aca3ddfa80e67c2910fb1a29ea4561c591dcf -->

## Chapters

- [1. Transport, routing and overlay ownership](1-transport-routing-and-overlay-ownership.md)
- [2. Isolated attachment units and bounded capacity](2-isolated-attachment-units-and-bounded-capacity.md)
- [3. Worked inter-zone routing and enforcement schedule](3-worked-inter-zone-routing-and-enforcement-schedule.md)
- [4. Address, naming and protocol-family decisions](4-address-naming-and-protocol-family-decisions.md)
- [5. MTU, performance and failure engineering](5-mtu-performance-and-failure-engineering.md)
- [6. Management paths and interface handover](6-management-paths-and-interface-handover.md)
- [References — Parent basis and external context](07-references-parent-basis-and-external-context.md)
- [v1.4 — Connected infrastructure design and acceptance](08-v1-4-connected-infrastructure-design-and-acceptance.md)

## Source front matter
<!-- SOURCE-BLOCK NET:0 BEGIN -->

<a id="V14_NET_START"></a>

INFRASTRUCTURE ARCHITECTURE  /  NET

<!-- SOURCE-BLOCK NET:0 END -->

<!-- SOURCE-BLOCK NET:1 BEGIN -->

v1.4 linked worked design: [WD — resources, paths, build receipts and acceptance](../../solutions/internal-protected-workload/README.md#V14_WD_START)

<!-- SOURCE-BLOCK NET:1 END -->

<!-- SOURCE-BLOCK NET:2 BEGIN -->

## Portable Multi-Tenant<br>Secure Hosting

<!-- SOURCE-BLOCK NET:2 END -->

<!-- SOURCE-BLOCK NET:3 BEGIN -->

*Fabric, Security Boundaries and Infrastructure Interfaces*

<!-- SOURCE-BLOCK NET:3 END -->

<!-- SOURCE-BLOCK NET:4 BEGIN -->

Draft v1.4  \|  16 September 2026

<!-- SOURCE-BLOCK NET:4 END -->

<!-- SOURCE-BLOCK NET:5 BEGIN -->

Buildable routing, attachment, traffic-path, protocol-family, MTU and management-interface guidance, subordinate to the parent architecture.

<!-- SOURCE-BLOCK NET:5 END -->

<!-- SOURCE-BLOCK NET:6 BEGIN -->


<a id="source-table-6"></a>

| Document control | Record |
| --- | --- |
| Document ID / parent | NET — supplement to RA v1.4 |
| Status | Proposed reference design and engineering guidance; adoption and qualification remain separate. |
| Baseline | Draft v1.2 infrastructure architecture, with retained v1.2 requirements and verification catalogues. |
| Audience | Infrastructure, security, network, platform, storage, service and operations owners; provisioning engineers. |
| Authority | Applicable external obligations and adopted controls prevail; supplements cannot silently weaken the parent. |
| Release boundary | Documentation and local document checks only. No live infrastructure deployment, qualification or authorization asserted. |

<!-- SOURCE-BLOCK NET:6 END -->

<!-- SOURCE-BLOCK NET:7 BEGIN -->

<!-- SOURCE-BLOCK NET:7 END -->

<!-- SOURCE-BLOCK NET:8 BEGIN -->

Start here: [Parent architecture — RA](../../architecture/reference/1-purpose-scope-and-architectural-authority.md#RA_s_001)  •  [Document family and gap map — GM](../../assurance/gap-map/1-document-family-scope-and-precedence.md#GM_s_001)

<!-- SOURCE-BLOCK NET:8 END -->

<!-- SOURCE-BLOCK NET:9 BEGIN -->

Keep the eight Word files together after extracting the release package. Cross-document links use sibling filenames and stable bookmarks. START\_HERE.html provides an additional navigation index.

<!-- SOURCE-BLOCK NET:9 END -->

<!-- SOURCE-BLOCK NET:10 BEGIN -->

<!-- SOURCE-BLOCK NET:10 END -->

<a id="NET_contents"></a>

<!-- SOURCE-BLOCK NET:20 BEGIN -->

<!-- SOURCE-BLOCK NET:20 END -->

<!-- SOURCE-BLOCK NET:21 BEGIN -->

Use the contents and named section links to navigate. After later edits, update Word fields and verify pagination before release.

<!-- SOURCE-BLOCK NET:21 END -->

<!-- SOURCE-BLOCK NET:22 BEGIN -->

<!-- SOURCE-BLOCK NET:22 END -->
