# 23. Storage, data services and copy lineage

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<!-- SOURCE-BLOCK HB11:374 BEGIN -->

<a id="__RefHeading___Toc13335_1645000677"></a>
<a id="sec_23"></a>

<!-- SOURCE-BLOCK HB11:374 END -->

<!-- SOURCE-BLOCK HB11:375 BEGIN -->

The portable storage contract defines block, file and object service semantics rather than a datastore or storage-container name. A StorageProfile specifies capacity, durability/availability expectations, access protocol, performance class, encryption/key policy, snapshot/clone/export rules, replication, retention, backup and sanitization. Distinguish a performance class from a hardware label: measured latency, IOPS/throughput and contention behavior are the acceptance criteria.

<!-- SOURCE-BLOCK HB11:375 END -->

<!-- SOURCE-BLOCK HB11:376 BEGIN -->

Each volume, share, bucket and recovery copy has a tenant/WSD identity, categorization, domain/location constraints and owner. Enforce authorization at storage APIs and data paths; a network route does not grant data access. Cross-tenant mounts, volume attachment, snapshots, clones and object access are denied unless a specific sharing service authorizes them. Replication, deduplication, cache, tiering and erasure coding are implementation details whose security and failure effects still require assessment.

<!-- SOURCE-BLOCK HB11:376 END -->

<!-- SOURCE-BLOCK HB11:377 BEGIN -->


<a id="source-table-377"></a>

| Data operation | Required portable semantics |
| --- | --- |
| Provision / attach | Quota reservation, correct tenant/domain, authenticated access, encryption context and performance profile |
| Snapshot / clone | Consistent point and copy lineage; inherited category/access/retention; explicit target authorization |
| Replicate / tier | Approved locations and keys; consistency, capacity and recovery dependence recorded |
| Export / import | Documented format/subset, integrity manifest, destination authorization and verified permissions |
| Retire / reuse | Retention/hold reconciliation, approved sanitization and evidence before reassignment |

<!-- SOURCE-BLOCK HB11:377 END -->

<!-- SOURCE-BLOCK HB11:378 BEGIN -->

S3-compatible object access is a de facto compatibility surface, not a blanket statement that all implementations have identical semantics. Qualify the required subset: object operations, listing/pagination, multipart, metadata/tags, versions, policy, encryption, retention and lifecycle behavior. Do not assume an object ETag is always a content MD5. For file and block services, qualify authentication/ACL mapping, locking, consistency and snapshot/export behavior across platforms. These are local portability acceptance requirements, not claims that every target supports every feature.

<!-- SOURCE-BLOCK HB11:378 END -->

<!-- SOURCE-BLOCK HB11:379 BEGIN -->

Storage performance and durability tests include rebuild/degraded operation and noisy-neighbor contention. Separate backup administration and key custody from routine production storage operation. Copy lineage must survive a WSD rename or migration so retained data, keys and deletion authority remain explainable. Disposal follows applicable GC rules and an approved sanitization method; NIST SP 800-88 Rev. 2 is a supporting technical reference, not a replacement for those rules. \[[S27](77-appendix-h-primary-sources-and-implementation-references.md#S27)\]

<!-- SOURCE-BLOCK HB11:379 END -->

<!-- SOURCE-BLOCK HB11:380 BEGIN -->

<a id="req_STO_001"></a>

STO-001  Every storage resource and derivative copy SHALL carry owner, categorization, access scope, key policy, placement/retention constraints and lineage; cross-scope attachment or export SHALL require explicit authorization.

<!-- SOURCE-BLOCK HB11:380 END -->

<!-- SOURCE-BLOCK HB11:381 BEGIN -->

Storage operations  \|  Verify: [CT-037](73-appendix-d-conformance-test-catalogue.md#test_CT_037), [CT-053](73-appendix-d-conformance-test-catalogue.md#test_CT_053), [CT-078](73-appendix-d-conformance-test-catalogue.md#test_CT_078)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  new-v1.1

<!-- SOURCE-BLOCK HB11:381 END -->

<!-- SOURCE-BLOCK HB11:382 BEGIN -->

<a id="req_STO_002"></a>

STO-002  Storage service profiles SHALL define measurable capacity/performance, consistency, replication, snapshot/clone and portability semantics and SHALL be tested under contention and the accepted failure condition.

<!-- SOURCE-BLOCK HB11:382 END -->

<!-- SOURCE-BLOCK HB11:383 BEGIN -->

Storage operations  \|  Verify: [CT-039](73-appendix-d-conformance-test-catalogue.md#test_CT_039), [CT-052](73-appendix-d-conformance-test-catalogue.md#test_CT_052), [CT-060](73-appendix-d-conformance-test-catalogue.md#test_CT_060)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  new-v1.1

<!-- SOURCE-BLOCK HB11:383 END -->

<!-- SOURCE-BLOCK HB11:384 BEGIN -->

<a id="req_STO_003"></a>

STO-003  Storage release and reuse SHALL reconcile all known copies and legal/administrative holds, apply an approved sanitization method and retain a receipt describing scope, method, verification and exceptions.

<!-- SOURCE-BLOCK HB11:384 END -->

<!-- SOURCE-BLOCK HB11:385 BEGIN -->

Storage operations  \|  Verify: [CT-053](73-appendix-d-conformance-test-catalogue.md#test_CT_053), [CT-059](73-appendix-d-conformance-test-catalogue.md#test_CT_059), [CT-078](73-appendix-d-conformance-test-catalogue.md#test_CT_078)  \|  Basis: [S27](77-appendix-h-primary-sources-and-implementation-references.md#S27)  \|  new-v1.1

<!-- SOURCE-BLOCK HB11:385 END -->

[Previous chapter](22-compute-hypervisor-security-and-co-residency.md) · [Chapter index](README.md) · [Next chapter](24-identity-privileged-access-and-service-identities.md)
