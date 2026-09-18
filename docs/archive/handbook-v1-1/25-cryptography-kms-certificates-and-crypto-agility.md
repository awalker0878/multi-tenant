# 25. Cryptography, KMS, certificates and crypto agility

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK HB11:396 BEGIN -->

<a id="__RefHeading___Toc13339_1645000677"></a>
<a id="sec_25"></a>

<!-- SOURCE-BLOCK HB11:396 END -->

<!-- SOURCE-BLOCK HB11:397 BEGIN -->

Cryptography is a service dependency with ownership, lifecycle and failure behavior. The CryptographicProfile names approved algorithms/modes, protocols, trust roots, module-validation requirements, data/key separation, rotation, revocation, recovery and migration policy. Encryption at rest and in transit is the default for protected data paths in this handbook; a profile defines the exact scope, endpoints and exceptions. Encryption alone does not resolve administrator access, workload compromise or jurisdiction. \[[S09](77-appendix-h-primary-sources-and-implementation-references.md#S09); [S10](77-appendix-h-primary-sources-and-implementation-references.md#S10)\]

<!-- SOURCE-BLOCK HB11:397 END -->

<!-- SOURCE-BLOCK HB11:398 BEGIN -->

A KeyPolicy distinguishes tenant data keys, provider infrastructure keys, backup/recovery keys and signing keys. Record who can use a key, administer it, export/escrow it where permitted, disable it or destroy it. Key lifetime must cover all retained copies that must remain recoverable. A volume deletion is not proof of cryptographic erasure when plaintext copies, exported keys, snapshots or shared encryption contexts remain.

<!-- SOURCE-BLOCK HB11:398 END -->

<!-- SOURCE-BLOCK HB11:399 BEGIN -->

Test KMS failure before offering a service: determine whether running hosts cache keys, whether new boots/attachments fail, when cached authority expires and how recovery retrieves approved key material. No plaintext or unmanaged-key fallback is permitted. The recovery design avoids circular dependencies such as needing the failed KMS-hosting cluster to unlock its own only recovery copy.

<!-- SOURCE-BLOCK HB11:399 END -->

<!-- SOURCE-BLOCK HB11:400 BEGIN -->

Certificates have an issuer, subject/service identity, lifetime, trust distribution, renewal owner and revocation process. Validate peer identity, not merely encryption. Prefer modern supported protocol configurations; any legacy protocol exception has a bounded scope and remediation plan. Maintain a cryptographic inventory and a post-quantum transition dependency plan using the adopted current guidance; do not claim that every endpoint already supports new algorithms or that a product feature implies an approved cryptographic module.

<!-- SOURCE-BLOCK HB11:400 END -->

<!-- SOURCE-BLOCK HB11:401 BEGIN -->

<a id="req_CRY_001"></a>

CRY-001  Protected data services SHALL enforce their versioned cryptographic profile at rest and in transit; the profile SHALL identify approved algorithms/modes, endpoint identity validation, module/operating-environment evidence and exceptions.

<!-- SOURCE-BLOCK HB11:401 END -->

<!-- SOURCE-BLOCK HB11:402 BEGIN -->

Security authority  \|  Verify: [CT-028](73-appendix-d-conformance-test-catalogue.md#test_CT_028), [CT-038](73-appendix-d-conformance-test-catalogue.md#test_CT_038), [CT-063](73-appendix-d-conformance-test-catalogue.md#test_CT_063)  \|  Basis: [S09](77-appendix-h-primary-sources-and-implementation-references.md#S09) / [S10](77-appendix-h-primary-sources-and-implementation-references.md#S10)  \|  new-v1.1

<!-- SOURCE-BLOCK HB11:402 END -->

<!-- SOURCE-BLOCK HB11:403 BEGIN -->

<a id="req_CRY_002"></a>

CRY-002  Key use, administration, recovery and destruction SHALL have explicit separated authority and dependency records; key destruction SHALL NOT invalidate required retained-data recovery without an approved disposition decision.

<!-- SOURCE-BLOCK HB11:403 END -->

<!-- SOURCE-BLOCK HB11:404 BEGIN -->

Key-management operations  \|  Verify: [CT-038](73-appendix-d-conformance-test-catalogue.md#test_CT_038), [CT-053](73-appendix-d-conformance-test-catalogue.md#test_CT_053), [CT-059](73-appendix-d-conformance-test-catalogue.md#test_CT_059)  \|  Basis: [S09](77-appendix-h-primary-sources-and-implementation-references.md#S09)  \|  new-v1.1

<!-- SOURCE-BLOCK HB11:404 END -->

<!-- SOURCE-BLOCK HB11:405 BEGIN -->

<a id="req_CRY_003"></a>

CRY-003  KMS/trust-service outage behavior SHALL be tested and SHALL NOT enable plaintext fallback; cryptographic inventory, certificate rotation and algorithm-transition plans SHALL be maintained.

<!-- SOURCE-BLOCK HB11:405 END -->

<!-- SOURCE-BLOCK HB11:406 BEGIN -->

Key-management operations  \|  Verify: [CT-028](73-appendix-d-conformance-test-catalogue.md#test_CT_028), [CT-038](73-appendix-d-conformance-test-catalogue.md#test_CT_038), [CT-055](73-appendix-d-conformance-test-catalogue.md#test_CT_055)  \|  Basis: [S09](77-appendix-h-primary-sources-and-implementation-references.md#S09) / [S10](77-appendix-h-primary-sources-and-implementation-references.md#S10)  \|  new-v1.1

<!-- SOURCE-BLOCK HB11:406 END -->

[Previous chapter](24-identity-privileged-access-and-service-identities.md) · [Chapter index](README.md) · [Next chapter](26-images-configuration-baselines-and-endpoint-protection.md)
