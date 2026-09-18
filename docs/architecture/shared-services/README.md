# Shared services, data protection and recovery architecture

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/05_Shared_Services_Data_and_Recovery_v1_4.docx)

> **Source:** SVC — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 2257e6f3badac48b07989244fbfae96643d68cc6633b28e9799a14733bccea3a -->

## Chapters

- [1. Shared service placement and consumption boundaries](1-shared-service-placement-and-consumption-boundaries.md)
- [2. Name, time, initialization and telemetry profiles](2-name-time-initialization-and-telemetry-profiles.md)
- [3. Identity, certificates, keys and independent recovery](3-identity-certificates-keys-and-independent-recovery.md)
- [4. Storage, copies and retained-data ownership](4-storage-copies-and-retained-data-ownership.md)
- [5. Backup capture, independent protection and isolated restore](5-backup-capture-independent-protection-and-isolated-restore.md)
- [6. Failure, recovery, migration and failback topology](6-failure-recovery-migration-and-failback-topology.md)
- [References — Parent basis and external context](07-references-parent-basis-and-external-context.md)
- [v1.4 — Connected infrastructure design and acceptance](08-v1-4-connected-infrastructure-design-and-acceptance.md)

## Source front matter
<!-- SOURCE-BLOCK SVC:0 BEGIN -->

<a id="V14_SVC_START"></a>

INFRASTRUCTURE ARCHITECTURE  /  SVC

<!-- SOURCE-BLOCK SVC:0 END -->

<!-- SOURCE-BLOCK SVC:1 BEGIN -->

v1.4 linked worked design: [WD — resources, paths, build receipts and acceptance](../../solutions/internal-protected-workload/README.md#V14_WD_START)

<!-- SOURCE-BLOCK SVC:1 END -->

<!-- SOURCE-BLOCK SVC:2 BEGIN -->

## Portable Multi-Tenant<br>Secure Hosting

<!-- SOURCE-BLOCK SVC:2 END -->

<!-- SOURCE-BLOCK SVC:3 BEGIN -->

*Shared Services, Data Protection and Recovery Architecture*

<!-- SOURCE-BLOCK SVC:3 END -->

<!-- SOURCE-BLOCK SVC:4 BEGIN -->

Draft v1.4  \|  16 September 2026

<!-- SOURCE-BLOCK SVC:4 END -->

<!-- SOURCE-BLOCK SVC:5 BEGIN -->

The infrastructure behind shared consumption endpoints, data copies, key custody, protection and recovery, with clear operational and administrative boundaries.

<!-- SOURCE-BLOCK SVC:5 END -->

<!-- SOURCE-BLOCK SVC:6 BEGIN -->


<a id="source-table-6"></a>

| Document control | Record |
| --- | --- |
| Document ID / parent | SVC — supplement to RA v1.4 |
| Status | Proposed reference design and engineering guidance; adoption and qualification remain separate. |
| Baseline | Draft v1.2 infrastructure architecture, with retained v1.2 requirements and verification catalogues. |
| Audience | Infrastructure, security, network, platform, storage, service and operations owners; provisioning engineers. |
| Authority | Applicable external obligations and adopted controls prevail; supplements cannot silently weaken the parent. |
| Release boundary | Documentation and local document checks only. No live infrastructure deployment, qualification or authorization asserted. |

<!-- SOURCE-BLOCK SVC:6 END -->

<!-- SOURCE-BLOCK SVC:7 BEGIN -->

<!-- SOURCE-BLOCK SVC:7 END -->

<!-- SOURCE-BLOCK SVC:8 BEGIN -->

Start here: [Parent architecture — RA](../reference/1-purpose-scope-and-architectural-authority.md#RA_s_001)  •  [Document family and gap map — GM](../../assurance/gap-map/1-document-family-scope-and-precedence.md#GM_s_001)

<!-- SOURCE-BLOCK SVC:8 END -->

<!-- SOURCE-BLOCK SVC:9 BEGIN -->

Keep the eight Word files together after extracting the release package. Cross-document links use sibling filenames and stable bookmarks. START\_HERE.html provides an additional navigation index.

<!-- SOURCE-BLOCK SVC:9 END -->

<!-- SOURCE-BLOCK SVC:10 BEGIN -->

<!-- SOURCE-BLOCK SVC:10 END -->

<a id="SVC_contents"></a>

<!-- SOURCE-BLOCK SVC:20 BEGIN -->

<!-- SOURCE-BLOCK SVC:20 END -->

<!-- SOURCE-BLOCK SVC:21 BEGIN -->

Use the contents and named section links to navigate. After later edits, update Word fields and verify pagination before release.

<!-- SOURCE-BLOCK SVC:21 END -->

<!-- SOURCE-BLOCK SVC:22 BEGIN -->

<!-- SOURCE-BLOCK SVC:22 END -->
