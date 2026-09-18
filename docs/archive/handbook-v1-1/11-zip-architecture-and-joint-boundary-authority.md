# 11. ZIP architecture and joint boundary authority

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<a id="__RefHeading___Toc13309_1645000677"></a>
<a id="sec_11"></a>

A ZIP is the logical controlled interface connecting two zones. It can be realized by a qualified composition of routing, firewalling, service insertion, distributed enforcement, authentication, inspection and telemetry; it is not synonymous with a single appliance. The normal implementation uses an explicit security edge, but a distributed implementation is eligible only when it proves every required ZIP function, authority boundary, failure behavior and bypass constraint. A router, VPC or distributed firewall alone is not automatically a ZIP. \[[S01](77-appendix-h-primary-sources-and-implementation-references.md#S01), Annex F; [S02](77-appendix-h-primary-sources-and-implementation-references.md#S02), cloud ZIP mapping\]

Each ZIP binds exactly two adjacent domain/instance or external-domain endpoints and identifies the joint authority responsible for the boundary. That authority approves permitted services, directionality, inspection needs, management paths, security posture changes and evidence. A shared physical edge may host several logical ZIPs only if their policy, routing, identities, management privileges, logs and failure effects remain within the accepted profile.

![Two independent domain instances communicate only through their declared logical ZIP. A partner/public external domain has a separate boundary. An authorized management path administers the security service without becoming a workload transit path. A shared physical cluster may host independent ZIP contexts but does not merge their trust domains.](../../assets/diagrams/9bf5cbabc6ceabed9acf.png)

<a id="fig_zip"></a>

Figure 2. Boundary policy is separate from transport and shared infrastructure

Qualify enforcement for same-host traffic, direct native routing, connected routes on shared attachments, asymmetric return paths, source NAT, failover and stale sessions. Required functions include access control, authentication/integrity where applicable, malformed-protocol handling, required inspection/sensors, attributable logging and a heightened-security posture. Distinguish required inspection from traffic that remains end-to-end encrypted; certificate interception requires a specifically authorized design rather than an assumption that every ZIP decrypts traffic.

<a id="req_ZIP_001"></a>

ZIP-001  All inter-zone network paths SHALL traverse the applicable ZIP/security edge.

Security-edge operations  \|  Verify: [CT-003](73-appendix-d-conformance-test-catalogue.md#test_CT_003), [CT-080](73-appendix-d-conformance-test-catalogue.md#test_CT_080)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_ZIP_002"></a>

ZIP-002  A ZIP SHALL identify exactly two authorized adjacent endpoints, each an internal domain instance or approved external/management domain, and SHALL NOT create a general-purpose third-zone transit path.

Security authority  \|  Verify: [CT-023](73-appendix-d-conformance-test-catalogue.md#test_CT_023), [CT-025](73-appendix-d-conformance-test-catalogue.md#test_CT_025)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00) / [S01](77-appendix-h-primary-sources-and-implementation-references.md#S01) / [S02](77-appendix-h-primary-sources-and-implementation-references.md#S02)  \|  revised-v1.0

<a id="req_ZIP_003"></a>

ZIP-003  Default inter-zone policy SHALL be deny; allowed flows SHALL be generated from approved Flow Intentions and Service Bindings.

Security-edge operations  \|  Verify: [CT-007](73-appendix-d-conformance-test-catalogue.md#test_CT_007), [CT-025](73-appendix-d-conformance-test-catalogue.md#test_CT_025), [CT-066](73-appendix-d-conformance-test-catalogue.md#test_CT_066)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_ZIP_004"></a>

ZIP-004  ZIP management traffic SHALL be segregated from operational traffic.

Security-edge operations  \|  Verify: [CT-004](73-appendix-d-conformance-test-catalogue.md#test_CT_004), [CT-026](73-appendix-d-conformance-test-catalogue.md#test_CT_026)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_ZIP_005"></a>

ZIP-005  Data-path ZIPs and management-path ZIPs SHALL be governed and deployed as distinct security services; shared virtualization SHALL only be used where the applicable assurance analysis supports it.

Security authority  \|  Verify: [CT-026](73-appendix-d-conformance-test-catalogue.md#test_CT_026), [CT-035](73-appendix-d-conformance-test-catalogue.md#test_CT_035), [CT-080](73-appendix-d-conformance-test-catalogue.md#test_CT_080)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_ZIP_006"></a>

ZIP-006  Each ZIP SHALL record its two zone authorities, joint approval, required security functions, management authority, heightened posture, session-revocation behavior and current evidence.

Security authority  \|  Verify: [CT-067](73-appendix-d-conformance-test-catalogue.md#test_CT_067), [CT-077](73-appendix-d-conformance-test-catalogue.md#test_CT_077), [CT-080](73-appendix-d-conformance-test-catalogue.md#test_CT_080)  \|  Basis: [S01](77-appendix-h-primary-sources-and-implementation-references.md#S01) / [S02](77-appendix-h-primary-sources-and-implementation-references.md#S02)  \|  new-v1.1

<a id="req_ZIP_007"></a>

ZIP-007  A distributed or shared-infrastructure ZIP SHALL be qualified against the same required security outcomes as a dedicated edge; any unsupported mandatory function SHALL make that realization ineligible.

Platform engineering  \|  Verify: [CT-003](73-appendix-d-conformance-test-catalogue.md#test_CT_003), [CT-023](73-appendix-d-conformance-test-catalogue.md#test_CT_023), [CT-080](73-appendix-d-conformance-test-catalogue.md#test_CT_080)  \|  Basis: [S02](77-appendix-h-primary-sources-and-implementation-references.md#S02)  \|  new-v1.1

[Previous chapter](10-zone-classes-external-domains-and-adjacency.md) · [Chapter index](README.md) · [Next chapter](12-mz-oob-and-privileged-management-access.md)
