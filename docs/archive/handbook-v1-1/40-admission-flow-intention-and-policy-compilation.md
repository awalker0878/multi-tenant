# 40. Admission, Flow Intention and policy compilation

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK HB11:558 BEGIN -->

<a id="__RefHeading___Toc13373_1645000677"></a>
<a id="sec_40"></a>

<!-- SOURCE-BLOCK HB11:558 END -->

<!-- SOURCE-BLOCK HB11:559 BEGIN -->

Admission evaluates portable intent first, then checks provider plans as a second layer. A Flow Intention identifies source and destination workload/service identity, a versioned FlowProfile, permitted initiation direction, purpose, owner, lifetime and logging requirement. The profile resolves protocol/ports, statefulness, required TLS/application identity and optional L7/FQDN controls. A flow request is not a raw firewall rule or a substitute for application authorization.

<!-- SOURCE-BLOCK HB11:559 END -->

<!-- SOURCE-BLOCK HB11:560 BEGIN -->

The compiler resolves labels to authoritative identities and networks; classifies same-domain, cross-domain, management or external traffic; validates the zone graph; selects an eligible enforcement pattern; computes required routes and service attachments; and emits policies with a stable intent-to-rule mapping. Mandatory provider denies and incident containment dominate ordinary tenant allow policy. Rule changes include established-session handling and membership convergence.

<!-- SOURCE-BLOCK HB11:560 END -->

<!-- SOURCE-BLOCK HB11:561 BEGIN -->


<a id="source-table-561"></a>

| Admission input | Reject when |
| --- | --- |
| Owner / tenant / entitlement | Identity cannot act for the referenced tenant or exceeds service scope |
| Profiles / category | Reference is unknown, mutable, expired, ineligible or contradicts a mandatory requirement |
| Zone / external graph | Direct public/internal attachment, unapproved partner relation or missing ZIP authority |
| Flow / service binding | Unknown identity/service, missing direction, unsupported security function or hidden broad scope |
| Placement / capacity | No qualified tuple, insufficient failure headroom or prohibited co-residency/location |
| Plan / approval | Unapproved topology, secret exposure, stale state/policy generation or expired approval |

<!-- SOURCE-BLOCK HB11:561 END -->

<!-- SOURCE-BLOCK HB11:562 BEGIN -->

The control plane records both the admitted request and normalized intent. It should explain denial in terms of consumer outcomes rather than exposing internal route targets. No tenant-created exception object grants a waiver: the exception must resolve to an approved, scoped and current authority record. An admission-engine outage prevents new security-significant changes while preserving the existing verified data-plane policy.

<!-- SOURCE-BLOCK HB11:562 END -->

<!-- SOURCE-BLOCK HB11:563 BEGIN -->

<a id="req_POL_001"></a>

POL-001  Admission policy SHALL be provider independent wherever the rule expresses an architectural invariant.

<!-- SOURCE-BLOCK HB11:563 END -->

<!-- SOURCE-BLOCK HB11:564 BEGIN -->

Automation platform  \|  Verify: [CT-017](73-appendix-d-conformance-test-catalogue.md#test_CT_017), [CT-025](73-appendix-d-conformance-test-catalogue.md#test_CT_025), [CT-066](73-appendix-d-conformance-test-catalogue.md#test_CT_066)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<!-- SOURCE-BLOCK HB11:564 END -->

<!-- SOURCE-BLOCK HB11:565 BEGIN -->

<a id="req_POL_002"></a>

POL-002  Provider-specific plan checks SHOULD validate that the adapter compiled the intent into the expected native constructs.

<!-- SOURCE-BLOCK HB11:565 END -->

<!-- SOURCE-BLOCK HB11:566 BEGIN -->

Automation platform  \|  Verify: [CT-009](73-appendix-d-conformance-test-catalogue.md#test_CT_009), [CT-048](73-appendix-d-conformance-test-catalogue.md#test_CT_048), [CT-066](73-appendix-d-conformance-test-catalogue.md#test_CT_066)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<!-- SOURCE-BLOCK HB11:566 END -->

<!-- SOURCE-BLOCK HB11:567 BEGIN -->

<a id="req_FLOW_001"></a>

FLOW-001  Flow Intentions SHALL resolve explicit identities, service/profile version, initiation direction, lifetime, purpose and logging; compilation SHALL preserve mandatory policy precedence and enforce approved session-revocation behavior.

<!-- SOURCE-BLOCK HB11:567 END -->

<!-- SOURCE-BLOCK HB11:568 BEGIN -->

Security-edge operations  \|  Verify: [CT-007](73-appendix-d-conformance-test-catalogue.md#test_CT_007), [CT-020](73-appendix-d-conformance-test-catalogue.md#test_CT_020), [CT-066](73-appendix-d-conformance-test-catalogue.md#test_CT_066), [CT-077](73-appendix-d-conformance-test-catalogue.md#test_CT_077)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  new-v1.1

<!-- SOURCE-BLOCK HB11:568 END -->

[Previous chapter](39-canonical-api-object-ownership-and-status.md) · [Chapter index](README.md) · [Next chapter](41-zero-touch-provisioning-and-reconciliation-workflow.md)
