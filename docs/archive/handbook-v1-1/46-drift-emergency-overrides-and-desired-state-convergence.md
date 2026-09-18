# 46. Drift, emergency overrides and desired-state convergence

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<a id="__RefHeading___Toc13385_1645000677"></a>
<a id="sec_46"></a>

Reconciliation compares declared intent, approved plan, Terraform state, native platform state, effective routes/policy, inventory and evidence. Differences are classified by security and service impact. Do not blindly revert an emergency block merely because ordinary desired state still contains the old allow rule. An incident override is a controlled higher-priority object with scope, actor, reason, expiry/review and explicit release authority.

Security-significant drift changes the technical conformance condition and triggers a documented risk/containment decision. Historical authorization records are immutable evidence; the controller does not rewrite an official decision to pretend it was never issued. It can suspend readiness/new changes or exposure according to current authorization conditions. Emergency changes must be reconciled into the source or removed through an approved resolution.

Define a measurable detection objective by profile, inspection coverage, actions allowed automatically and cases requiring operator review. Detection queries use stable resource identities and avoid repeated destructive actions while the platform is converging. Drift on an unused optional feature and drift enabling public exposure are not equal priority. The evidence record retains before/after states and the decision trail.

<a id="req_DRIFT_001"></a>

DRIFT-001  Security-significant drift SHALL generate an actionable event and update technical conformance/readiness conditions until resolved or accepted; formal authorization records SHALL remain separately attributable and immutable.

Operations/SRE  \|  Verify: [CT-014](73-appendix-d-conformance-test-catalogue.md#test_CT_014), [CT-049](73-appendix-d-conformance-test-catalogue.md#test_CT_049), [CT-057](73-appendix-d-conformance-test-catalogue.md#test_CT_057)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00) / [S05](77-appendix-h-primary-sources-and-implementation-references.md#S05)  \|  revised-v1.0

<a id="req_DRIFT_002"></a>

DRIFT-002  Emergency changes SHALL be reconciled back into the source of truth after the incident or maintenance action.

Operations/SRE  \|  Verify: [CT-014](73-appendix-d-conformance-test-catalogue.md#test_CT_014), [CT-057](73-appendix-d-conformance-test-catalogue.md#test_CT_057)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_DRIFT_003"></a>

DRIFT-003  Incident containment overrides SHALL take precedence over ordinary reconciliation until explicitly released or handled by their approved expiry policy; automated repair SHALL NOT silently undo containment.

Incident response  \|  Verify: [CT-057](73-appendix-d-conformance-test-catalogue.md#test_CT_057), [CT-058](73-appendix-d-conformance-test-catalogue.md#test_CT_058), [CT-066](73-appendix-d-conformance-test-catalogue.md#test_CT_066)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  new-v1.1

[Previous chapter](45-secrets-and-automation-credentials.md) · [Chapter index](README.md) · [Next chapter](52-part-vi-assurance-and-operations.md)
