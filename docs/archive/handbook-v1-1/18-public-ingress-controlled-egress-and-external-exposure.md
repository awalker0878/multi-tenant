# 18. Public ingress, controlled egress and external exposure

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<a id="__RefHeading___Toc13323_1645000677"></a>
<a id="sec_18"></a>

## Public ingress

Public exposure is requested as a service outcome. The Exposure identifies owner, external domain, public service identity, protocol, TLS/certificate/DNS dependencies, PAZ ingress function, backend FlowIntent, telemetry and lifecycle. The internal domain is not attached directly to a public network. Ingress qualification covers load balancing, reverse proxy/API mediation, denial-of-service handling, backend identity and required application-layer inspection.

Where TLS terminates at ingress, re-encryption and backend certificate validation follow the selected profile. TLS passthrough is an explicit alternative with documented inspection limits. Preserve trustworthy client attribution: only approved proxies may supply client-identity headers; externally supplied headers cannot override the trusted identity chain. Public DNS and certificates are withdrawn or transferred in a controlled order during retirement.

## Internet egress and other external connections

No WSD receives Internet reachability by default. An EgressProfile identifies allowed destination/service scope, DNS behavior, proxy/NAT use, logging, identity attribution and revocation. A NAT gateway changes addressing; it is not a substitute for security policy. FQDN-based policy requires a defined resolver, refresh behavior and handling of shared/CDN addresses. Raw IP exceptions are scoped and reviewed.

Partner, enterprise and interconnect exposure uses the same lifecycle but different trust and agreement metadata. Translation for overlapping addresses is limited to approved endpoints and records both address identities. Existing-session behavior on policy revocation is explicit: terminate or drain within an approved bound, never leave an indefinite hidden permission.

<a id="req_ING_001"></a>

ING-001  A workload SHALL NOT obtain direct public ingress by attaching its internal Security Domain directly to a public network.

Security-edge operations  \|  Verify: [CT-006](73-appendix-d-conformance-test-catalogue.md#test_CT_006), [CT-025](73-appendix-d-conformance-test-catalogue.md#test_CT_025)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_ING_002"></a>

ING-002  Public exposure SHALL be represented by an Exposure object with owner, protocol, endpoint, certificate/DNS dependencies, logging, security profile, and lifecycle state.

Service owner  \|  Verify: [CT-006](73-appendix-d-conformance-test-catalogue.md#test_CT_006), [CT-063](73-appendix-d-conformance-test-catalogue.md#test_CT_063)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_EGR_001"></a>

EGR-001  Internet egress SHALL be deny-by-default and enabled only through an approved egress profile.

Security-edge operations  \|  Verify: [CT-005](73-appendix-d-conformance-test-catalogue.md#test_CT_005), [CT-064](73-appendix-d-conformance-test-catalogue.md#test_CT_064)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_EGR_002"></a>

EGR-002  Egress telemetry SHALL permit attribution to the originating tenant/WSD and should preserve useful source identity where operationally feasible.

Security-edge operations  \|  Verify: [CT-010](73-appendix-d-conformance-test-catalogue.md#test_CT_010), [CT-064](73-appendix-d-conformance-test-catalogue.md#test_CT_064)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_EXP_001"></a>

EXP-001  Exposure SHALL remain disabled until current-generation boundary, certificate, backend, logging and authorization gates pass; exposure revocation SHALL enforce the approved existing-session policy.

Security-edge operations  \|  Verify: [CT-063](73-appendix-d-conformance-test-catalogue.md#test_CT_063), [CT-069](73-appendix-d-conformance-test-catalogue.md#test_CT_069), [CT-077](73-appendix-d-conformance-test-catalogue.md#test_CT_077)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  new-v1.1

[Previous chapter](17-shared-services-and-explicit-service-bindings.md) · [Chapter index](README.md) · [Next chapter](19-microsegmentation-labels-and-workload-attachment.md)
