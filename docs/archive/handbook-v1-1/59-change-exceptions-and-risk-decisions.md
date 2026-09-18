# 59. Change, exceptions and risk decisions

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK HB11:771 BEGIN -->

<a id="__RefHeading___Toc13415_1645000677"></a>
<a id="sec_59"></a>

<!-- SOURCE-BLOCK HB11:771 END -->

<!-- SOURCE-BLOCK HB11:772 BEGIN -->

Classify changes by their effect, not by their Terraform file location. Workload scale within an approved envelope can be pre-authorized; inter-zone policy, public exposure, privileged roles, keys, routing authority, assurance or data location requires the corresponding elevated authority. Every production change binds current intent and approval to a specific immutable plan and target generation.

<!-- SOURCE-BLOCK HB11:772 END -->

<!-- SOURCE-BLOCK HB11:773 BEGIN -->

A SecurityException includes requirement IDs, exact scope, accountable risk owner, justification, compensating controls, approving authority, effective date, expiry/review, constraints and closure evidence. An exception does not grant rights to waive laws, external policy or an authorization condition beyond the approver’s remit. An architecture cannot silently “exception” away mandatory isolation and still claim the original assurance profile; change the offered scope or obtain a properly authorized alternative.

<!-- SOURCE-BLOCK HB11:773 END -->

<!-- SOURCE-BLOCK HB11:774 BEGIN -->


<a id="source-table-774"></a>

| State/event | Controller behavior |
| --- | --- |
| Proposed or rejected exception | No enforcement relaxation; record decision and rationale |
| Approved and effective | Apply only within its exact requirement/resource/time scope; show residual risk in evidence |
| Approaching expiry | Notify owner/authority; require renewal evidence or planned remediation |
| Expired or revoked | Mark affected conformance/readiness and block new reliance; execute pre-approved remediation/continuity action, not blind destruction |
| Closed | Verify compensating/temporary objects removed or incorporated into an approved baseline; retain history |

<!-- SOURCE-BLOCK HB11:774 END -->

<!-- SOURCE-BLOCK HB11:775 BEGIN -->

Emergency change and incident override are related but distinct. An urgent containment block can be authorized before the ordinary pipeline completes; it still needs actor, scope, time, incident reference and retrospective reconciliation. An exception permitting a risky path requires its own risk authority. A generic “emergency” label is not an unrestricted allow rule.

<!-- SOURCE-BLOCK HB11:775 END -->

<!-- SOURCE-BLOCK HB11:776 BEGIN -->

<a id="req_EXC_001"></a>

EXC-001  Every exception SHALL have an accountable risk owner and expiry or review date.

<!-- SOURCE-BLOCK HB11:776 END -->

<!-- SOURCE-BLOCK HB11:777 BEGIN -->

Risk owner  \|  Verify: [CT-058](73-appendix-d-conformance-test-catalogue.md#test_CT_058), [CT-062](73-appendix-d-conformance-test-catalogue.md#test_CT_062)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<!-- SOURCE-BLOCK HB11:777 END -->

<!-- SOURCE-BLOCK HB11:778 BEGIN -->

<a id="req_EXC_002"></a>

EXC-002  The control plane SHALL surface expired exceptions as non-compliant state rather than allowing them to become permanent undocumented architecture.

<!-- SOURCE-BLOCK HB11:778 END -->

<!-- SOURCE-BLOCK HB11:779 BEGIN -->

Risk owner  \|  Verify: [CT-058](73-appendix-d-conformance-test-catalogue.md#test_CT_058), [CT-069](73-appendix-d-conformance-test-catalogue.md#test_CT_069)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<!-- SOURCE-BLOCK HB11:779 END -->

<!-- SOURCE-BLOCK HB11:780 BEGIN -->

<a id="req_EXC_003"></a>

EXC-003  Exceptions SHALL bind requirement IDs, precise scope, effective/expiry times, compensating controls and authorized risk approval; expiry handling SHALL preserve evidence and follow a pre-approved secure continuity/remediation decision.

<!-- SOURCE-BLOCK HB11:780 END -->

<!-- SOURCE-BLOCK HB11:781 BEGIN -->

Risk owner  \|  Verify: [CT-017](73-appendix-d-conformance-test-catalogue.md#test_CT_017), [CT-058](73-appendix-d-conformance-test-catalogue.md#test_CT_058), [CT-069](73-appendix-d-conformance-test-catalogue.md#test_CT_069)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  new-v1.1

<!-- SOURCE-BLOCK HB11:781 END -->

[Previous chapter](58-operating-model-and-separation-of-duties.md) · [Chapter index](README.md) · [Next chapter](60-architecture-review-and-onboarding-gates.md)
