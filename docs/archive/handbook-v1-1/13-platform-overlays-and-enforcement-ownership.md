# 13. Platform overlays and enforcement ownership

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK HB11:258 BEGIN -->

<a id="__RefHeading___Toc13313_1645000677"></a>
<a id="sec_13"></a>

<!-- SOURCE-BLOCK HB11:258 END -->

<!-- SOURCE-BLOCK HB11:259 BEGIN -->

The platform overlay normally owns high-cardinality tenant routing, networks and security identity. The underlay carries tunnel/transport reachability and precommissioned platform/edge attachments. This reduces routine switch churn without claiming that capacity growth, physical onboarding or a fabric-routed service class can never change the fabric. The service class declares which lifecycle path applies.

<!-- SOURCE-BLOCK HB11:259 END -->

<!-- SOURCE-BLOCK HB11:260 BEGIN -->

Inside one authorized Security Domain Instance, the platform may route natively, subject to mandatory microsegmentation and internal-boundary policy. Between independent security domains, even domains with the same zone class, the applicable ZIP/boundary service controls the path. The location of enforcement may be distributed, centralized or combined; the resulting reachability and authority are what qualification verifies.

<!-- SOURCE-BLOCK HB11:260 END -->

<!-- SOURCE-BLOCK HB11:261 BEGIN -->

The adapter inventory identifies every component capable of forwarding tenant traffic: host virtual switches, overlay gateways, external subnets, service appliances, load balancers, physical attachments and recovery links. Default platform behaviors are normalized before workload connection. A tenant must not create a second NIC, router, floating address, security group or network attachment that escapes the canonical policy.

<!-- SOURCE-BLOCK HB11:261 END -->

<!-- SOURCE-BLOCK HB11:262 BEGIN -->

<a id="req_OVL_001"></a>

OVL-001  A platform SHALL provide an isolated routing/policy mechanism capable of realizing the Security Domain semantics required by the applicable conformance profile.

<!-- SOURCE-BLOCK HB11:262 END -->

<!-- SOURCE-BLOCK HB11:263 BEGIN -->

Platform engineering  \|  Verify: [CT-016](73-appendix-d-conformance-test-catalogue.md#test_CT_016), [CT-018](73-appendix-d-conformance-test-catalogue.md#test_CT_018), [CT-080](73-appendix-d-conformance-test-catalogue.md#test_CT_080)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<!-- SOURCE-BLOCK HB11:263 END -->

<!-- SOURCE-BLOCK HB11:264 BEGIN -->

<a id="req_OVL_002"></a>

OVL-002  Native routing MAY be used within one authorized Security Domain Instance; communication between independent security domains SHALL follow the approved boundary/ZIP realization and its policy.

<!-- SOURCE-BLOCK HB11:264 END -->

<!-- SOURCE-BLOCK HB11:265 BEGIN -->

Platform engineering  \|  Verify: [CT-003](73-appendix-d-conformance-test-catalogue.md#test_CT_003), [CT-021](73-appendix-d-conformance-test-catalogue.md#test_CT_021), [CT-023](73-appendix-d-conformance-test-catalogue.md#test_CT_023)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00) / [S01](77-appendix-h-primary-sources-and-implementation-references.md#S01) / [S02](77-appendix-h-primary-sources-and-implementation-references.md#S02)  \|  revised-v1.0

<!-- SOURCE-BLOCK HB11:265 END -->

<!-- SOURCE-BLOCK HB11:266 BEGIN -->

<a id="req_OVL_003"></a>

OVL-003  Before a workload is attached, the adapter SHALL normalize permissive native defaults and enforce the mandatory baseline on all supported NIC, router, gateway and workload-attachment paths.

<!-- SOURCE-BLOCK HB11:266 END -->

<!-- SOURCE-BLOCK HB11:267 BEGIN -->

Platform engineering  \|  Verify: [CT-022](73-appendix-d-conformance-test-catalogue.md#test_CT_022), [CT-066](73-appendix-d-conformance-test-catalogue.md#test_CT_066), [CT-069](73-appendix-d-conformance-test-catalogue.md#test_CT_069)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  new-v1.1

<!-- SOURCE-BLOCK HB11:267 END -->

[Previous chapter](12-mz-oob-and-privileged-management-access.md) · [Chapter index](README.md) · [Next chapter](14-route-authority-and-safe-forwarding-compilation.md)
