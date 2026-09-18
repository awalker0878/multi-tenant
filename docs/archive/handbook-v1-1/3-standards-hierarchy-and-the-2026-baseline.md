# 3. Standards hierarchy and the 2026 baseline

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<a id="__RefHeading___Toc13291_1645000677"></a>
<a id="sec_3"></a>

The uploaded document used ITSG-33 and ITSP.80.022 as its principal references. This revision adds ITSP.80.023 for cloud/SDN zoning and records an important control-catalogue transition: ITSP.10.033 took effect on 31 March 2026 and explicitly supersedes ITSG-33 Annex 3A. This is not a claim that every publication or lifecycle activity labelled ITSG-33 has been withdrawn. Existing ISSIP artefacts need an explicit migration/crosswalk decision. \[[S00](77-appendix-h-primary-sources-and-implementation-references.md#S00), section 3; [S02](77-appendix-h-primary-sources-and-implementation-references.md#S02), Introduction; [S05](77-appendix-h-primary-sources-and-implementation-references.md#S05), Foreword\]

The current cryptographic reference checked for this release is ITSP.40.111 version 5, effective 29 May 2026. The handbook therefore uses a versioned CryptographicProfile and algorithm inventory rather than embedding a permanent “RSA-2048/TLS-1.2” compliance shortcut. Product module validation, approved modes, operating environments and algorithm lifecycle all remain part of implementation evidence. \[[S10](77-appendix-h-primary-sources-and-implementation-references.md#S10), Effective date and Introduction\]


<a id="source-table-151"></a>

| Reference layer | Application rule |
| --- | --- |
| Applicable legislation, policy, directive and adopted configuration requirements | Determine organizational applicability with the responsible authority; a local exception cannot waive an obligation outside that authority. |
| System categorization, tailored profile and authorization conditions | Allocate each selected control to provider, tenant or shared implementation; record parameters and inherited evidence. |
| Cyber Centre zoning, virtualization, cryptography and lifecycle guidance | Use together, documenting tension between consolidation objectives and physical/zone separation recommendations. |
| This handbook and approved implementation profile | Define portable service semantics and measurable local requirements. |
| Vendor/API/provider documentation and protocol specifications | Validate the exact supported implementation; documentation is not certification or authorization. |

ITSP.10.033 also changes the numbering of Canadian-specific 100-series controls/enhancements to 400-series identifiers. Do not mechanically join old and new catalogues using a numeric string. Retain source edition and original control identifier with every mapping. The PBMM profile remains a contextual source inherited from the original handbook; adoption requires a named profile version and an explicit reconciliation of any legacy catalogue references. \[[S05](77-appendix-h-primary-sources-and-implementation-references.md#S05), Revision changes; [S06](77-appendix-h-primary-sources-and-implementation-references.md#S06)\]

<a id="req_STD_001"></a>

STD-001  The standards register SHALL record edition, effective/review date, applicability, owner and supersession relationships; external changes SHALL trigger an impact review of affected profiles and evidence.

Security authority  \|  Verify: [CT-062](73-appendix-d-conformance-test-catalogue.md#test_CT_062), [CT-075](73-appendix-d-conformance-test-catalogue.md#test_CT_075)  \|  Basis: [S01](77-appendix-h-primary-sources-and-implementation-references.md#S01) / [S02](77-appendix-h-primary-sources-and-implementation-references.md#S02) / [S05](77-appendix-h-primary-sources-and-implementation-references.md#S05) / [S10](77-appendix-h-primary-sources-and-implementation-references.md#S10)  \|  new-v1.1

<a id="req_STD_002"></a>

STD-002  Control mappings SHALL preserve source edition and identifier and SHALL distinguish direct source requirements, local translations and design decisions; a family-level crosswalk SHALL NOT be represented as a completed control assessment.

Security authority  \|  Verify: [CT-062](73-appendix-d-conformance-test-catalogue.md#test_CT_062), [CT-075](73-appendix-d-conformance-test-catalogue.md#test_CT_075)  \|  Basis: [S05](77-appendix-h-primary-sources-and-implementation-references.md#S05)  \|  new-v1.1

[Previous chapter](2-normative-language-invariants-and-authority.md) · [Chapter index](README.md) · [Next chapter](4-categorization-and-policy-profiles.md)
