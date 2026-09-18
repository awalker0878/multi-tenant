# 8. Publish shared-service handoffs without sharing authority

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/02_Engineering/Platform_Engineering_and_Build_Specifications.docx) · [Chapter index](README.md)

> **Source:** PBS — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 8c2dd9e86b4ea021922777a963534c6b52d85dff8ee398c3a12cc81287356643 -->
<!-- SOURCE-BLOCK PBS:95 BEGIN -->

<a id="PBS_08"></a>

<!-- SOURCE-BLOCK PBS:95 END -->

<!-- SOURCE-BLOCK PBS:96 BEGIN -->

Each integration is a producer/consumer agreement about usable infrastructure. It is not a reason to grant the consumer every privilege held by the producer.

<!-- SOURCE-BLOCK PBS:96 END -->

<!-- SOURCE-BLOCK PBS:97 BEGIN -->

Design basis and related records: [PROV §1](../../implementation/provisioning-strategy/1-provisioning-scopes-ownership-and-accepted-handoffs.md#PROV_s_001)  •  [PROV §3](../../implementation/provisioning-strategy/3-terraform-native-tools-and-operation-level-support.md#PROV_s_003)  •  [SVC §1](../../architecture/shared-services/1-shared-service-placement-and-consumption-boundaries.md#SVC_s_001)  •  [EK §5](../delivery-guide/5-management-and-shared-service-interfaces.md#EK_05)

<!-- SOURCE-BLOCK PBS:97 END -->

<!-- SOURCE-BLOCK PBS:98 BEGIN -->


<a id="source-table-98"></a>

| Producer | Minimum accepted output | Consumer action / limit |
| --- | --- | --- |
| Fabric / attachment owner | Actual interface, transport class, allowed use, capacity, MTU and acceptance revision. | Platform owner consumes the attachment; does not change spine policy. |
| Security-edge owner | Approved domain pair, route/policy references, handoff identities and enforcement restrictions. | Domain owner configures its side; does not receive edge administrator credentials. |
| IPAM and naming owner | Reserved prefix/address ownership, DNS/DHCP policy and confirmed lifecycle receipt. | Workload owner registers only accepted assignments; no independent competing allocator. |
| Data/trust/protection owner | Tenant data scope, key/client identity, capture/restore path and retained obligations. | Actual client receives only its entitled use; producer administration stays separate. |
| Operations owner | Required events, health scope, alert routing, loss handling and accepted recovery interface. | Service handover proves observation and support, not merely installation of an agent. |

<!-- SOURCE-BLOCK PBS:98 END -->

<!-- SOURCE-BLOCK PBS:99 BEGIN -->

<!-- SOURCE-BLOCK PBS:99 END -->

<!-- SOURCE-BLOCK PBS:100 BEGIN -->

HashiCorp notes that terraform\_remote\_state output access requires access to the underlying state snapshot and recommends separate publication where different access controls are needed. A handoff can therefore publish narrowly scoped accepted facts rather than granting broad state access. The implementation chooses its existing controlled inventory or publication mechanism. \[D04\]

<!-- SOURCE-BLOCK PBS:100 END -->

<!-- SOURCE-BLOCK PBS:101 BEGIN -->

Verified mechanism source: [D04 — HashiCorp: terraform\_remote\_state data source](https://developer.hashicorp.com/terraform/language/state/remote-state-data)

<!-- SOURCE-BLOCK PBS:101 END -->

<!-- SOURCE-BLOCK PBS:102 BEGIN -->

Acceptance is bidirectional: producer confirms the offered capability, consumer confirms its dependency is met. A change in service version, allowed prefix, key scope or failure behaviour invalidates affected downstream assumptions. Notify consumers and re-evaluate the corresponding paths before using the changed handoff.

<!-- SOURCE-BLOCK PBS:102 END -->

<!-- SOURCE-BLOCK PBS:103 BEGIN -->

Continue with: [NBD §6](../network-boundaries/6-issue-an-interface-control-and-handoff-record.md#NBD_06)  •  [OPS §2](../../operations/recovery-transition/2-specify-dependency-loss-before-it-becomes-an-incident.md#OPS_02)

<!-- SOURCE-BLOCK PBS:103 END -->

<!-- SOURCE-BLOCK PBS:104 BEGIN -->

<!-- SOURCE-BLOCK PBS:104 END -->

[Previous chapter](7-openstack-protect-mandatory-network-mutation.md) · [Chapter index](README.md) · [Next chapter](9-release-a-native-build-package-that-can-be-independently-reviewed.md)
