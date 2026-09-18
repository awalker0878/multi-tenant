# 49. Evidence, controls and authorization records

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK HB11:666 BEGIN -->

<a id="__RefHeading___Toc13393_1645000677"></a>
<a id="sec_49"></a>

<!-- SOURCE-BLOCK HB11:666 END -->

<!-- SOURCE-BLOCK HB11:667 BEGIN -->

An EvidenceRecord is a signed or equivalently tamper-evident manifest that binds requested intent, admission decisions, profiles, placement, IPAM leases, routes, boundary relationships, Terraform/module/provider/runner digests, realized resources, tests and exceptions. Store large logs/configurations separately with immutable identifiers and integrity digests. Grant assessors the necessary read scope without exposing other tenants or secret-bearing state. Evidence sensitivity can exceed the sensitivity of any single displayed field. \[[S05](77-appendix-h-primary-sources-and-implementation-references.md#S05); [S11](77-appendix-h-primary-sources-and-implementation-references.md#S11)\]

<!-- SOURCE-BLOCK HB11:667 END -->

<!-- SOURCE-BLOCK HB11:668 BEGIN -->

![A handbook requirement and source-edition mapping lead to an approved intent/profile, a realized object and a test result. Their signed artifact references form an evidence record. Technical conformance and Service Ready conditions are evaluated separately from an independently issued authorization decision. Exceptions and incident overrides remain visible in the chain.](../../assets/diagrams/45f5a64d0820a8d03f7f.png)

<!-- SOURCE-BLOCK HB11:668 END -->

<!-- SOURCE-BLOCK HB11:669 BEGIN -->

<a id="fig_evidence"></a>

Figure 5. An attributable chain from requirement to operational decision

<!-- SOURCE-BLOCK HB11:669 END -->

<!-- SOURCE-BLOCK HB11:670 BEGIN -->

Control results map a specific requirement and source edition/control selection to implementation owner, realized object, test execution and artifact. The family mappings in Appendix E are candidate selection aids. The adopting assessor must select actual ITSP.10.033 controls, enhancements and organization-defined parameters and decide inheritance from shared services. The package intentionally does not label a family-level mapping as a completed security assessment. \[[S05](77-appendix-h-primary-sources-and-implementation-references.md#S05)\]

<!-- SOURCE-BLOCK HB11:670 END -->

<!-- SOURCE-BLOCK HB11:671 BEGIN -->

Separate technicalConformance, serviceReadiness and authorizationDecisionRef. A technical failure may suspend service readiness or trigger an authorized containment action; it does not delete or rewrite the historical authorization decision. An AuthorizationDecision records the authorized scope, issued-by authority, date, validity/review conditions, residual risks and conditions of operation. Only the designated authority issues or modifies that decision. The controller evaluates whether current operation still satisfies its conditions.

<!-- SOURCE-BLOCK HB11:671 END -->

<!-- SOURCE-BLOCK HB11:672 BEGIN -->

Evidence includes a collection time, the target generation, profile/capability digests and expiry/freshness policy. A passing test against yesterday’s topology cannot automatically validate a changed route today. Archive retirement evidence and retained-data obligations using stable tombstone identifiers so a deleted workload remains auditable without retaining unrestricted live access.

<!-- SOURCE-BLOCK HB11:672 END -->

<!-- SOURCE-BLOCK HB11:673 BEGIN -->

<a id="req_EVID_001"></a>

EVID-001  The evidence record SHALL identify the source revision, policy version, provider/module versions, realized security relationships, test results, and active exceptions.

<!-- SOURCE-BLOCK HB11:673 END -->

<!-- SOURCE-BLOCK HB11:674 BEGIN -->

Assurance engineering  \|  Verify: [CT-049](73-appendix-d-conformance-test-catalogue.md#test_CT_049), [CT-069](73-appendix-d-conformance-test-catalogue.md#test_CT_069), [CT-075](73-appendix-d-conformance-test-catalogue.md#test_CT_075)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<!-- SOURCE-BLOCK HB11:674 END -->

<!-- SOURCE-BLOCK HB11:675 BEGIN -->

<a id="req_EVID_002"></a>

EVID-002  Evidence SHALL bind target generation, source/profile/capability/dependency digests, artifact integrity, collection time, test executions and active exceptions; freshness SHALL be evaluated after material changes.

<!-- SOURCE-BLOCK HB11:675 END -->

<!-- SOURCE-BLOCK HB11:676 BEGIN -->

Assurance engineering  \|  Verify: [CT-048](73-appendix-d-conformance-test-catalogue.md#test_CT_048), [CT-049](73-appendix-d-conformance-test-catalogue.md#test_CT_049), [CT-069](73-appendix-d-conformance-test-catalogue.md#test_CT_069)  \|  Basis: [S05](77-appendix-h-primary-sources-and-implementation-references.md#S05) / [S11](77-appendix-h-primary-sources-and-implementation-references.md#S11)  \|  new-v1.1

<!-- SOURCE-BLOCK HB11:676 END -->

<!-- SOURCE-BLOCK HB11:677 BEGIN -->

<a id="req_EVID_003"></a>

EVID-003  Formal authorization decisions SHALL be issued by the designated authority and retained separately from technical test status, with scope, validity and operating conditions that the controller can evaluate.

<!-- SOURCE-BLOCK HB11:677 END -->

<!-- SOURCE-BLOCK HB11:678 BEGIN -->

Security authority  \|  Verify: [CT-049](73-appendix-d-conformance-test-catalogue.md#test_CT_049), [CT-058](73-appendix-d-conformance-test-catalogue.md#test_CT_058), [CT-069](73-appendix-d-conformance-test-catalogue.md#test_CT_069)  \|  Basis: [S04](77-appendix-h-primary-sources-and-implementation-references.md#S04) / [S05](77-appendix-h-primary-sources-and-implementation-references.md#S05)  \|  new-v1.1

<!-- SOURCE-BLOCK HB11:678 END -->

[Previous chapter](48-conformance-framework-and-test-execution.md) · [Chapter index](README.md) · [Next chapter](50-logging-telemetry-and-time-integrity.md)
