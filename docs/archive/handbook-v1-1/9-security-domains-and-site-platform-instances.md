# 9. Security Domains and site/platform instances

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<a id="__RefHeading___Toc13305_1645000677"></a>
<a id="sec_9"></a>

A logical Security Domain binds zone class, security authority, tenant/provider scope, address policy, allowed sharing and assurance. An instance binds that policy to one site, platform tuple and failure domain. Site-local instances are preferred; inter-site replication is an explicit controlled service. A domain’s policies are portable, but its implementation may be a VPC, routing context, scoped Tier-1 design or another tested construction.

Do not equate “same zone class” with “same zone” or “same routing authority”. Two restricted-zone instances belonging to different tenants are independently isolated. Within an approved shared instance, microsegmentation protects WSDs and tiers. Stronger profiles can require dedicated instances, hosts, security contexts, storage scope and administration rather than only an extra router.


<a id="source-table-206"></a>

| Identity | Immutable or controlled attributes |
| --- | --- |
| Logical domain | domainId, zoneClass, authorityRef, tenant/provider owner, assuranceRef, sharingPolicyRef |
| Instance | instanceId, domainRef, siteRef, platformProfileRef, addressScopeRef, edgeAttachmentRefs |
| Observed realization | Native IDs, network/route-policy digest, active generation, enforcement locations, test/evidence references |

<a id="req_SDI_001"></a>

SDI-001  A Security Domain Instance SHALL contain only networks authorized to share its routing/security authority.

Security authority  \|  Verify: [CT-025](73-appendix-d-conformance-test-catalogue.md#test_CT_025), [CT-035](73-appendix-d-conformance-test-catalogue.md#test_CT_035)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_SDI_002"></a>

SDI-002  Sharing a zone class SHALL NOT imply reachability between independent Security Domain Instances.

Platform engineering  \|  Verify: [CT-001](73-appendix-d-conformance-test-catalogue.md#test_CT_001), [CT-002](73-appendix-d-conformance-test-catalogue.md#test_CT_002), [CT-021](73-appendix-d-conformance-test-catalogue.md#test_CT_021)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_SDI_003"></a>

SDI-003  Dedicated Security Domain Instances SHOULD be available for workloads whose assurance profile or threat model requires stronger isolation than shared logical segmentation.

Platform engineering  \|  Verify: [CT-018](73-appendix-d-conformance-test-catalogue.md#test_CT_018), [CT-035](73-appendix-d-conformance-test-catalogue.md#test_CT_035)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_SDI_004"></a>

SDI-004  Each Security Domain Instance SHALL reference a logical domain and a qualified site/platform realization; membership and sharing changes SHALL be assessed as security-significant changes.

Security authority  \|  Verify: [CT-025](73-appendix-d-conformance-test-catalogue.md#test_CT_025), [CT-035](73-appendix-d-conformance-test-catalogue.md#test_CT_035), [CT-048](73-appendix-d-conformance-test-catalogue.md#test_CT_048)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  new-v1.1

[Previous chapter](8-wsd-intent-and-lifecycle-responsibility.md) · [Chapter index](README.md) · [Next chapter](10-zone-classes-external-domains-and-adjacency.md)
