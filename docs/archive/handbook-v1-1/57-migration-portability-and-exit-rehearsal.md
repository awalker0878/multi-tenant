# 57. Migration, portability and exit rehearsal

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK HB11:749 BEGIN -->

<a id="__RefHeading___Toc13409_1645000677"></a>
<a id="sec_57"></a>

<!-- SOURCE-BLOCK HB11:749 END -->

<!-- SOURCE-BLOCK HB11:750 BEGIN -->

A MigrationConnection expresses a bounded transition between approved source and target domains. It includes data classification, source/destination authority, service/protocol, bandwidth, window/expiry, migration owner, consistency method, rollback or recovery plan, telemetry and teardown. A permanent migration/transit network is not the default. Do not use transition pressure to bypass ZIP controls or broaden shared-service access.

<!-- SOURCE-BLOCK HB11:750 END -->

<!-- SOURCE-BLOCK HB11:751 BEGIN -->

Recreate the same WSD semantics at the target with newly qualified platform-specific instances. Validate CPU/guest compatibility, drivers, boot mode, image/container formats, storage/application consistency, identity, keys, certificates, DNS, monitoring, backup and policy. Exportable disks alone do not make an application portable. Live migration between unrelated hypervisors is not promised; conversion, backup/restore or application-level transfer may be required.

<!-- SOURCE-BLOCK HB11:751 END -->

<!-- SOURCE-BLOCK HB11:752 BEGIN -->

A cutover plan chooses a final consistency point, fences old writers, confirms the target data state, tests permitted and forbidden paths, moves DNS/ingress through approved steps and observes the service before declaring success. A rollback may require reverse synchronization rather than simply starting the old VM. Retain both environments only within an approved time/cost/security window; remove transition connectivity and obsolete copies according to retention policy.

<!-- SOURCE-BLOCK HB11:752 END -->

<!-- SOURCE-BLOCK HB11:753 BEGIN -->

Run periodic exit rehearsals using representative workloads on a second qualified platform. Measure elapsed effort, data transfer, downtime, policy equivalence, dependency changes, egress/copy costs and operational skills. Record non-portable extensions explicitly and maintain a viable exit plan for them. Portability is an evidenced service outcome, not a commitment that every implementation has identical native capabilities.

<!-- SOURCE-BLOCK HB11:753 END -->

<!-- SOURCE-BLOCK HB11:754 BEGIN -->

<a id="req_MIG_001"></a>

MIG-001  Migration connectivity SHALL be time-bound unless explicitly converted to an approved steady-state connection.

<!-- SOURCE-BLOCK HB11:754 END -->

<!-- SOURCE-BLOCK HB11:755 BEGIN -->

Migration owner  \|  Verify: [CT-058](73-appendix-d-conformance-test-catalogue.md#test_CT_058), [CT-060](73-appendix-d-conformance-test-catalogue.md#test_CT_060), [CT-076](73-appendix-d-conformance-test-catalogue.md#test_CT_076)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<!-- SOURCE-BLOCK HB11:755 END -->

<!-- SOURCE-BLOCK HB11:756 BEGIN -->

<a id="req_MIG_002"></a>

MIG-002  Migration flows SHALL traverse an approved security edge when they cross security-domain boundaries.

<!-- SOURCE-BLOCK HB11:756 END -->

<!-- SOURCE-BLOCK HB11:757 BEGIN -->

Migration owner  \|  Verify: [CT-003](73-appendix-d-conformance-test-catalogue.md#test_CT_003), [CT-060](73-appendix-d-conformance-test-catalogue.md#test_CT_060)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<!-- SOURCE-BLOCK HB11:757 END -->

<!-- SOURCE-BLOCK HB11:758 BEGIN -->

<a id="req_MIG_003"></a>

MIG-003  Migration and exit rehearsals SHALL validate data/application consistency, identity/key dependencies, equivalent security outcomes, fencing/cutover, rollback feasibility and complete transition teardown.

<!-- SOURCE-BLOCK HB11:758 END -->

<!-- SOURCE-BLOCK HB11:759 BEGIN -->

Migration owner  \|  Verify: [CT-054](73-appendix-d-conformance-test-catalogue.md#test_CT_054), [CT-060](73-appendix-d-conformance-test-catalogue.md#test_CT_060), [CT-073](73-appendix-d-conformance-test-catalogue.md#test_CT_073), [CT-078](73-appendix-d-conformance-test-catalogue.md#test_CT_078)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  new-v1.1

<!-- SOURCE-BLOCK HB11:759 END -->

<!-- SOURCE-BLOCK HB11:760 BEGIN -->

<!-- SOURCE-BLOCK HB11:760 END -->

[Previous chapter](56-lifecycle-retirement-and-secure-disposal.md) · [Chapter index](README.md) · [Next chapter](64-part-vii-governance-and-delivery.md)
