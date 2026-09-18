# 47. Assurance profiles and isolation decisions

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<a id="__RefHeading___Toc13389_1645000677"></a>
<a id="sec_47"></a>

Assurance Profiles are local realization policies, not official security categorization levels or a substitute for a system assurance determination. Standard, Enhanced and Dedicated select explicit separation and verification requirements. Their definitions must be versioned; a change to their meaning triggers re-evaluation of placements. All profiles retain tenant isolation, deny-by-default communication, independent management, attributable logging, protected credentials and tested recovery. \[[S03](77-appendix-h-primary-sources-and-implementation-references.md#S03); [S05](77-appendix-h-primary-sources-and-implementation-references.md#S05)\]


<a id="source-table-644"></a>

| Dimension | Standard | Enhanced | Dedicated |
| --- | --- | --- | --- |
| Tenant/domain sharing | Shared infrastructure; separate tenant authority and tested policy; domain sharing only within approved authority | Dedicated logical routing and edge policy contexts for the WSD; shared hardware only as approved | Named dedicated physical resources for the declared scope; no implicit sharing |
| Host co-residency | Zone-specific host pools by baseline; compatible tenants may share within that zone | Zone-specific pools; tenant/WSD dedicated placement where required by the profile | Dedicated host pool and explicit ancillary-service dependencies |
| Storage and copies | Access-controlled logical storage boundary, copy lineage and encryption | Dedicated logical pool/key scope where supported and required; constrained administrative sharing | Dedicated storage scope if selected; management/backup sharing separately decided |
| Management and edge | Isolated MZ, separate data/management contexts; qualified shared edge hardware | Dedicated logical edge context plus stronger change/inspection controls | Declared physical edge/management isolation scope; dependencies documented |
| Testing and recovery | Mandatory deployment subset; full qualification and scheduled recovery tests | Additional compromise, failure, privilege and shared-component tests | All required tests plus verification of physical dedication and independent recovery |
| Telemetry and review | Profile-defined event coverage, detection and retention objectives | Tighter locally approved detection/review objectives and additional sensors | Profile-defined objectives; physical dedication never replaces monitoring |

Dedicated is a vector, not a single checkbox: host, cluster, storage, edge, management, backup, key custody and site can each be shared or dedicated. Record which are actually dedicated. Dedicated hosts connected to a shared management or backup plane do not make the whole service physically independent. Any alternative to the zone-specific host-pool baseline needs explicit risk acceptance and evidence addressing the virtualization guidance; an assurance label alone is insufficient. \[[S03](77-appendix-h-primary-sources-and-implementation-references.md#S03)\]

The profile fixes mandatory test sets, evidence freshness, operator review, maximum exception age and recovery cadence. Numeric values in Appendix F are proposed engineering starting points, not statements of government policy or delivered service guarantees. A production profile cannot be Qualified while mandatory numeric parameters, owners or approval references are missing.

<a id="req_ASSUR_001"></a>

ASSUR-001  Assurance profile selection SHALL be based on system security requirements and risk analysis rather than tenant preference alone.

Security authority  \|  Verify: [CT-035](73-appendix-d-conformance-test-catalogue.md#test_CT_035), [CT-062](73-appendix-d-conformance-test-catalogue.md#test_CT_062)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00) / [S03](77-appendix-h-primary-sources-and-implementation-references.md#S03) / [S05](77-appendix-h-primary-sources-and-implementation-references.md#S05)  \|  retained-v1.0

<a id="req_ASSUR_002"></a>

ASSUR-002  Assurance profiles SHALL define explicit isolation for compute, storage, routing, edge, management, backup and keys, with measurable verification and exception rules; “dedicated” SHALL identify its actual resource scope.

Security authority  \|  Verify: [CT-018](73-appendix-d-conformance-test-catalogue.md#test_CT_018), [CT-035](73-appendix-d-conformance-test-catalogue.md#test_CT_035), [CT-037](73-appendix-d-conformance-test-catalogue.md#test_CT_037), [CT-062](73-appendix-d-conformance-test-catalogue.md#test_CT_062)  \|  Basis: [S03](77-appendix-h-primary-sources-and-implementation-references.md#S03) / [S05](77-appendix-h-primary-sources-and-implementation-references.md#S05)  \|  new-v1.1

<a id="req_ASSUR_003"></a>

ASSUR-003  A production profile SHALL have approved parameter values, owners, applicable test sets and evidence freshness limits; incomplete or expired profiles SHALL be ineligible for new production placement.

Security authority  \|  Verify: [CT-018](73-appendix-d-conformance-test-catalogue.md#test_CT_018), [CT-058](73-appendix-d-conformance-test-catalogue.md#test_CT_058), [CT-069](73-appendix-d-conformance-test-catalogue.md#test_CT_069)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  new-v1.1

[Previous chapter](52-part-vi-assurance-and-operations.md) · [Chapter index](README.md) · [Next chapter](48-conformance-framework-and-test-execution.md)
