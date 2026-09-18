# 34. Portability dimensions and platform qualification

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<a id="__RefHeading___Toc13359_1645000677"></a>
<a id="sec_34"></a>

Portability has four distinct dimensions: the same consumer contract can be admitted; equivalent security/service semantics can be realized; workload images/data can be recovered on the target; and operators can run, monitor, patch and retire the result. Passing one dimension does not prove the others. A networking adapter can be contract-conformant while an application remains dependent on a proprietary device or database format.

Every platform has a capability record tied to product versions, APIs, Terraform provider source/version, licensing/entitlements, enabled features, hardware profile, site/failure topology and conformance evidence. A documentation-only candidate is not production eligible. Qualification changes are versioned; security-impacting upgrade, expiry, significant drift or unsupported lifecycle status can suspend new placement until assessed.


<a id="source-table-490"></a>

| Capability state | Meaning / placement treatment |
| --- | --- |
| Candidate | Mapping/design exists; exact tuple or evidence not yet approved. Production placement denied. |
| Testing | Tuple and test campaign assigned; failures and limitations visible. Production placement denied. |
| Qualified | All mandatory tests and approvals for named profiles are current. Only those profiles can be placed. |
| Restricted | Specific capability or service classes are suspended; safe existing operation is separately assessed. |
| Expired / Revoked | New placement denied; existing workloads follow the approved risk/continuity decision. |

The initial profiles in sections 35-38 are target designs, not invented certification records. Product/provider versions unavailable from the user’s environment are deliberately not labelled tested. The companion schema enforces that a qualified record contains a full tuple, evidence digest, tested profiles, validity interval and approving authority. A feature advertised in vendor documentation remains insufficient until the selected deployment proves the required behavior.

<a id="req_PORT_001"></a>

PORT-001  Every platform SHALL publish a machine-readable capability profile and a tested implementation profile.

Platform engineering  \|  Verify: [CT-015](73-appendix-d-conformance-test-catalogue.md#test_CT_015), [CT-018](73-appendix-d-conformance-test-catalogue.md#test_CT_018), [CT-080](73-appendix-d-conformance-test-catalogue.md#test_CT_080)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_PORT_002"></a>

PORT-002  A placement decision SHALL fail rather than silently reduce a requested security or availability capability.

Automation platform  \|  Verify: [CT-018](73-appendix-d-conformance-test-catalogue.md#test_CT_018), [CT-061](73-appendix-d-conformance-test-catalogue.md#test_CT_061)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_PORT_003"></a>

PORT-003  Platform-specific features MAY be exposed as optional extensions provided the WSD declares the dependency and portability impact.

Architecture authority  \|  Verify: [CT-016](73-appendix-d-conformance-test-catalogue.md#test_CT_016), [CT-060](73-appendix-d-conformance-test-catalogue.md#test_CT_060), [CT-073](73-appendix-d-conformance-test-catalogue.md#test_CT_073)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_QUAL_001"></a>

QUAL-001  Production placement SHALL require a current qualified PlatformProfile containing the exact product/API/provider/hardware tuple, applicable features/licenses, tested limits, evidence and approval; a candidate or documentation snapshot SHALL be ineligible.

Security authority  \|  Verify: [CT-015](73-appendix-d-conformance-test-catalogue.md#test_CT_015), [CT-018](73-appendix-d-conformance-test-catalogue.md#test_CT_018), [CT-069](73-appendix-d-conformance-test-catalogue.md#test_CT_069)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  new-v1.1

[Previous chapter](33-evpn-vxlan-multihoming-and-border-engineering.md) · [Chapter index](README.md) · [Next chapter](35-nutanix-implementation-profile.md)
