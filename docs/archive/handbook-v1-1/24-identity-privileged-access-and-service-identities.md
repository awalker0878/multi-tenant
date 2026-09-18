# 24. Identity, privileged access and service identities

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<a id="__RefHeading___Toc13337_1645000677"></a>
<a id="sec_24"></a>

Use separate identities for people, workload-to-service authentication and automation actuators. Federation maps authoritative groups to scoped roles; short-lived credentials reduce standing privilege where the product supports them. Authentication does not authorize a route, and network reachability does not authorize an API action. Each privileged role has an approved task set, target scope, expiry/review and auditable owner.

Privileged access uses hardened administrative devices, phishing-resistant MFA where applicable, role-based task delegation, just-in-time grants and session records. Avoid reusing a high-authority credential on a workload host. Separate issuance, approval and use of security-sensitive credentials where the risk profile calls for it. Workload identities are narrowly scoped to the service and resource they consume; one tenant’s identity cannot enumerate or administer another tenant’s data.

Service accounts that cannot use short-lived credentials require vaulted secrets, rotation, revocation and a measured residual exposure window. Record credential use in CI/provider APIs without logging the secret. Recovery identities must be independent enough to survive normal IdP failure but remain strongly controlled, time-limited and tested. Offboarding revokes both direct role bindings and indirect group/token/session grants. Third-party support access is task-scoped, recorded and automatically expires. \[[S07](77-appendix-h-primary-sources-and-implementation-references.md#S07), secure system administration\]

<a id="req_IAM_001"></a>

IAM-001  Human, workload and automation identities SHALL have separately scoped authorization, credential lifecycle and accountability; no tenant identity SHALL acquire provider foundation authority through role or group inheritance.

Identity operations  \|  Verify: [CT-019](73-appendix-d-conformance-test-catalogue.md#test_CT_019), [CT-027](73-appendix-d-conformance-test-catalogue.md#test_CT_027), [CT-028](73-appendix-d-conformance-test-catalogue.md#test_CT_028)  \|  Basis: [S07](77-appendix-h-primary-sources-and-implementation-references.md#S07)  \|  new-v1.1

<a id="req_IAM_002"></a>

IAM-002  Privileged access SHALL use the approved hardened path, strong authentication, least privilege and time-bound delegation; emergency and supplier access SHALL be logged, tested and revoked after use.

Identity operations  \|  Verify: [CT-026](73-appendix-d-conformance-test-catalogue.md#test_CT_026), [CT-027](73-appendix-d-conformance-test-catalogue.md#test_CT_027), [CT-079](73-appendix-d-conformance-test-catalogue.md#test_CT_079)  \|  Basis: [S07](77-appendix-h-primary-sources-and-implementation-references.md#S07)  \|  new-v1.1

<a id="req_IAM_003"></a>

IAM-003  Credential and session revocation SHALL be verified at the consuming service within the approved propagation interval, including cached tokens and delegated grants.

Identity operations  \|  Verify: [CT-028](73-appendix-d-conformance-test-catalogue.md#test_CT_028), [CT-077](73-appendix-d-conformance-test-catalogue.md#test_CT_077), [CT-079](73-appendix-d-conformance-test-catalogue.md#test_CT_079)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  new-v1.1

[Previous chapter](23-storage-data-services-and-copy-lineage.md) · [Chapter index](README.md) · [Next chapter](25-cryptography-kms-certificates-and-crypto-agility.md)
