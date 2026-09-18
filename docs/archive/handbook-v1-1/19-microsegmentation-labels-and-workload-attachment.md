# 19. Microsegmentation, labels and workload attachment

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<a id="__RefHeading___Toc13325_1645000677"></a>
<a id="sec_19"></a>

A shared Security Domain Instance is not a shared trust assumption. The v1.1 baseline strengthens the original MICRO-001 recommendation to a mandatory default deny for unapproved WSD-to-WSD and tier-to-tier traffic. Required platform bootstrap services are explicitly profiled and do not become a general any-to-any exception. Same-host and same-subnet paths are included; tests that only cross a gateway miss important enforcement paths.

Policy selectors use immutable provider-owned security attributes, such as tenant, WSD, domain and role. Tenants may manage ordinary labels only where those labels cannot expand mandatory policy. The compiler resolves membership, precedence and permitted services before a workload is attached. Baseline rules dominate optional tenant rules. Guarded changes prevent a label update from temporarily moving an endpoint into a permissive default group.

Control extra NICs, source-address changes, permitted address pairs, virtual appliances, promiscuous access, nested virtualization, privileged containers and host-network attachment through explicit capabilities. A platform incapable of enforcing the required baseline is not accepted by substituting naming conventions or an operator promise. Delegated tenant policy authoring is allowed only inside a bounded envelope with effective-policy evaluation.

<a id="req_MICRO_001"></a>

MICRO-001  WSD-to-WSD and tier-to-tier communication inside a shared Security Domain Instance SHALL be denied unless an approved policy explicitly permits it.

Platform engineering  \|  Verify: [CT-021](73-appendix-d-conformance-test-catalogue.md#test_CT_021), [CT-066](73-appendix-d-conformance-test-catalogue.md#test_CT_066)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  revised-v1.0

<a id="req_MICRO_002"></a>

MICRO-002  Platform metadata used for security policy SHALL be managed, validated, and protected from unauthorized tenant modification.

Platform engineering  \|  Verify: [CT-020](73-appendix-d-conformance-test-catalogue.md#test_CT_020), [CT-066](73-appendix-d-conformance-test-catalogue.md#test_CT_066)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_MICRO_003"></a>

MICRO-003  The platform SHALL prevent unapproved NIC, source-identity, privileged-workload and label changes from bypassing mandatory segmentation; effective policy SHALL be verified for same-host and cross-host traffic.

Platform engineering  \|  Verify: [CT-020](73-appendix-d-conformance-test-catalogue.md#test_CT_020), [CT-021](73-appendix-d-conformance-test-catalogue.md#test_CT_021), [CT-022](73-appendix-d-conformance-test-catalogue.md#test_CT_022), [CT-065](73-appendix-d-conformance-test-catalogue.md#test_CT_065)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  new-v1.1

[Previous chapter](18-public-ingress-controlled-egress-and-external-exposure.md) · [Chapter index](README.md) · [Next chapter](20-provider-internal-edge-attachment-contract.md)
