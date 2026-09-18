# 1. Document family, scope and precedence

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/01_Gap_Map_and_Decision_Register_v1_4.docx) · [Chapter index](README.md)

> **Source:** GM — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 26dbaac8c13797b58ca5d057f76df8b3da63ec3f4b336036f18f5c6902512207 -->
<!-- SOURCE-BLOCK GM:22 BEGIN -->

<a id="__RefHeading___Toc1259_342027687"></a>
<a id="GM_s_001"></a>

<!-- SOURCE-BLOCK GM:22 END -->

<!-- SOURCE-BLOCK GM:23 BEGIN -->

Parent architecture: [RA §1](../../architecture/reference/1-purpose-scope-and-architectural-authority.md#RA_s_001)  •  [RA §30](../../architecture/reference/30-implementation-handoff-and-delivery-sequence.md#RA_s_030)

<!-- SOURCE-BLOCK GM:23 END -->

<!-- SOURCE-BLOCK GM:24 BEGIN -->

This release develops the infrastructure reference architecture rather than a provisioning application. The parent defines the durable topology, security boundaries and cross-platform provisioning strategy. The supplements explain the engineering choices that make that architecture buildable and operable. They use the parent’s terminology, decision IDs, interface IDs and P0–P6 work packages. The v1.2 baseline is cited as [B2](06-references-parent-basis-and-external-context.md#GM_src_B2); new worked examples and engineering elaborations are proposed reference content, not facts about a deployed site.

<!-- SOURCE-BLOCK GM:24 END -->

<!-- SOURCE-BLOCK GM:25 BEGIN -->


<a id="source-table-25"></a>

| Document | Primary responsibility | Does not replace |
| --- | --- | --- |
| RA · parent reference architecture | What exists, how it relates, security/authority/failure boundaries and selected provisioning model. | Site low-level design, actual vendor qualification or formal authorization. |
| GM · gap and decision map | Trace each knowledge/design gap to its parent, detailed treatment, owner, gate and remaining evidence. | A declaration that writing a paragraph closes implementation risk. |
| NET · fabric and security | Routing and attachment mechanisms, path analysis, protocol families, MTU and management interfaces. | Vendor switch configuration or actual site address plan. |
| VND · vendor realization | Common fixture and native component/path/lifecycle design across the three stacks. | Unverified product compatibility, licences or provider operation coverage. |
| PROV · provisioning | Owned work packages, bootstrap, tool coverage, activation, recovery of changes and adoption. | A custom controller/API specification or executable deployment. |
| SVC · services/data/recovery | Consumption and management, names/trust, storage/copies, protection and recovery dependencies. | Business application architecture or invented retention/cryptographic parameters. |
| QUAL · site and qualification | Actual design records, capacity/service decisions, applicability, evidence and operational acceptance. | An executed test campaign or authority-issued risk decision. |

<!-- SOURCE-BLOCK GM:25 END -->

<!-- SOURCE-BLOCK GM:26 BEGIN -->

<!-- SOURCE-BLOCK GM:26 END -->

<!-- SOURCE-BLOCK GM:27 BEGIN -->

Precedence is: applicable external authority and adopted control/authorization conditions; the adopted parent reference and explicit architecture decisions; controlled supplements within that scope; the approved site implementation design; and the actual as-built/evidence records. A site variation can differ only through an explicit accepted decision. A supplement cannot silently amend a mandatory parent outcome or reinterpret a source as less restrictive.

<!-- SOURCE-BLOCK GM:27 END -->

<!-- SOURCE-BLOCK GM:28 BEGIN -->

Documents are linked through stable document IDs and section bookmarks. Each supplement points back to its applicable parent chapters; parent chapters point to the detail’s primary home. All Word files must remain together after extracting the package for relative cross-document links. Readable document/section labels remain usable even when a viewer does not open a bookmark automatically. The included START\_HERE.html provides a second navigation route.

<!-- SOURCE-BLOCK GM:28 END -->

<!-- SOURCE-BLOCK GM:29 BEGIN -->

All content is proposed for organizational adoption. No installed version, address, hardware count, service target or personnel assignment is invented as a production fact. The parent’s 194 requirement identifiers remain in the reference register; the 80 CT procedures and 12 realization addenda remain not-run. Prior optional API/schema implementation material is not republished as a functioning controller. Its earlier implementation defects are not claimed fixed by this architecture-led release.

<!-- SOURCE-BLOCK GM:29 END -->

<!-- SOURCE-BLOCK GM:30 BEGIN -->

Related engineering: [Parent authority and scope](../../architecture/reference/1-purpose-scope-and-architectural-authority.md#RA_s_001)  •  [Adoption and service gates](../site-qualification/1-from-proposed-architecture-to-accepted-service.md#QUAL_s_001)

<!-- SOURCE-BLOCK GM:30 END -->

[Chapter index](README.md) · [Next chapter](2-primary-knowledge-homes-and-cross-cutting-changes.md)
