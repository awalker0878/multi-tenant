# 30. Service catalogue, quotas and capacity on demand

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK HB11:446 BEGIN -->

<a id="__RefHeading___Toc13349_1645000677"></a>
<a id="sec_30"></a>

<!-- SOURCE-BLOCK HB11:446 END -->

<!-- SOURCE-BLOCK HB11:447 BEGIN -->

The provider offers capacity through reusable service classes, not project-specific hardware configurations. Separate entitlement, reservation and measured consumption. A tenant quota limits requests; a committed capacity reservation protects a promised resource; current utilization measures actual use. None is interchangeable with procured or installed inventory. Admission checks both tenant limits and the provider’s failure-headroom budget.

<!-- SOURCE-BLOCK HB11:447 END -->

<!-- SOURCE-BLOCK HB11:448 BEGIN -->

Capacity inventory tracks ordered, received, staged, commissioned, available, reserved, consumed and retiring resources. Each state has an owner, age, support expiry and reason. Report unused procured capacity and stranded capacity caused by incompatible profiles, missing staff/attachments or delayed commissioning. Expansion is a foundation lifecycle with its own approval and qualification, so routine WSD requests do not carry hardware procurement steps.

<!-- SOURCE-BLOCK HB11:448 END -->

<!-- SOURCE-BLOCK HB11:449 BEGIN -->

Cost/showback includes compute, storage performance/capacity, backup retention, edge/inspection, external data movement and dedicated isolation where those materially affect service cost. Use unit rates and measurement rules with effective dates; do not promise savings without measured baselines. Tenant-facing limits, service SLOs, supported sizes and rejection reasons are documented. A constrained site must reject or queue safely rather than borrow security-reserved capacity.

<!-- SOURCE-BLOCK HB11:449 END -->

<!-- SOURCE-BLOCK HB11:450 BEGIN -->

<a id="req_SVCM_001"></a>

SVCM-001  The service catalogue SHALL publish entitlements, hard quotas, reservation semantics, availability/recovery targets, supported capabilities and lifecycle obligations with stable service identifiers.

<!-- SOURCE-BLOCK HB11:450 END -->

<!-- SOURCE-BLOCK HB11:451 BEGIN -->

Service owner  \|  Verify: [CT-019](73-appendix-d-conformance-test-catalogue.md#test_CT_019), [CT-056](73-appendix-d-conformance-test-catalogue.md#test_CT_056), [CT-062](73-appendix-d-conformance-test-catalogue.md#test_CT_062)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  new-v1.1

<!-- SOURCE-BLOCK HB11:451 END -->

<!-- SOURCE-BLOCK HB11:452 BEGIN -->

<a id="req_SVCM_002"></a>

SVCM-002  Capacity inventory SHALL reconcile procured, staged, commissioned, available, reserved and consumed resources and SHALL report unused/stranded capacity, ownership and support-life exposure.

<!-- SOURCE-BLOCK HB11:452 END -->

<!-- SOURCE-BLOCK HB11:453 BEGIN -->

Capacity management  \|  Verify: [CT-074](73-appendix-d-conformance-test-catalogue.md#test_CT_074)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  new-v1.1

<!-- SOURCE-BLOCK HB11:453 END -->

[Previous chapter](29-placement-data-location-and-sovereign-optionality.md) · [Chapter index](README.md) · [Next chapter](31-application-responsibilities-and-end-to-end-service-readiness.md)
