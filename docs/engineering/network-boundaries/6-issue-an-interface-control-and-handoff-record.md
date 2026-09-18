# 6. Issue an interface control and handoff record

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/02_Engineering/Network_and_Boundary_Detailed_Engineering.docx) · [Chapter index](README.md)

> **Source:** NBD — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 7a86351d7f4be320e48d3112485bbab4b0f5b4a79cd0e420a823c793a708733a -->
<a id="NBD_06"></a>

Use this record for each material interface. Link it to the existing LLD network/route/flow schedules so the same facts are not maintained independently.

Design basis and related records: [ET §3](../../templates/lld/3-networks-addresses-and-native-gateways.md#ET_03)  •  [ET §4](../../templates/lld/4-routes-zips-and-permitted-flows.md#ET_04)  •  [PROV §1](../../implementation/provisioning-strategy/1-provisioning-scopes-ownership-and-accepted-handoffs.md#PROV_s_001)


<a id="source-table-73"></a>

| Field | Required interpretation | Working response |
| --- | --- | --- |
| Identity / endpoints | Stable interface ID; producer and consumer native objects; both endpoint owners. | \[Enter nbd interface id\] |
| Authority / membership | Domain and zone scope; who changes route, policy and endpoint membership. | \[Enter nbd authority\] |
| Forward and reply | Actual family, prefix, next hop, interface, route source and reverse-path owner. | \[Enter nbd routing\] |
| Security and identity | Permitted initiator/service, effective control, source validation and service entitlement. | \[Enter nbd enforcement\] |
| Capacity / failure | Accepted MTU, limits, HA mode, failure dependencies and safe loss behaviour. | \[Enter nbd failure budget\] |
| Acceptance / lifecycle | Configuration revision, observations, both owners’ handoff, reuse and withdrawal. | \[Enter nbd acceptance\] |

The producer signs off the available capability and permitted use; the consumer verifies that its own dependency is satisfied. A network handoff is incomplete when only one endpoint is known, the return path is unowned, or the selected feature lacks release-specific support.

Publish minimal accepted outputs for dependent packages: identities, scope, supported operation, limits and current restrictions. Keep credential custody and sensitive native configuration inside the owning administrative boundary. This record may be stored in an existing change/inventory system; it does not require a new API service.

Continue with: [PBS §8](../platform-build/8-publish-shared-service-handoffs-without-sharing-authority.md#PBS_08)  •  [IT §3](../../templates/implementation-mop/3-as-built-deviation-and-defect-record.md#IT_03)

[Previous chapter](5-keep-fabric-authority-separate-from-tenant-routing.md) · [Chapter index](README.md) · [Next chapter](7-release-the-network-design-under-an-explicit-failure-model.md)
