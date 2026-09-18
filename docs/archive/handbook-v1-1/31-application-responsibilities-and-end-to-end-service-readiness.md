# 31. Application responsibilities and end-to-end service readiness

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<a id="__RefHeading___Toc13351_1645000677"></a>
<a id="sec_31"></a>

The infrastructure provider supplies the declared security and hosting service; the workload owner remains accountable for application behavior, business authorization, data categorization and application recovery requirements. Shared responsibility must identify who patches the guest, manages application secrets, configures database permissions, approves public exposure and validates restored business data. A managed service can transfer specific operational tasks, but not by leaving the owner undefined.

The onboarding record enumerates application dependencies and validates that declared flows are sufficient. Use functional synthetic checks in addition to reachability. Where a service must speak to another system in a different zone, require both application authorization and the infrastructure boundary approval. Infrastructure evidence cannot prove that an application correctly implements privacy, business rules or authorization for individual records.

A service is ready only when the current desired generation has valid profile resolution, eligible placement, realized infrastructure, passed mandatory tests, protected evidence, inventory ownership and the required authorization decision. Application acceptance is a separately attributable condition. A test endpoint used only to prove the substrate is not evidence that a production application has been validated.

<a id="req_RESP_001"></a>

RESP-001  Every applicable infrastructure/application control and recovery dependency SHALL have a provider, tenant or shared responsibility assignment and evidence owner; unresolved mandatory responsibilities SHALL block Service Ready.

Service owner  \|  Verify: [CT-062](73-appendix-d-conformance-test-catalogue.md#test_CT_062), [CT-069](73-appendix-d-conformance-test-catalogue.md#test_CT_069)  \|  Basis: [S05](77-appendix-h-primary-sources-and-implementation-references.md#S05) / [S08](77-appendix-h-primary-sources-and-implementation-references.md#S08)  \|  new-v1.1

[Previous chapter](30-service-catalogue-quotas-and-capacity-on-demand.md) · [Chapter index](README.md) · [Next chapter](35-part-iv-infrastructure-and-platform-realization.md)
