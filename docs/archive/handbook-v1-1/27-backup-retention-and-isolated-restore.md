# 27. Backup, retention and isolated restore

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK HB11:415 BEGIN -->

<a id="__RefHeading___Toc13343_1645000677"></a>
<a id="sec_27"></a>

<!-- SOURCE-BLOCK HB11:415 END -->

<!-- SOURCE-BLOCK HB11:416 BEGIN -->

Backup is a service, not a routing-domain name. Separate its data endpoints from management and repository administration. A BackupPolicy specifies protected objects, application consistency, schedule, retention/hold, independent copies, immutability where required, encryption/key custody, approved locations, recovery access and restore verification. A successful backup job does not prove recovery; acceptance is based on a verified restore of useful data and application state.

<!-- SOURCE-BLOCK HB11:416 END -->

<!-- SOURCE-BLOCK HB11:417 BEGIN -->

At least one recovery copy for a protected production service should be protected from routine production administrator credentials according to the selected recovery policy. Immutability settings and deletion authority are tested, not assumed from a marketing label. Protect the catalogue, configuration and key dependencies needed to locate and decrypt a copy. Retention changes are security-sensitive and cannot be made by a compromised workload identity.

<!-- SOURCE-BLOCK HB11:417 END -->

<!-- SOURCE-BLOCK HB11:418 BEGIN -->

Restore into an isolated recovery Security Domain with default-deny connectivity. Validate integrity and consistency markers, malware/risk posture, identity and secrets, required application services and recovery timing. Reconnection to production is a separate authorized transition. A restored image does not inherit old standing privileged sessions. For database/file services, record whether consistency is crash-consistent, application-consistent or transaction-point recovery; do not interchange those claims.

<!-- SOURCE-BLOCK HB11:418 END -->

<!-- SOURCE-BLOCK HB11:419 BEGIN -->

Retirement preserves required held/retained copies with accountable owners, keys and disposal dates. A production WSD may be retired while retention obligations remain under a retained-data record. Final deletion evidence identifies every known remaining copy and its authority. The service owner selects business recovery requirements; backup operations proves the selected mechanism and reports missed objectives.

<!-- SOURCE-BLOCK HB11:419 END -->

<!-- SOURCE-BLOCK HB11:420 BEGIN -->

<a id="req_BKP_001"></a>

BKP-001  Backup consumers SHALL NOT receive connectivity to backup management interfaces merely because they consume backup service.

<!-- SOURCE-BLOCK HB11:420 END -->

<!-- SOURCE-BLOCK HB11:421 BEGIN -->

Backup operations  \|  Verify: [CT-004](73-appendix-d-conformance-test-catalogue.md#test_CT_004), [CT-051](73-appendix-d-conformance-test-catalogue.md#test_CT_051)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<!-- SOURCE-BLOCK HB11:421 END -->

<!-- SOURCE-BLOCK HB11:422 BEGIN -->

<a id="req_BKP_002"></a>

BKP-002  Restore workflows SHALL enforce the same tenant, security-zone, identity, and evidence controls as backup ingestion.

<!-- SOURCE-BLOCK HB11:422 END -->

<!-- SOURCE-BLOCK HB11:423 BEGIN -->

Backup operations  \|  Verify: [CT-052](73-appendix-d-conformance-test-catalogue.md#test_CT_052), [CT-054](73-appendix-d-conformance-test-catalogue.md#test_CT_054)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<!-- SOURCE-BLOCK HB11:423 END -->

<!-- SOURCE-BLOCK HB11:424 BEGIN -->

<a id="req_BKP_003"></a>

BKP-003  Every protected production WSD SHALL have a BackupPolicy with consistency, retention, location, key and protected-copy requirements; successful isolated restore SHALL be demonstrated at the policy cadence.

<!-- SOURCE-BLOCK HB11:424 END -->

<!-- SOURCE-BLOCK HB11:425 BEGIN -->

Backup operations  \|  Verify: [CT-051](73-appendix-d-conformance-test-catalogue.md#test_CT_051), [CT-052](73-appendix-d-conformance-test-catalogue.md#test_CT_052), [CT-053](73-appendix-d-conformance-test-catalogue.md#test_CT_053)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  new-v1.1

<!-- SOURCE-BLOCK HB11:425 END -->

<!-- SOURCE-BLOCK HB11:426 BEGIN -->

<a id="req_BKP_004"></a>

BKP-004  Production credentials SHALL NOT be able to destroy or reduce the protection of recovery copies designated independent/immutable; retained copies SHALL keep the keys and catalogue required for authorized recovery.

<!-- SOURCE-BLOCK HB11:426 END -->

<!-- SOURCE-BLOCK HB11:427 BEGIN -->

Backup operations  \|  Verify: [CT-038](73-appendix-d-conformance-test-catalogue.md#test_CT_038), [CT-051](73-appendix-d-conformance-test-catalogue.md#test_CT_051), [CT-053](73-appendix-d-conformance-test-catalogue.md#test_CT_053)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  new-v1.1

<!-- SOURCE-BLOCK HB11:427 END -->

[Previous chapter](26-images-configuration-baselines-and-endpoint-protection.md) · [Chapter index](README.md) · [Next chapter](28-availability-and-recovery-service-profiles.md)
