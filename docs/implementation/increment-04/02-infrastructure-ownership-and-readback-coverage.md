# Infrastructure ownership and readback coverage

[Documentation home](../../README.md) · [Source document](../../../Implementation_Execution_Guide.docx) · [Chapter index](README.md)

> **Source:** IMP04 — Implementation Increment 04. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 9ca5c85333dcb51137ca694aea7b034e393fa8927831f0b475b3b88e842418f7 -->
<!-- SOURCE-BLOCK IMP04:18 BEGIN -->

<a id="chapter_2"></a>

<!-- SOURCE-BLOCK IMP04:18 END -->

<!-- SOURCE-BLOCK IMP04:19 BEGIN -->

[Contents and release status](01-implementation-increment-04.md#chapter_1)

<!-- SOURCE-BLOCK IMP04:19 END -->

<!-- SOURCE-BLOCK IMP04:20 BEGIN -->

A native change can complete after its runner loses the reply. A successful configuration GET can precede policy realization. A completed task can coexist with the wrong resource state. Readback therefore means observing the selected native configuration and progress after the change, while retaining the actual owner, scope and version of the original operation.

<!-- SOURCE-BLOCK IMP04:20 END -->

<!-- SOURCE-BLOCK IMP04:21 BEGIN -->


<a id="source-table-21"></a>

| Owner / boundary | Accepted input | Observation or hold |
| --- | --- | --- |
| Platform resource owner | Exact native IDs, current expected fields and supported API profile | Compare selected configuration; no object creation or adoption |
| Network/security owner | Domain/gateway/policy and current expected realization version | Match the declared status span; preserve independent quarantine |
| Change and execution owner | Original operation, plan, generation, task IDs and writer status | Pending tasks and uncertain writers stop ordinary recovery |
| Incident authority | Current containment and release authority | An observation cannot release an active incident restriction |
| Operations / data owner | Current data/retention obligations and accepted operating conditions | Preserve resources and data until a separately authorized decision |

<!-- SOURCE-BLOCK IMP04:21 END -->

<!-- SOURCE-BLOCK IMP04:22 BEGIN -->

## Exact selected resources, not a discovery service

<!-- SOURCE-BLOCK IMP04:22 END -->

<!-- SOURCE-BLOCK IMP04:23 BEGIN -->

The NSX profile reads segments, Tier-1 gateways, static routes, groups and gateway/security policies through Local Manager paths. The Nutanix profile reads VPCs and subnets plus one known task through networking/prism v4.3. The existing Neutron reader is retained independently. No reader claims complete inventory or all-platform lifecycle coverage.

<!-- SOURCE-BLOCK IMP04:23 END -->

<!-- SOURCE-BLOCK IMP04:24 BEGIN -->

Portable tenant/domain labels are bound to native identities by an accepted engineering record. They do not create native RBAC or prove that the selected records cover every relevant dependency. A native tenantId is not automatically the architecture’s customer tenant label.

<!-- SOURCE-BLOCK IMP04:24 END -->

<!-- SOURCE-BLOCK IMP04:25 BEGIN -->

## Architecture remains the authority

<!-- SOURCE-BLOCK IMP04:25 END -->

<!-- SOURCE-BLOCK IMP04:26 BEGIN -->

[Reference architecture and provisioning strategy](../../architecture/reference/README.md)

<!-- SOURCE-BLOCK IMP04:26 END -->

<!-- SOURCE-BLOCK IMP04:27 BEGIN -->

[Worked infrastructure design and acceptance](../../solutions/internal-protected-workload/README.md)

<!-- SOURCE-BLOCK IMP04:27 END -->

<!-- SOURCE-BLOCK IMP04:28 BEGIN -->

[Increment04 architecture-to-code mapping](../../../sources/increment04_traceability.csv)

<!-- SOURCE-BLOCK IMP04:28 END -->

<!-- SOURCE-BLOCK IMP04:29 BEGIN -->

These tools fit the existing implementation work packages and evidence handoffs. They do not require a new hosting controller, resource API, scheduler, message bus or authorization application. Existing change and inventory systems can hold the records.

<!-- SOURCE-BLOCK IMP04:29 END -->

<!-- SOURCE-BLOCK IMP04:30 BEGIN -->

<!-- SOURCE-BLOCK IMP04:30 END -->

[Previous chapter](01-implementation-increment-04.md) · [Chapter index](README.md) · [Next chapter](03-nsx-configuration-and-realization.md)
