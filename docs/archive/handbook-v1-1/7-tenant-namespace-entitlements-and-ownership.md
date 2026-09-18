# 7. Tenant Namespace, entitlements and ownership

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<a id="__RefHeading___Toc13301_1645000677"></a>
<a id="sec_7"></a>

A Tenant Namespace is the administrative root for identity groups, authorized service classes, quota, ownership, cost attribution and lifecycle. Use immutable non-semantic IDs in automation and readable names as labels. Renaming an organization or service must not rewrite security identity, address ownership or evidence history. All cross-tenant references are rejected unless an approved service-consumption or inter-tenant agreement explicitly authorizes them.

Separate the tenant service owner, tenant workload operator and tenant security reviewer. A tenant operator can request or manage entitled workload resources but cannot edit provider policy baselines, shared routing, management infrastructure or platform qualification. Provider read-only support views are tenant-scoped and redact credentials and other tenants’ metadata. Chargeback/showback can use opaque service/cost references without embedding organizational names in VRFs.


<a id="source-table-186"></a>

| Tenant lifecycle | Operational meaning |
| --- | --- |
| Requested | Ownership and entitlements are under review; no workload connectivity is implied. |
| Active | Entitled requests can be admitted under current profiles. |
| Restricted | Only a defined subset of operations is permitted; cause and remediation owner are recorded. |
| Suspended | New ordinary operations stop; existing workloads follow the explicit security/continuity decision. |
| Retiring / Retired | Dependencies and retention are reconciled; tombstone and evidence survive as required. |

<a id="req_TEN_001"></a>

TEN-001  Cross-tenant routing SHALL be denied by default even when two tenants use the same zone class.

Automation platform  \|  Verify: [CT-001](73-appendix-d-conformance-test-catalogue.md#test_CT_001), [CT-002](73-appendix-d-conformance-test-catalogue.md#test_CT_002), [CT-019](73-appendix-d-conformance-test-catalogue.md#test_CT_019)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_TEN_002"></a>

TEN-002  Tenant administrators SHALL NOT have authority to modify provider management, security-edge infrastructure, physical fabric, or another tenant namespace.

Automation platform  \|  Verify: [CT-019](73-appendix-d-conformance-test-catalogue.md#test_CT_019), [CT-026](73-appendix-d-conformance-test-catalogue.md#test_CT_026)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_TEN_003"></a>

TEN-003  Tenant ownership, entitlements and role bindings SHALL be versioned and auditable; suspension SHALL specify permitted recovery/containment actions and SHALL NOT imply indiscriminate workload deletion.

Service owner  \|  Verify: [CT-019](73-appendix-d-conformance-test-catalogue.md#test_CT_019), [CT-057](73-appendix-d-conformance-test-catalogue.md#test_CT_057), [CT-070](73-appendix-d-conformance-test-catalogue.md#test_CT_070)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  new-v1.1

[Previous chapter](08-part-ii-portable-security-architecture.md) · [Chapter index](README.md) · [Next chapter](8-wsd-intent-and-lifecycle-responsibility.md)
