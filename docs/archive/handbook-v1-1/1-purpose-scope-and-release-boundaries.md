# 1. Purpose, scope and release boundaries

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<a id="__RefHeading___Toc13287_1645000677"></a>
<a id="sec_1"></a>

This handbook specifies a reusable, secure-by-default hosting service across Nutanix, VMware/NSX, OpenStack and separately qualified physical or container platforms. It preserves the uploaded baseline’s Tenant Namespace, Workload Security Domain (WSD), Security Domain Instance, Flow Intention, Service Binding, Exposure and ZIP concepts while adding the hosting and operating controls needed around them. It deliberately uses neutral labels rather than inherited departmental or site-specific VRF names. \[[S00](77-appendix-h-primary-sources-and-implementation-references.md#S00), sections 1 and 4\]

Version 1.1 is a completed reference-architecture document baseline for review and implementation. It is not a claim that a live environment has passed conformance, that a provider combination is certified, or that an authorizing official has approved a system. The companion package contains validated document/contract artefacts and conformance specifications; it is not a deployed service controller or a set of production platform adapters.


<a id="source-table-111"></a>

| Included | Implementation-specific deliverables still required |
| --- | --- |
| Security, network, compute, storage, identity, cryptography, reliability, lifecycle and evidence semantics | Site inventory, physical design, exact product releases, licenses, supported hardware and measured scale limits |
| Portable contract and authority boundaries; three target platform profiles | Qualified native adapters, deployment credentials, operational ownership and approved platform capability records |
| Normative requirements, control-family crosswalk, test procedures and audit closure | System categorization, tailored control selection, threat/risk analysis, independent assessment and formal authorization |

The initial service envelope is Unclassified, Protected A and Protected B information with separately assessed integrity and availability impact. Protected C and classified operation require an additional authorized architecture and are not silently enabled by selecting “dedicated” or HRZ. Application business logic, detailed rack cabling and commercial product selection remain outside this reference baseline, but their interfaces and acceptance evidence are specified. \[[S02](77-appendix-h-primary-sources-and-implementation-references.md#S02), Overview\]

<a id="req_ARCH_001"></a>

ARCH-001  The hosting contract SHALL be vendor neutral and SHALL NOT require consumers to specify vendor-specific identifiers or topology objects.

Architecture authority  \|  Verify: [CT-016](73-appendix-d-conformance-test-catalogue.md#test_CT_016), [CT-017](73-appendix-d-conformance-test-catalogue.md#test_CT_017)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_ARCH_002"></a>

ARCH-002  Routine tenant and workload lifecycle operations SHOULD NOT require changes to physical leaf or spine configuration.

Architecture authority  \|  Verify: [CT-071](73-appendix-d-conformance-test-catalogue.md#test_CT_071), [CT-072](73-appendix-d-conformance-test-catalogue.md#test_CT_072)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_ARCH_003"></a>

ARCH-003  All inter-zone paths SHALL be explicit and SHALL traverse the applicable ZIP/security edge.

Architecture authority  \|  Verify: [CT-003](73-appendix-d-conformance-test-catalogue.md#test_CT_003), [CT-025](73-appendix-d-conformance-test-catalogue.md#test_CT_025)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00) / [S01](77-appendix-h-primary-sources-and-implementation-references.md#S01) / [S02](77-appendix-h-primary-sources-and-implementation-references.md#S02)  \|  retained-v1.0

<a id="req_ARCH_004"></a>

ARCH-004  Management/OOB traffic SHALL be separated from tenant operational traffic and SHALL have independently controlled access paths.

Architecture authority  \|  Verify: [CT-004](73-appendix-d-conformance-test-catalogue.md#test_CT_004), [CT-026](73-appendix-d-conformance-test-catalogue.md#test_CT_026)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00) / [S01](77-appendix-h-primary-sources-and-implementation-references.md#S01) / [S02](77-appendix-h-primary-sources-and-implementation-references.md#S02)  \|  retained-v1.0

<a id="req_SCOPE_001"></a>

SCOPE-001  Every implementation SHALL publish its offered service classes, supported information categories, excluded capabilities and required qualification evidence before accepting a production request.

Architecture authority  \|  Verify: [CT-018](73-appendix-d-conformance-test-catalogue.md#test_CT_018), [CT-062](73-appendix-d-conformance-test-catalogue.md#test_CT_062)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  new-v1.1

[Previous chapter](01-part-i-foundations-and-governance-context.md) · [Chapter index](README.md) · [Next chapter](2-normative-language-invariants-and-authority.md)
