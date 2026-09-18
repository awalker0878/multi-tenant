# 39. Canonical API, object ownership and status

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<a id="__RefHeading___Toc13371_1645000677"></a>
<a id="sec_39"></a>

The API exposes versioned desired intent. The object envelope contains apiVersion, kind, metadata and spec; the controller maintains status through a separate authorization path. Metadata includes immutable identity, tenant scope, generation/resource version, ownership and lifecycle references. Status records observedGeneration, conditions, operation ID, qualified realization references and current evidence. A consumer-supplied “approved” or “compliant” value is never authoritative.

The companion JSON Schema uses Draft 2020-12 and closes normal object fields to prevent silent acceptance of misspellings or vendor-specific escape hatches. Syntax validation is only the first gate: semantic admission resolves references and versions, checks role authority, rejects cross-tenant references, validates zone adjacency, and proves capability/placement compatibility. Arrays with identity-bearing members are unique by logical ID, not merely by identical JSON bytes. \[[S30](77-appendix-h-primary-sources-and-implementation-references.md#S30)\]


<a id="source-table-550"></a>

| API behavior | Required contract |
| --- | --- |
| Create | Idempotency key; explicit owner and entitled profile references; no raw vendor topology |
| Update | Expected generation/resource version; reject stale updates; separate security-sensitive approval |
| Observe | Current desired and observed generation, non-secret conditions and operation history |
| Delete | Retirement request with dependency/retention finalizers; not an immediate blind destroy |
| Convert version | Published conversion, explicit defaults and no silent expansion of security permissions |
| Errors | Machine-readable reason, failing field/constraint and retry classification; no secret leakage |

Use a major-version change for a breaking semantic change; a compatible minor revision can add optional capabilities only with explicit safe defaults. The package’s hosting.platform/v1.1 contract is the proposed revision baseline, not a claim that an existing controller already supports it. Legacy illustrative v1 requests require an explicit migration because the new contract separates category fields, references typed profiles and removes REZ from internal domain enums.

<a id="req_API_001"></a>

API-001  The portable API SHALL be versioned and backward-compatibility rules SHALL be published.

Automation platform  \|  Verify: [CT-016](73-appendix-d-conformance-test-catalogue.md#test_CT_016), [CT-070](73-appendix-d-conformance-test-catalogue.md#test_CT_070)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_API_002"></a>

API-002  Vendor identifiers, VLAN/VNI/VRF details, route targets, raw firewall rules and raw next-hop routes SHALL NOT be part of the normal consumer contract.

Automation platform  \|  Verify: [CT-017](73-appendix-d-conformance-test-catalogue.md#test_CT_017), [CT-019](73-appendix-d-conformance-test-catalogue.md#test_CT_019)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_API_003"></a>

API-003  The API SHALL enforce immutable IDs, idempotent create, optimistic concurrency, typed/closed schemas, authorized references and controller-owned status; stale or unauthorized updates SHALL fail before side effects.

Automation platform  \|  Verify: [CT-017](73-appendix-d-conformance-test-catalogue.md#test_CT_017), [CT-046](73-appendix-d-conformance-test-catalogue.md#test_CT_046), [CT-070](73-appendix-d-conformance-test-catalogue.md#test_CT_070)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  new-v1.1

[Previous chapter](43-part-v-service-control-plane-and-automation.md) · [Chapter index](README.md) · [Next chapter](40-admission-flow-intention-and-policy-compilation.md)
