# 29. Placement, data location and sovereign optionality

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK HB11:436 BEGIN -->

<a id="__RefHeading___Toc13347_1645000677"></a>
<a id="sec_29"></a>

<!-- SOURCE-BLOCK HB11:436 END -->

<!-- SOURCE-BLOCK HB11:437 BEGIN -->

Placement is a constraint solver over approved capabilities, security/assurance, location, capacity, lifecycle and service reliability. Consumers normally request outcomes and eligible policy profiles rather than a vendor. “auto” means select a qualified target, not choose any available capacity. The decision records candidates, rejected constraints and the selected profile digest so a later assessor can reconstruct why the placement was allowed.

<!-- SOURCE-BLOCK HB11:437 END -->

<!-- SOURCE-BLOCK HB11:438 BEGIN -->

Model location/control constraints separately for primary data, replicas, backups, logs, diagnostic exports, control planes, administrators, support personnel and keys. Residency answers where data is stored; it does not alone answer jurisdiction, legal compulsion, administrative control or exit capability. The responsible legal/privacy/security authority determines those obligations. The controller enforces the resulting approved PlacementProfile rather than making legal conclusions.

<!-- SOURCE-BLOCK HB11:438 END -->

<!-- SOURCE-BLOCK HB11:439 BEGIN -->

Sovereign optionality is supported through usable exports, independently held documentation/keys where appropriate, replaceable identity integrations and tested service contracts. Record dependencies that constrain exit: proprietary snapshots, virtual devices, databases, licenses, agents, operating procedures and data-volume transfer costs. A nominally open file format is not a successful exit until the target recovers the application and its security outcomes. \[[S00](77-appendix-h-primary-sources-and-implementation-references.md#S00), closing statement; [S28](77-appendix-h-primary-sources-and-implementation-references.md#S28)\]

<!-- SOURCE-BLOCK HB11:439 END -->

<!-- SOURCE-BLOCK HB11:440 BEGIN -->

<a id="req_PLACE_001"></a>

PLACE-001  Placement SHALL satisfy all mandatory security, assurance, location, lifecycle, capacity and recovery constraints using a current qualified platform profile; unresolved or conflicting constraints SHALL reject the request.

<!-- SOURCE-BLOCK HB11:440 END -->

<!-- SOURCE-BLOCK HB11:441 BEGIN -->

Automation platform  \|  Verify: [CT-018](73-appendix-d-conformance-test-catalogue.md#test_CT_018), [CT-035](73-appendix-d-conformance-test-catalogue.md#test_CT_035), [CT-056](73-appendix-d-conformance-test-catalogue.md#test_CT_056), [CT-061](73-appendix-d-conformance-test-catalogue.md#test_CT_061)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  new-v1.1

<!-- SOURCE-BLOCK HB11:441 END -->

<!-- SOURCE-BLOCK HB11:442 BEGIN -->

<a id="req_PLACE_002"></a>

PLACE-002  Data, backup, telemetry, diagnostic, control-plane, administrative-access and key locations/control constraints SHALL be represented separately and enforced through approved profiles and agreements.

<!-- SOURCE-BLOCK HB11:442 END -->

<!-- SOURCE-BLOCK HB11:443 BEGIN -->

Service owner  \|  Verify: [CT-061](73-appendix-d-conformance-test-catalogue.md#test_CT_061), [CT-079](73-appendix-d-conformance-test-catalogue.md#test_CT_079)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  new-v1.1

<!-- SOURCE-BLOCK HB11:443 END -->

<!-- SOURCE-BLOCK HB11:444 BEGIN -->

<a id="req_PLACE_003"></a>

PLACE-003  Each portable service class SHALL have a documented exit path, declared proprietary dependencies and representative export/recovery evidence; residency or format support alone SHALL NOT be presented as portability or sovereignty proof.

<!-- SOURCE-BLOCK HB11:444 END -->

<!-- SOURCE-BLOCK HB11:445 BEGIN -->

Architecture authority  \|  Verify: [CT-060](73-appendix-d-conformance-test-catalogue.md#test_CT_060), [CT-073](73-appendix-d-conformance-test-catalogue.md#test_CT_073)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  new-v1.1

<!-- SOURCE-BLOCK HB11:445 END -->

[Previous chapter](28-availability-and-recovery-service-profiles.md) · [Chapter index](README.md) · [Next chapter](30-service-catalogue-quotas-and-capacity-on-demand.md)
