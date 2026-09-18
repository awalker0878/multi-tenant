# 4. Categorization and policy profiles

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<a id="__RefHeading___Toc13293_1645000677"></a>
<a id="sec_4"></a>

Confidentiality, integrity and availability are independent impact assessments. “Protected B” is not a network topology, and “Medium availability” in a security categorization is not a service uptime target. The request records the three category fields separately, selects a SecurityProfile for controls, selects an AssuranceProfile for isolation and evidence, and selects AvailabilityProfile and RecoveryProfile for service behavior. A profile reference is immutable by name/version and resolves to a controlled digest. \[[S00](77-appendix-h-primary-sources-and-implementation-references.md#S00), sections 3 and 8; [S06](77-appendix-h-primary-sources-and-implementation-references.md#S06)\]


<a id="source-table-159"></a>

| Object | Defines | Does not mean |
| --- | --- | --- |
| SecurityProfile | Applicable category envelope, control catalogue edition, control/parameter selection and obligations | Automatic authorization for all data of the same confidentiality label |
| AssuranceProfile | Allowed sharing, enforcement strength and qualification/evidence depth | A replacement for formal Security Assurance Levels |
| AvailabilityProfile | Measured service objective, failure tolerance and maintenance behavior | The “availability” impact category |
| RecoveryProfile | Recovery scope, RTO, RPO, consistency, fencing and rehearsal | A guaranteed application recovery merely from replication |
| PlacementProfile | Eligible sites, location/access restrictions, capacity and platform capabilities | Residency automatically resolving jurisdiction or control |
| CryptographicProfile | Algorithms/modes, key custody, certificate lifecycle and crypto agility | A product logo or unchecked encryption flag |

Profile definitions are provider/security-authority controlled. Consumers can select entitled profiles, not edit their mandatory controls. Requested optional features may strengthen requirements; they cannot reduce a mandatory minimum. A request with contradictory requirements is rejected with a specific explanation rather than placed on a weaker profile. The reference defaults in Appendix F are proposed service-design values, not government-mandated time limits or a claim of measured capability.

<a id="req_CAT_001"></a>

CAT-001  Each WSD SHALL record confidentiality, integrity and availability separately and SHALL reference the exact adopted SecurityProfile, AssuranceProfile, AvailabilityProfile, RecoveryProfile and PlacementProfile.

Security authority  \|  Verify: [CT-017](73-appendix-d-conformance-test-catalogue.md#test_CT_017), [CT-062](73-appendix-d-conformance-test-catalogue.md#test_CT_062), [CT-069](73-appendix-d-conformance-test-catalogue.md#test_CT_069)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00) / [S05](77-appendix-h-primary-sources-and-implementation-references.md#S05) / [S06](77-appendix-h-primary-sources-and-implementation-references.md#S06)  \|  new-v1.1

<a id="req_CAT_002"></a>

CAT-002  Profile resolution SHALL be immutable and authorized; a consumer SHALL NOT lower mandatory requirements by editing a profile, forging a status field or choosing an unsupported category.

Automation platform  \|  Verify: [CT-017](73-appendix-d-conformance-test-catalogue.md#test_CT_017), [CT-018](73-appendix-d-conformance-test-catalogue.md#test_CT_018)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  new-v1.1

[Previous chapter](3-standards-hierarchy-and-the-2026-baseline.md) · [Chapter index](README.md) · [Next chapter](5-threat-model-and-trust-boundaries.md)
