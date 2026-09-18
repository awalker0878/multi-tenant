# 3. Capacity, service envelopes and growth triggers

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/06_Site_Design_Qualification_and_Operations_v1_4.docx) · [Chapter index](README.md)

> **Source:** QUAL — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 783edbba45483d0d3c3b966765589762698836320237906a0f9a60080574af37 -->
<!-- SOURCE-BLOCK QUAL:43 BEGIN -->

<a id="__RefHeading___Toc10037_1525915568"></a>
<a id="QUAL_s_003"></a>

<!-- SOURCE-BLOCK QUAL:43 END -->

<!-- SOURCE-BLOCK QUAL:44 BEGIN -->

Parent architecture: [RA §4](../../architecture/reference/4-hosting-cells-resource-pools-and-failure-boundaries.md#RA_s_004)  •  [RA §11](../../architecture/reference/11-compute-pools-hypervisors-and-workload-placement.md#RA_s_011)  •  [RA §12](../../architecture/reference/12-storage-backup-and-data-isolation-architecture.md#RA_s_012)  •  [RA §14](../../architecture/reference/14-availability-multi-site-operation-and-recovery-topology.md#RA_s_014)  •  [RA §26](../../architecture/reference/26-operating-model-capacity-and-observability.md#RA_s_026)

<!-- SOURCE-BLOCK QUAL:44 END -->

<!-- SOURCE-BLOCK QUAL:45 BEGIN -->

Admission is a multi-resource decision. Evaluate eligible compute, usable storage, inspected edge capacity, routing/policy objects, attachment contexts, addresses, API/service capacity and required recovery reserve together. Requested, reserved, consumed, procured and commissioned capacity are different quantities. A large installed total does not mean a particular service class can safely consume it. \[[B2](09-references-parent-basis-and-external-context.md#QUAL_src_B2) §§4, 14, 26\]

<!-- SOURCE-BLOCK QUAL:45 END -->

<!-- SOURCE-BLOCK QUAL:46 BEGIN -->

For each resource, admissible total demand is bounded by the measured qualified capacity surviving the selected failure, less the operational reserve for that same scenario. Existing commitments and the new request must be compared on the same units and accounting basis. Do not subtract a reserve twice if the measured figure already excludes it; do not count an allocation as both reserved and consumed in a total.

<!-- SOURCE-BLOCK QUAL:46 END -->

<!-- SOURCE-BLOCK QUAL:47 BEGIN -->

ILLUSTRATIVE ARITHMETIC — NOT A SIZING RECOMMENDATION — The numbers below are invented for a decision example. They are not measured platform limits, product minimums, approved service commitments or government thresholds.

<!-- SOURCE-BLOCK QUAL:47 END -->

<!-- SOURCE-BLOCK QUAL:48 BEGIN -->


<a id="source-table-48"></a>

| Resource and scenario | Illustrative calculation | Decision for the new request |
| --- | --- | --- |
| Memory; one of three 256 GiB hosts lost | Survivor 512 GiB − 64 GiB operating reserve = 448 GiB admissible. Existing 320 + requested 96 = 416 GiB. | Memory fits, with 32 GiB remaining under this model. Product minima and eligibility still need qualification. |
| Usable storage under selected failure | 20 TiB survivor − 4 TiB reserve = 16 TiB. Existing 12 + requested 3 = 15 TiB. | Capacity fits by 1 TiB; latency/rebuild/backup obligations must also fit. |
| Inspected concurrent sessions under edge failure | 10,000 survivor − 2,000 reserve = 8,000. Existing 7,000 + requested 1,500 = 8,500. | Reject or select another qualified capacity path: 500 sessions above admitted limit. |
| Logical attachment slots | 24 accepted − 16 allocated − 2 reserved − 2 unavailable = 4 available; request needs 4. | Slot count fits, but it cannot override the session-capacity failure. |

<!-- SOURCE-BLOCK QUAL:48 END -->

<!-- SOURCE-BLOCK QUAL:49 BEGIN -->

<!-- SOURCE-BLOCK QUAL:49 END -->

<!-- SOURCE-BLOCK QUAL:50 BEGIN -->

The overall allocation is not accepted because one binding resource fails. Do not build an unprotected partial service, merge contexts or borrow security reserve to make the request succeed. Queue, select another already eligible placement, or expand the foundation through the approved work packages. A reservation is owned and time-bounded so an abandoned request does not strand every scarce resource.

<!-- SOURCE-BLOCK QUAL:50 END -->

<!-- SOURCE-BLOCK QUAL:51 BEGIN -->


<a id="source-table-51"></a>

| Capacity dimension | Measurement and inventory | Growth trigger |
| --- | --- | --- |
| Compute | Eligible CPU/memory reservations, overcommit, actual host/rack survivor and maintenance load. | Forecast demand plus deployment lead time approaches safe envelope. |
| Storage | Usable capacity, copy overhead, rebuild, contention and latency percentiles. | Capacity or performance limit, not only percentage raw disk used. |
| Security edge | Inspection, packets/s, sessions/s, concurrent sessions, NAT ports, logical contexts and logs. | First applicable measured bottleneck under accepted failure. |
| Network and services | Routes, MAC/neighbor state, policy objects, IP/attachment pools, DNS/key/backup/log/API capacity. | Any missing co-requisite prevents new accepted service. |
| Procurement/commissioning | Ordered, received, staged, commissioned, reserved and consumed with age/support owner. | Stranded capacity or late expansion threatens service availability. |

<!-- SOURCE-BLOCK QUAL:51 END -->

<!-- SOURCE-BLOCK QUAL:52 BEGIN -->

<!-- SOURCE-BLOCK QUAL:52 END -->

<!-- SOURCE-BLOCK QUAL:53 BEGIN -->

Showback can attribute scarce dedicated hosts, retained backup capacity, inspected edge use and inter-site movement to the offered service. Cost calculations and claimed savings require actual inventory and rates; no savings are inferred from the reference topology. Capacity reporting should identify why purchased resources cannot yet be consumed, including missing licences, network attachments, staff, storage or protection integration.

<!-- SOURCE-BLOCK QUAL:53 END -->

<!-- SOURCE-BLOCK QUAL:54 BEGIN -->

Related engineering: [Attachment units](../../engineering/fabric/2-isolated-attachment-units-and-bounded-capacity.md#NET_s_002)  •  [Performance/failure observations](../../engineering/fabric/5-mtu-performance-and-failure-engineering.md#NET_s_005)

<!-- SOURCE-BLOCK QUAL:54 END -->

[Previous chapter](2-site-low-level-design-and-dependency-schedule.md) · [Chapter index](README.md) · [Next chapter](4-service-parameter-and-requirement-decisions.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0004 — Scale through commissioned hosting cells and capacity pools](../../adr/0004-scale-through-commissioned-hosting-cells-and-capacity-pools.md)
- [ADR-0030 — Admit demand against every surviving-capacity bottleneck](../../adr/0030-admit-demand-against-every-surviving-capacity-bottleneck.md)

<!-- END GENERATED DECISION LINKS -->
