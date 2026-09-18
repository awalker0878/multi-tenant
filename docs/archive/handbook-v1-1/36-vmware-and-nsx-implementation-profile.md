# 36. VMware and NSX implementation profile

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<a id="__RefHeading___Toc13363_1645000677"></a>
<a id="sec_36"></a>

The full portable network/security profile requires a qualified networking/security layer such as NSX; plain vSphere networking is not assumed equivalent. The candidate design maps tenant administration to scoped IAM/NSX project constructs, domain instances to qualified routing contexts, workload networks to segments, microsegmentation to distributed policy and zone transitions to a tested gateway/edge or equivalent logical ZIP. All mappings are conditional on the selected release and supported resource model. \[[S00](77-appendix-h-primary-sources-and-implementation-references.md#S00), section 24; [S18](77-appendix-h-primary-sources-and-implementation-references.md#S18)\]

Distinguish a Tier-1 routing function from the service components that actually provide stateful gateway enforcement. A project boundary or tag is not a complete security authority by itself. The profile records distributed versus centralized routing, edge/service-router placement, Tier-0/external attachment authority, policy precedence, service insertion and failover. Test same-host distributed paths and inter-domain paths rather than inferring an appliance hop from the conceptual diagram.


<a id="source-table-516"></a>

| Portable concern | Required profile evidence |
| --- | --- |
| Administrative tenancy | Scoped project/IAM roles, provider/global policy ownership and tenant visibility restrictions |
| Routing and boundary enforcement | Actual Tier-1/Tier-0/edge topology, native route propagation, gateway policy and return-path behavior |
| Mandatory segmentation | Provider-owned groups/tags, rule hierarchy and protection against tenant override |
| Compute/storage integration | Placement/co-residency, image boot/vTPM dependencies, datastore policy and backup/restore |
| Automation and upgrades | Exact NSX/vSphere/provider tuple, API/resource coverage, import/update/delete and canary regression |

Workload owners never receive unrestricted global route or gateway-policy authority. Mandatory and tenant rules are generated from the same portable intent so they cannot silently diverge. Provider-managed tags and groups are reconciled with source identity, and native default connectivity is removed or constrained before attachment. A profile lacking the required edge inspection or isolation uses another qualified service or rejects placement; it does not downgrade the ZIP definition.

<a id="req_NSX_001"></a>

NSX-001  An NSX implementation SHALL keep tenant/project policy distinct from provider/global management and security policy.

Platform engineering  \|  Verify: [CT-019](73-appendix-d-conformance-test-catalogue.md#test_CT_019), [CT-020](73-appendix-d-conformance-test-catalogue.md#test_CT_020), [CT-066](73-appendix-d-conformance-test-catalogue.md#test_CT_066)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_NSX_002"></a>

NSX-002  Gateway policy used for zone transitions SHALL be generated from portable Flow/ZIP intent rather than manually duplicated per workload.

Platform engineering  \|  Verify: [CT-003](73-appendix-d-conformance-test-catalogue.md#test_CT_003), [CT-007](73-appendix-d-conformance-test-catalogue.md#test_CT_007), [CT-009](73-appendix-d-conformance-test-catalogue.md#test_CT_009)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_NSX_003"></a>

NSX-003  The NSX profile SHALL identify actual routing and enforcement components, global/project authority and policy precedence, and SHALL qualify their behavior on the selected product/provider tuple rather than equating a Tier-1 or project with a ZIP.

Platform engineering  \|  Verify: [CT-003](73-appendix-d-conformance-test-catalogue.md#test_CT_003), [CT-015](73-appendix-d-conformance-test-catalogue.md#test_CT_015), [CT-024](73-appendix-d-conformance-test-catalogue.md#test_CT_024), [CT-080](73-appendix-d-conformance-test-catalogue.md#test_CT_080)  \|  Basis: [S18](77-appendix-h-primary-sources-and-implementation-references.md#S18)  \|  new-v1.1

[Previous chapter](35-nutanix-implementation-profile.md) · [Chapter index](README.md) · [Next chapter](37-openstack-implementation-profile.md)
