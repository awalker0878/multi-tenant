# 12. MZ, OOB and privileged management access

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<a id="__RefHeading___Toc13311_1645000677"></a>
<a id="sec_12"></a>

MZ describes a security zone and its administration policy. OOB describes management transport that remains independent of the workload data path, preferably using dedicated interfaces and network equipment where supported. A physically separate cable alone does not supply privileged identity, hardened administration or log integrity. Conversely, a virtual management segment must not be called physically OOB when it shares the production switching/control dependency. \[[S01](77-appendix-h-primary-sources-and-implementation-references.md#S01), Annex E; [S02](77-appendix-h-primary-sources-and-implementation-references.md#S02), management-zone guidance\]

Use an isolated MZ approach as the baseline. Separate provider platform administration, security-edge administration, fabric administration and tenant guest/application administration by authority and controlled paths. Approved administrators work from hardened dedicated administrative endpoints with phishing-resistant MFA where the applicable GC configuration requirements apply. Remote access crosses an explicitly approved management-access boundary; it is not the public workload PAZ reused for convenience. \[[S02](77-appendix-h-primary-sources-and-implementation-references.md#S02); [S07](77-appendix-h-primary-sources-and-implementation-references.md#S07), section 4\]

Tenant users consume a service-catalogue/API endpoint with scoped credentials, not direct infrastructure administrative APIs. Backup, KMS, logging and identity data endpoints remain published services; their management interfaces belong to the management trust plane. Prevent credentials from higher-authority planes being used on lower-trust workload devices. Record support access, session expiry, device trust, bastion policy and any approved emergency access. Test recovery without the normal federation provider.

<a id="req_MGT_001"></a>

MGT-001  Tenant workload networks SHALL have no direct route to infrastructure management interfaces.

Management operations  \|  Verify: [CT-004](73-appendix-d-conformance-test-catalogue.md#test_CT_004), [CT-026](73-appendix-d-conformance-test-catalogue.md#test_CT_026)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_MGT_002"></a>

MGT-002  Administrative access SHALL originate from an authorized management access path and traverse management-specific security controls.

Management operations  \|  Verify: [CT-026](73-appendix-d-conformance-test-catalogue.md#test_CT_026), [CT-027](73-appendix-d-conformance-test-catalogue.md#test_CT_027)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_MGT_003"></a>

MGT-003  Automation identities used to manage tenant workloads SHALL be separated from identities able to modify the physical fabric, security edge, or management foundation.

Automation platform  \|  Verify: [CT-019](73-appendix-d-conformance-test-catalogue.md#test_CT_019), [CT-044](73-appendix-d-conformance-test-catalogue.md#test_CT_044)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_MGT_004"></a>

MGT-004  Break-glass access SHALL be separately controlled, strongly authenticated, logged, time-bounded where feasible, and periodically tested.

Management operations  \|  Verify: [CT-027](73-appendix-d-conformance-test-catalogue.md#test_CT_027), [CT-079](73-appendix-d-conformance-test-catalogue.md#test_CT_079)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_MGT_005"></a>

MGT-005  The implementation SHALL document independent MZ semantics, OOB transport dependencies, remote-management boundary and privileged identity controls; tenant-facing APIs SHALL NOT expose infrastructure administration.

Management operations  \|  Verify: [CT-004](73-appendix-d-conformance-test-catalogue.md#test_CT_004), [CT-026](73-appendix-d-conformance-test-catalogue.md#test_CT_026), [CT-055](73-appendix-d-conformance-test-catalogue.md#test_CT_055)  \|  Basis: [S01](77-appendix-h-primary-sources-and-implementation-references.md#S01) / [S02](77-appendix-h-primary-sources-and-implementation-references.md#S02) / [S07](77-appendix-h-primary-sources-and-implementation-references.md#S07)  \|  new-v1.1

[Previous chapter](11-zip-architecture-and-joint-boundary-authority.md) · [Chapter index](README.md) · [Next chapter](13-platform-overlays-and-enforcement-ownership.md)
