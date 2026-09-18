# 56. Lifecycle, retirement and secure disposal

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<a id="__RefHeading___Toc13407_1645000677"></a>
<a id="sec_56"></a>

Retirement is a dependency-aware security and data-governance workflow. Separate terminating the live service from disposing of every retained copy. A legal/administrative retention obligation can outlive a WSD; represent it as a RetainedDataRecord with owner, access boundary, retention/hold policy, key dependency and final destruction authority. The tenant inventory retains a tombstone rather than silently losing evidence. \[[S27](77-appendix-h-primary-sources-and-implementation-references.md#S27)\]


<a id="source-table-740"></a>

| Step | Action and completion condition |
| --- | --- |
| 1 | Set Retiring, freeze optional new dependencies, identify consumers and approve the retirement/data-retention plan. |
| 2 | Verify required backups/exports and holds before removing the paths or identities needed to create them; test required recoverability. |
| 3 | Withdraw public ingress and discretionary egress; notify dependent service owners and coordinate DNS TTL/cutover. |
| 4 | Revoke obsolete application flows, bindings and sessions in dependency-safe order while retaining only authorized recovery/retention paths. |
| 5 | Stop and remove workload/ephemeral resources; remove unused domain instances only when no other owner/reference requires them. |
| 6 | Withdraw routes/attachments, remove DNS/DHCP records and release prefixes through quarantine; verify stale caches, leases and policy objects. |
| 7 | Revoke workload/automation identities, secrets and certificates; retain only separately authorized retained-data access and required recovery keys. |
| 8 | Sanitize disposable media/data according to the approved method and evidence; track replicas, snapshots, caches and offline copies; do not destroy shared/held keys prematurely. |
| 9 | Verify absence of live connectivity/authority, record retained-copy obligations and destruction evidence, and close service inventory with an auditable tombstone. |

Choose sanitization using the media technology, data sensitivity and validated method. Cryptographic erase depends on effective encryption and exclusive key scope; deleting a shared key or merely deleting a volume record is not proof that all data copies were sanitized. For retained copies, report the remaining obligations accurately rather than marking total destruction complete. NIST SP 800-88 Rev. 2 is supporting guidance; applicable organizational disposal requirements remain authoritative. \[[S27](77-appendix-h-primary-sources-and-implementation-references.md#S27)\]

Deletion finalizers protect dependencies and held data, but they cannot become silent permanent blockers. Operators need an audited escalation path that resolves each obligation before removing a finalizer. Repeated deletion requests are idempotent. Resource name reuse cannot inherit stale identity, DNS, storage entitlement or firewall policy.

<a id="req_LIFE_001"></a>

LIFE-001  Offboarding SHALL remove obsolete routes and policy objects and SHALL produce evidence of completion.

Service management  \|  Verify: [CT-013](73-appendix-d-conformance-test-catalogue.md#test_CT_013), [CT-059](73-appendix-d-conformance-test-catalogue.md#test_CT_059), [CT-070](73-appendix-d-conformance-test-catalogue.md#test_CT_070)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_LIFE_002"></a>

LIFE-002  Retirement SHALL distinguish live-service removal from retained-data obligations and SHALL verify identity, DNS, route, policy, attachment, copy and key lifecycle without deleting shared or held resources.

Service management  \|  Verify: [CT-013](73-appendix-d-conformance-test-catalogue.md#test_CT_013), [CT-053](73-appendix-d-conformance-test-catalogue.md#test_CT_053), [CT-059](73-appendix-d-conformance-test-catalogue.md#test_CT_059), [CT-070](73-appendix-d-conformance-test-catalogue.md#test_CT_070), [CT-078](73-appendix-d-conformance-test-catalogue.md#test_CT_078)  \|  Basis: [S27](77-appendix-h-primary-sources-and-implementation-references.md#S27)  \|  new-v1.1

<a id="req_LIFE_003"></a>

LIFE-003  Sanitization SHALL use an approved media-appropriate method with copy/key-scope evidence; deletion of a resource record SHALL NOT alone constitute proof of data destruction.

Data owner  \|  Verify: [CT-053](73-appendix-d-conformance-test-catalogue.md#test_CT_053), [CT-059](73-appendix-d-conformance-test-catalogue.md#test_CT_059)  \|  Basis: [S27](77-appendix-h-primary-sources-and-implementation-references.md#S27)  \|  new-v1.1

[Previous chapter](55-incident-response-and-scoped-containment.md) · [Chapter index](README.md) · [Next chapter](57-migration-portability-and-exit-rehearsal.md)
