# 10. Resource ownership, protection and change receipts

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/07_Worked_Infrastructure_Design_and_Acceptance_v1_4.docx) · [Chapter index](README.md)

> **Source:** WD — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: e4a2e42888349b5967f7b3174c78e53171728b13e99e4c78bc3cfb53310f68db -->
<!-- SOURCE-BLOCK WD:107 BEGIN -->

<a id="WD14_S10"></a>

<!-- SOURCE-BLOCK WD:107 END -->

<!-- SOURCE-BLOCK WD:108 BEGIN -->

One environment spans several resource owners. It does not require one executor with all their credentials. The schedule below names the minimum accepted handoffs that join the design. An existing catalogue, change platform, workflow engine and inventory can carry these records without a custom provisioning application.

<!-- SOURCE-BLOCK WD:108 END -->

<!-- SOURCE-BLOCK WD:109 BEGIN -->

Observe, create, update, adopt, replace, delete and reconcile uncertain outcomes are separate coverage decisions. A provider that can create an object but cannot reliably find it after a timeout does not provide a complete managed lifecycle. Native installers and service owners retain the resources they actually control.

<!-- SOURCE-BLOCK WD:109 END -->

<!-- SOURCE-BLOCK WD:110 BEGIN -->

Late platform tasks are especially important. Losing an executor lease, revoking a credential or interrupting a pipeline does not prove that a previously accepted native operation has stopped. Before restarting or transferring ownership, the responsible owner discovers active tasks and their completed side effects. Data-safe forward repair can be preferable to reversal.

<!-- SOURCE-BLOCK WD:110 END -->

<!-- SOURCE-BLOCK WD:111 BEGIN -->


<a id="source-table-111"></a>

| Owned resource set | Authoritative owner / executor | Receipt consumed by the next package |
| --- | --- | --- |
| Fabric, OOB and link capacity | P1 network owner; selected supported configuration mechanism. | Actual topology, address/MTU/failure scope, available attachment members and recovery access. |
| Cluster, pools and native control | P2 platform owner; supported installer/lifecycle tooling. | Installed tuple, eligible pools, storage/network baseline and current acceptance restrictions. |
| EC/SE contexts and service policy | P3 security-edge and service owners. | Actual context/interface IDs, permitted prefixes, policy and session handling, capacity and path evidence. |
| Tenant/domain networks | P4 platform network owner using supported providers/APIs. | Native IDs mapped to D/A identifiers, resolved addresses, protected policy and single-writer ownership. |
| Names and address allocations | Authoritative IPAM/DNS owner; delegated native scopes explicitly reconciled. | Allocation and record identity, TTL/lease/reuse conditions, no competing allocator. |
| VMs, disks and endpoint identity | P5 workload/platform owner in eligible pools. | Actual placement, image, network/disk attachment, resource and protection ownership. |
| Capture, backups and keys | Protection/key owners under separated use and disposition authority. | Recoverable copy and catalogue/key references, retention, actual restore evidence and custody. |
| Activation and retirement | Named service/data/security authorities and the current owning executors. | Current approved scope, observed result, retained obligations and no obsolete live authority. |

<!-- SOURCE-BLOCK WD:111 END -->

<!-- SOURCE-BLOCK WD:112 BEGIN -->

<!-- SOURCE-BLOCK WD:112 END -->

<!-- SOURCE-BLOCK WD:113 BEGIN -->

Related documents: [PROV — Single writer and failure recovery](../../implementation/provisioning-strategy/README.md#V14_PROV_START)  \|  [SVC — Copy and key lifecycle](../../architecture/shared-services/README.md#V14_SVC_START)

<!-- SOURCE-BLOCK WD:113 END -->

<!-- SOURCE-BLOCK WD:114 BEGIN -->

<!-- SOURCE-BLOCK WD:114 END -->

[Previous chapter](9-build-sequence-with-explicit-acceptance-dependencies.md) · [Chapter index](README.md) · [Next chapter](11-test-resource-capacity-and-mtu-accounting.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0016 — Assign one authoritative writer per native object and sensitive subresource](../../adr/0016-assign-one-authoritative-writer-per-native-object-and-sensitive-subresource.md)

<!-- END GENERATED DECISION LINKS -->
