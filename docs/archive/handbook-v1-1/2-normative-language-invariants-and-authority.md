# 2. Normative language, invariants and authority

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<a id="__RefHeading___Toc13289_1645000677"></a>
<a id="sec_2"></a>

SHALL identifies a requirement of this proposed handbook baseline; SHOULD identifies a recommendation that needs a recorded rationale when not followed; MAY identifies an optional capability. These words do not transform a locally authored requirement into a quotation from a government source. The adopting authority determines the binding policy hierarchy and approves the baseline. Requirements are defined once, assigned stable IDs, and used to generate Appendix C and the machine-readable catalogue.

Sources are separated into the user-provided baseline \[[S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)\], external guidance and standards \[[S01](77-appendix-h-primary-sources-and-implementation-references.md#S01)–[S30](77-appendix-h-primary-sources-and-implementation-references.md#S30)\], and explicit handbook design decisions. A source citation identifies context or the basis for a local translation. A control-family crosswalk is a selection aid, not proof that every enhancement or organization-defined parameter in a government control has been implemented. No unapproved exception changes a higher-authority obligation.

<a id="req_INV_001"></a>

INV-001  Tenant identity, security-zone identity, workload lifecycle, and platform realization are separate concepts.

Architecture authority  \|  Verify: [CT-016](73-appendix-d-conformance-test-catalogue.md#test_CT_016), [CT-070](73-appendix-d-conformance-test-catalogue.md#test_CT_070)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_INV_002"></a>

INV-002  A VPC, VRF, Tier-1 gateway, or Neutron router is an implementation mechanism, not the enterprise definition of a security zone.

Architecture authority  \|  Verify: [CT-025](73-appendix-d-conformance-test-catalogue.md#test_CT_025), [CT-080](73-appendix-d-conformance-test-catalogue.md#test_CT_080)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_INV_003"></a>

INV-003  Routes are derived from authorized intent; workload owners do not provide arbitrary route tables, BGP peers, route targets, or prefix imports/exports.

Architecture authority  \|  Verify: [CT-009](73-appendix-d-conformance-test-catalogue.md#test_CT_009), [CT-033](73-appendix-d-conformance-test-catalogue.md#test_CT_033)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_INV_004"></a>

INV-004  Shared services are exposed through explicit service bindings; broad reachability to a common-services supernet is not the default.

Architecture authority  \|  Verify: [CT-008](73-appendix-d-conformance-test-catalogue.md#test_CT_008)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_INV_005"></a>

INV-005  Portability means equivalent required outcomes and conformance, not identical topology.

Architecture authority  \|  Verify: [CT-016](73-appendix-d-conformance-test-catalogue.md#test_CT_016), [CT-060](73-appendix-d-conformance-test-catalogue.md#test_CT_060)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_INV_006"></a>

INV-006  A deployment is not Service Ready until realized state and security controls are verified.

Architecture authority  \|  Verify: [CT-049](73-appendix-d-conformance-test-catalogue.md#test_CT_049), [CT-069](73-appendix-d-conformance-test-catalogue.md#test_CT_069)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_INV_007"></a>

INV-007  Failure of an admission or control-plane dependency SHALL fail new changes closed; failure SHALL NOT silently create a security bypass.

Architecture authority  \|  Verify: [CT-011](73-appendix-d-conformance-test-catalogue.md#test_CT_011), [CT-045](73-appendix-d-conformance-test-catalogue.md#test_CT_045)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_REF_001"></a>

REF-001  The service contract SHALL remain stable when a supported platform is replaced, provided the replacement platform passes the required conformance profile.

Architecture authority  \|  Verify: [CT-016](73-appendix-d-conformance-test-catalogue.md#test_CT_016), [CT-060](73-appendix-d-conformance-test-catalogue.md#test_CT_060)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_REF_002"></a>

REF-002  Platform-specific extensions MAY be offered, but they SHALL be declared as capabilities and SHALL NOT redefine the portable core semantics.

Architecture authority  \|  Verify: [CT-016](73-appendix-d-conformance-test-catalogue.md#test_CT_016), [CT-018](73-appendix-d-conformance-test-catalogue.md#test_CT_018)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_DOC_001"></a>

DOC-001  Every normative requirement SHALL have a stable identifier, accountable owner, applicability, source basis, verification procedure and exception policy; generated catalogues SHALL contain every active requirement.

Architecture authority  \|  Verify: [CT-075](73-appendix-d-conformance-test-catalogue.md#test_CT_075)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  new-v1.1

<a id="req_AUTH_001"></a>

AUTH-001  Technical conformance, service readiness and formal authorization SHALL be recorded as distinct states; an automated test result SHALL NOT create, renew or impersonate an authorization decision.

Security authority  \|  Verify: [CT-049](73-appendix-d-conformance-test-catalogue.md#test_CT_049), [CT-069](73-appendix-d-conformance-test-catalogue.md#test_CT_069)  \|  Basis: [S04](77-appendix-h-primary-sources-and-implementation-references.md#S04) / [S05](77-appendix-h-primary-sources-and-implementation-references.md#S05)  \|  new-v1.1

[Previous chapter](1-purpose-scope-and-release-boundaries.md) · [Chapter index](README.md) · [Next chapter](3-standards-hierarchy-and-the-2026-baseline.md)
