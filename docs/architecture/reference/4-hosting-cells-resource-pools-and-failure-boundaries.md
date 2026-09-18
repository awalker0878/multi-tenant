# 4. Hosting cells, resource pools and failure boundaries

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/00_Reference_Architecture_v1_4.docx) · [Chapter index](README.md)

> **Source:** RA — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: e50894d7f7b87cef50a283399b85925c8a96c5b9cd0428ce71ca0143d9be8d19 -->
<!-- SOURCE-BLOCK RA:93 BEGIN -->

<a id="__RefHeading___Toc3646_865363315"></a>
<a id="RA_s_004"></a>

<!-- SOURCE-BLOCK RA:93 END -->

<!-- SOURCE-BLOCK RA:94 BEGIN -->

A hosting cell is the provider unit for commissioning, capacity expansion, version control and failure containment. It is introduced here as an architectural term, not as an OpenStack Nova cell or a vendor product. A cell normally uses one qualified platform stack, a defined site, named compute/storage resources and explicit attachments to management, transport and security services. Several cells can share a site fabric without sharing tenant routing.

<!-- SOURCE-BLOCK RA:94 END -->

<!-- SOURCE-BLOCK RA:95 BEGIN -->

The reference separates management capacity, security-edge capacity and tenant workload capacity. Within workload capacity, host pools enforce the adopted zone and co-residency policy. A small site may combine some physical roles only through a documented variation that preserves the required isolation and recovery behaviour. It must not describe logical separation as physical independence.

<!-- SOURCE-BLOCK RA:95 END -->

<!-- SOURCE-BLOCK RA:96 BEGIN -->


<a id="source-table-96"></a>

| Cell boundary | Required design decision | Growth action |
| --- | --- | --- |
| Compute | Eligible hosts, zone/domain sharing, accelerators, host/rack failure tolerance | Add qualified hosts or a new pool; validate evacuation and restart constraints |
| Storage | Backend and controller scope, usable capacity, rebuild reserve, copy locations | Expand an existing supported fault domain or add a separately qualified storage pool |
| Network | Transport endpoints, routed attachment slots, prefix/route/policy limits | Increase commissioned capacity; do not silently share an exhausted isolation context |
| Control | Managers, API authority, release compatibility and recovery dependencies | Scale or introduce a separate management scope before its supported limit |
| Security services | Logical contexts, inspection/session capacity, log throughput and failure headroom | Expand the edge service before accepting additional protected connectivity |

<!-- SOURCE-BLOCK RA:96 END -->

<!-- SOURCE-BLOCK RA:97 BEGIN -->

<!-- SOURCE-BLOCK RA:97 END -->

<!-- SOURCE-BLOCK RA:98 BEGIN -->

The provider advertises available capacity by service class, not merely total free CPU or terabytes. Usable capacity is the amount that remains deliverable after the agreed failure and operational reserves. Capacity that is installed but lacks a compatible storage tier, security-edge slot, licence, address pool or operational owner is not ready for tenant allocation. Ordered, received, staged, commissioned, available, reserved and consumed capacity are separate inventory states.

<!-- SOURCE-BLOCK RA:98 END -->

<!-- SOURCE-BLOCK RA:99 BEGIN -->

No specific number of hosts, switches or firewall instances is prescribed for every site. The site design derives counts from quorum, supported platform minima, sustained load under failure, maintenance and growth. A two-node symbol in a topology means redundant roles, not a claim that two nodes satisfy every product or assurance requirement. The commissioning record establishes the actual independent resources and bottlenecks.

<!-- SOURCE-BLOCK RA:99 END -->

<!-- SOURCE-BLOCK RA:100 BEGIN -->

Routine tenant growth consumes previously commissioned pools. Provider growth changes pools, attachments or cells under a separate infrastructure change. This separation is the practical meaning of capacity on demand: ordinary workload requests do not trigger procurement, physical cabling or an unreviewed fabric design. A capacity deficit results in an explicit queue, alternate eligible placement or rejection.

<!-- SOURCE-BLOCK RA:100 END -->

<!-- SOURCE-BLOCK RA:101 BEGIN -->

A cell is not declared independently resilient until actual power, rack, switching, storage, control, security and trust dependencies are recorded. Count logical attachment slots separately from redundant links and edge processing capacity. A free slot is not usable capacity when another required resource is exhausted. QUAL §3 supplies unit-aware illustrative admission arithmetic; its numbers are not site sizing or approved service commitments.

<!-- SOURCE-BLOCK RA:101 END -->

<!-- SOURCE-BLOCK RA:102 BEGIN -->

Related engineering: [QUAL §2 — Site low-level design and dependency schedule](../../assurance/site-qualification/2-site-low-level-design-and-dependency-schedule.md#QUAL_s_002)  •  [QUAL §3 — Capacity, service envelopes and growth triggers](../../assurance/site-qualification/3-capacity-service-envelopes-and-growth-triggers.md#QUAL_s_003)  •  [NET §2 — Isolated attachment units and bounded capacity](../../engineering/fabric/2-isolated-attachment-units-and-bounded-capacity.md#NET_s_002)

<!-- SOURCE-BLOCK RA:102 END -->

[Previous chapter](3-system-context-and-physical-hosting-topology.md) · [Chapter index](README.md) · [Next chapter](5-physical-fabric-and-platform-attachment.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0004 — Scale through commissioned hosting cells and capacity pools](../../adr/0004-scale-through-commissioned-hosting-cells-and-capacity-pools.md)
- [ADR-0030 — Admit demand against every surviving-capacity bottleneck](../../adr/0030-admit-demand-against-every-surviving-capacity-bottleneck.md)

<!-- END GENERATED DECISION LINKS -->
