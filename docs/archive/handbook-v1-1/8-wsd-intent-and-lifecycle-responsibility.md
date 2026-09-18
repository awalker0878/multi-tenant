# 8. WSD intent and lifecycle responsibility

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK HB11:193 BEGIN -->

<a id="__RefHeading___Toc13303_1645000677"></a>
<a id="sec_8"></a>

<!-- SOURCE-BLOCK HB11:193 END -->

<!-- SOURCE-BLOCK HB11:194 BEGIN -->

A WSD captures a workload or bounded workload set with one accountable service owner and an explicit security and recovery context. It names required zones, networks, flow intentions, service bindings, external exposure, storage/compute profiles and evidence requirements. It is the unit for admission, readiness, incident containment, migration and retirement, not necessarily a single Terraform state or one VPC.

<!-- SOURCE-BLOCK HB11:194 END -->

<!-- SOURCE-BLOCK HB11:195 BEGIN -->

The owner is responsible for application requirements and data classification, while the provider realizes and verifies the infrastructure contract. Application operators need to declare dynamic dependencies, scheduled jobs, partner services, administrative channels and recovery behavior. Undocumented application dependencies are not resolved by opening a shared subnet. A request may be admitted only when its dependency graph is satisfiable on an eligible platform.

<!-- SOURCE-BLOCK HB11:195 END -->

<!-- SOURCE-BLOCK HB11:196 BEGIN -->

The WSD references rather than owns reusable Security Domains and provider profiles. Resource ownership records distinguish exclusively owned objects from borrowed services, attached domains and retained recovery copies. Destructive operations traverse that graph and do not remove resources with other active dependents. Logical identity survives an authorized site move or platform rebuild even when native VM, network, disk and address identifiers change.

<!-- SOURCE-BLOCK HB11:196 END -->

<!-- SOURCE-BLOCK HB11:197 BEGIN -->

<a id="req_WSD_001"></a>

WSD-001  Every managed workload SHALL belong to a WSD or an explicitly documented equivalent lifecycle object.

<!-- SOURCE-BLOCK HB11:197 END -->

<!-- SOURCE-BLOCK HB11:198 BEGIN -->

Service owner  \|  Verify: [CT-017](73-appendix-d-conformance-test-catalogue.md#test_CT_017), [CT-070](73-appendix-d-conformance-test-catalogue.md#test_CT_070)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<!-- SOURCE-BLOCK HB11:198 END -->

<!-- SOURCE-BLOCK HB11:199 BEGIN -->

<a id="req_WSD_002"></a>

WSD-002  The WSD SHALL contain security and connectivity intent; it SHALL NOT contain vendor-specific infrastructure identifiers in the consumer contract.

<!-- SOURCE-BLOCK HB11:199 END -->

<!-- SOURCE-BLOCK HB11:200 BEGIN -->

Automation platform  \|  Verify: [CT-016](73-appendix-d-conformance-test-catalogue.md#test_CT_016), [CT-017](73-appendix-d-conformance-test-catalogue.md#test_CT_017)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<!-- SOURCE-BLOCK HB11:200 END -->

<!-- SOURCE-BLOCK HB11:201 BEGIN -->

<a id="req_WSD_003"></a>

WSD-003  A WSD SHALL declare compute, storage, identity, backup, recovery, exposure and evidence dependencies in addition to network intent; unresolved mandatory dependencies SHALL block Service Ready.

<!-- SOURCE-BLOCK HB11:201 END -->

<!-- SOURCE-BLOCK HB11:202 BEGIN -->

Service owner  \|  Verify: [CT-062](73-appendix-d-conformance-test-catalogue.md#test_CT_062), [CT-069](73-appendix-d-conformance-test-catalogue.md#test_CT_069)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  new-v1.1

<!-- SOURCE-BLOCK HB11:202 END -->

[Previous chapter](7-tenant-namespace-entitlements-and-ownership.md) · [Chapter index](README.md) · [Next chapter](9-security-domains-and-site-platform-instances.md)
