# 17. Shared services and explicit Service Bindings

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<a id="__RefHeading___Toc13321_1645000677"></a>
<a id="sec_17"></a>

A Service Binding grants consumption of an approved provider service to a specific domain or workload identity. The ServiceProfile defines endpoint identity, protocol/port, connection initiation, required authentication, certificates, availability, telemetry and administrative separation. Endpoint resolution is provider-owned and versioned. DNS, time, identity, PKI, logging, monitoring, backup and KMS are distinct services with different trust and failure characteristics.

A binding does not create a route to an entire common-services subnet. Where a service must initiate a connection, such as a pull-based backup or management agent flow, that direction is explicit and constrained to the intended workload identity. Multi-tenant service backends enforce their own data/API authorization even when network access is permitted. An authenticated service endpoint is not evidence that every tenant is entitled to every resource behind it.


<a id="source-table-306"></a>

| Service | Consumption path | Separated administrative path |
| --- | --- | --- |
| DNS / time | Approved resolver/time endpoints, limited protocols | Zone/clock configuration and service administration |
| Identity / PKI / KMS | Scoped authentication, certificate issuance or key-use API | Directory, trust-root, key lifecycle and recovery custody |
| Logging / monitoring | Authenticated ingestion or explicitly approved collection | Collector configuration, tenant log access and retention control |
| Backup | Approved agent/proxy/data endpoint and restore mediation | Backup policy, repository, immutability and custodial deletion |
| Image / software repository | Approved signed artefacts from controlled endpoints | Repository publication, signing keys and provenance control |

Zone-aligned endpoints can avoid unnecessary cross-zone connections, but duplicating an endpoint does not automatically make the service independent. Record shared controllers, keys, storage and failure domains. Service retirement includes identifying dependent WSDs, publishing a replacement/version change and revoking obsolete bindings after a controlled transition.

<a id="req_SVC_001"></a>

SVC-001  Consumers SHALL NOT receive broad routing to a shared-services supernet solely because they consume one shared service.

Service operations  \|  Verify: [CT-008](73-appendix-d-conformance-test-catalogue.md#test_CT_008), [CT-037](73-appendix-d-conformance-test-catalogue.md#test_CT_037)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_SVC_002"></a>

SVC-002  Where useful, shared services SHOULD expose zone-aligned endpoints so that consumption does not force unnecessary cross-zone routing.

Service operations  \|  Verify: [CT-008](73-appendix-d-conformance-test-catalogue.md#test_CT_008), [CT-025](73-appendix-d-conformance-test-catalogue.md#test_CT_025)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_SVC_003"></a>

SVC-003  Each ServiceProfile SHALL define direction, endpoint identity, authentication, allowed scope, availability, failure behavior and management separation; bindings SHALL be revoked when their entitlement or service version expires.

Service operations  \|  Verify: [CT-008](73-appendix-d-conformance-test-catalogue.md#test_CT_008), [CT-028](73-appendix-d-conformance-test-catalogue.md#test_CT_028), [CT-077](73-appendix-d-conformance-test-catalogue.md#test_CT_077)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  new-v1.1

[Previous chapter](16-ipv6-and-alternate-path-control.md) · [Chapter index](README.md) · [Next chapter](18-public-ingress-controlled-egress-and-external-exposure.md)
