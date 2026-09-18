# 37. OpenStack implementation profile

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<a id="__RefHeading___Toc13365_1645000677"></a>
<a id="sec_37"></a>

OpenStack administration maps to Keystone project/role scope; domain instances use qualified Neutron routing/address contexts, networks/subnets and a defined boundary enforcement design. Nova, Cinder and the selected image/key/backup services provide the other hosting functions. The distribution, Neutron backend, enabled extensions, API policy and supporting services are part of the capability record. The existence of a generic OpenStack provider does not imply every distribution exposes identical behavior. \[[S00](77-appendix-h-primary-sources-and-implementation-references.md#S00), section 25; [S19](77-appendix-h-primary-sources-and-implementation-references.md#S19)\]

Normalize all applicable security-group defaults rather than assuming they already implement the service deny baseline. Control external network/router access, floating addresses, additional ports, port-security settings and allowed address pairs. Native Neutron routers provide connectivity; stateful inter-zone inspection, shared-service isolation, policy precedence and management separation need an explicit qualified construction. Tenant API permissions must prevent creation of alternate paths outside the contract.


<a id="source-table-527"></a>

| Portable concern | Required profile evidence |
| --- | --- |
| Tenant / identity | Keystone project scope, roles, application credentials and provider-owned API policy |
| Routing / external paths | Neutron backend, router/namespace or logical-routing behavior, provider/external network scope and floating-address authority |
| Segmentation | Security-group defaults, port security, permitted address pairs and immutable mandatory policy |
| Data / compute | Nova placement, Cinder storage scope, image provenance, key integration and recovery support |
| Operations | Exact distribution/service/provider versions, quotas, API throttling, eventual consistency and cleanup behavior |

An administrator-controlled policy layer may be needed when tenant-editable security groups cannot express the mandatory boundary hierarchy. Shared networks are not an isolation shortcut. Confirm whether enabled backend features support the required address families, failure modes and inspection; unsupported functionality is recorded in the registry. Test project deletion and asynchronous port/router removal for stale routes, leases and addresses, not just successful Terraform deletion messages.

<a id="req_OS_001"></a>

OS-001  Default OpenStack security-group behaviour SHALL be reviewed and normalized to the secure-by-default service baseline.

Platform engineering  \|  Verify: [CT-005](73-appendix-d-conformance-test-catalogue.md#test_CT_005), [CT-021](73-appendix-d-conformance-test-catalogue.md#test_CT_021), [CT-066](73-appendix-d-conformance-test-catalogue.md#test_CT_066)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_OS_002"></a>

OS-002  Provider networks and external-router capabilities SHALL remain provider controlled and SHALL not become unrestricted tenant escape paths.

Platform engineering  \|  Verify: [CT-019](73-appendix-d-conformance-test-catalogue.md#test_CT_019), [CT-022](73-appendix-d-conformance-test-catalogue.md#test_CT_022), [CT-023](73-appendix-d-conformance-test-catalogue.md#test_CT_023)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_OS_003"></a>

OS-003  The OpenStack profile SHALL record distribution, service/API versions, Neutron backend/extensions and provider authority over external/port-security operations; native routing or editable security groups SHALL NOT be assumed to satisfy all ZIP functions.

Platform engineering  \|  Verify: [CT-015](73-appendix-d-conformance-test-catalogue.md#test_CT_015), [CT-018](73-appendix-d-conformance-test-catalogue.md#test_CT_018), [CT-022](73-appendix-d-conformance-test-catalogue.md#test_CT_022), [CT-080](73-appendix-d-conformance-test-catalogue.md#test_CT_080)  \|  Basis: [S19](77-appendix-h-primary-sources-and-implementation-references.md#S19)  \|  new-v1.1

[Previous chapter](36-vmware-and-nsx-implementation-profile.md) · [Chapter index](README.md) · [Next chapter](38-bare-metal-containers-and-future-platforms.md)
