# 51. Capacity, performance and capacity-on-demand operations

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Handbook_v1_1.docx) · [Chapter index](README.md)

> **Source:** HB11 — Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: afbe9313dda4c68d5bb3af9ae6e9fcb5f098894c59e5f443270795bf2f9c21a1 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
<a id="__RefHeading___Toc13397_1645000677"></a>
<a id="sec_51"></a>

Size the entire service path, not only aggregate switch bandwidth. Admission depends on compute memory/CPU, storage usable capacity and latency, failure/rebuild reserve, edge throughput and sessions, inspection cost, route/policy object limits, IP pools, service endpoint limits, log ingestion/retention and controller/API concurrency. Measure with the enabled security feature set and realistic packet sizes, session churn and workload mix. An uninspected throughput figure is not evidence for an inspected production edge.

For each bottleneck, compare demand after the specified failure with the measured sustainable capacity remaining after that failure. A useful local model is admissibleDemand &lt;= survivingQualifiedCapacity - operationalReserve. Reserve includes rebuild/rebalance, maintenance, migration, forecast growth and uncertainty as applicable; avoid counting the same capacity twice. The profile defines which simultaneous failures or maintenance conditions are covered. “N+1” without a named failure model and recovery-load measurement is incomplete.


<a id="source-table-693"></a>

| Capacity object | Admission and operating evidence |
| --- | --- |
| Compute | Usable memory/CPU after host or rack loss; reservation/oversubscription policy; anti-affinity and evacuation capacity |
| Storage | Usable rather than raw capacity; replicas/erasure overhead, snapshots/backup, rebuild reserve, IOPS/latency and failure testing |
| Security edge | Throughput, packets/s, connections/s, concurrent sessions, NAT ports, inspection and per-context quotas under failure |
| Network/control | Prefixes, routes, VNIs, MAC/ARP/ND, policy objects, API rate limits, IPAM and runner concurrency |
| Shared services | DNS/identity/KMS/backup/logging endpoint capacity, saturation behavior and tenant attribution |
| Procurement/inventory | Ordered, received, installed, commissioned, allocated and consumed capacity; aging stock and deployment constraints |

Deliver standard services from shared qualified capacity, with quotas and accountable reservations rather than routinely purchasing isolated infrastructure per application project. Forecast expansion against deployment lead time and use phased procurement. Report unused procured capacity and why it is not commissioned or consumable. Procurement cost, installed capacity, allocation and actual consumption are different measures; showback must not disguise idle stock as delivered service.

<a id="req_CAP_001"></a>

CAP-001  Capacity planning SHALL include N+failure headroom so that loss of a security-edge node does not require disabling or bypassing enforcement.

Capacity management  \|  Verify: [CT-012](73-appendix-d-conformance-test-catalogue.md#test_CT_012), [CT-056](73-appendix-d-conformance-test-catalogue.md#test_CT_056)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  retained-v1.0

<a id="req_CAP_002"></a>

CAP-002  Placement and growth admission SHALL evaluate measured surviving capacity, security-feature overhead, shared dependencies, quotas and operational reserves for the approved failure model.

Capacity management  \|  Verify: [CT-039](73-appendix-d-conformance-test-catalogue.md#test_CT_039), [CT-047](73-appendix-d-conformance-test-catalogue.md#test_CT_047), [CT-056](73-appendix-d-conformance-test-catalogue.md#test_CT_056)  \|  Basis: [S00](77-appendix-h-primary-sources-and-implementation-references.md#S00)  \|  new-v1.1

<a id="req_CAP_003"></a>

CAP-003  Capacity reporting SHALL distinguish procured, received, commissioned, allocated, reserved and consumed capacity and identify unused-capacity age, constraints and accountable remediation.

Service management  \|  Verify: [CT-074](73-appendix-d-conformance-test-catalogue.md#test_CT_074)  \|  Basis: [S28](77-appendix-h-primary-sources-and-implementation-references.md#S28)  \|  new-v1.1

[Previous chapter](50-logging-telemetry-and-time-integrity.md) · [Chapter index](README.md) · [Next chapter](52-high-availability-and-dependency-failure-behavior.md)
