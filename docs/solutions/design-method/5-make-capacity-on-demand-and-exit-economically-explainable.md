# 5. Make capacity-on-demand and exit economically explainable

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/01_Architecture/Service_Design_and_Decision_Development.docx) · [Chapter index](README.md)

> **Source:** SDP — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 133c2512e904737c1f410106fd1b421fba8309965af0621785b250402fb9214e -->
<!-- SOURCE-BLOCK SDP:56 BEGIN -->

<a id="SDP_05"></a>

<!-- SOURCE-BLOCK SDP:56 END -->

<!-- SOURCE-BLOCK SDP:57 BEGIN -->

Capacity is consumable only when the whole offered service can be delivered inside its failure and security constraints.

<!-- SOURCE-BLOCK SDP:57 END -->

<!-- SOURCE-BLOCK SDP:58 BEGIN -->

Design basis and related records: [RA §4](../../architecture/reference/4-hosting-cells-resource-pools-and-failure-boundaries.md#RA_s_004)  •  [RA §26](../../architecture/reference/26-operating-model-capacity-and-observability.md#RA_s_026)  •  [QUAL §3](../../assurance/site-qualification/3-capacity-service-envelopes-and-growth-triggers.md#QUAL_s_003)  •  [AK §5](../../architecture/delivery-guide/5-service-resilience-capacity-and-portability.md#AK_05)

<!-- SOURCE-BLOCK SDP:58 END -->

<!-- SOURCE-BLOCK SDP:59 BEGIN -->

Keep ordered, received, staged, commissioned, available, reserved, consumed and retiring capacity distinct. A purchased server without accepted transport, storage, edge slots, entitlement or operating ownership is not service-ready capacity. A tenant quota limits consumption rights; it is not proof that the provider can honour every concurrent request.

<!-- SOURCE-BLOCK SDP:59 END -->

<!-- SOURCE-BLOCK SDP:60 BEGIN -->


<a id="source-table-60"></a>

| Decision | Engineering consequence | Operating record |
| --- | --- | --- |
| Reserve for the covered failure | Calculate demand against surviving qualified capacity in each limiting unit. | Track compute, storage, sessions, inspected throughput, address pools and dependency limits separately. |
| Expand before exhaustion | Use actual procurement, staging, commissioning and qualification lead time. | Record the trigger, owner, forecast confidence and time to usable service—not only delivery date. |
| Charge or show service consumption | State the unit, period and boundary; separate dedicated scope and protection retention. | Do not disguise idle stock or duplicate reservations as consumed tenant capacity. |
| Maintain a viable exit | Include target capacity, copy volume, conversion, downtime, skills and retained obligations. | Rehearsal evidence distinguishes deployment portability from successful data/service recovery. |

<!-- SOURCE-BLOCK SDP:60 END -->

<!-- SOURCE-BLOCK SDP:61 BEGIN -->

<!-- SOURCE-BLOCK SDP:61 END -->

<!-- SOURCE-BLOCK SDP:62 BEGIN -->

A local cost model can separate shared fixed service costs, metered resource consumption, retained-copy costs and dedicated isolation costs. No rates or savings are asserted here. Record assumptions and measurement periods before using the model to justify consolidation or replacement.

<!-- SOURCE-BLOCK SDP:62 END -->

<!-- SOURCE-BLOCK SDP:63 BEGIN -->

The next commitment decision is therefore not “which stack has free CPU?” It is “which eligible service envelope has enough surviving capacity, current support, accepted dependencies and a usable exit path?”

<!-- SOURCE-BLOCK SDP:63 END -->

<!-- SOURCE-BLOCK SDP:64 BEGIN -->

Continue with: [NBD §7](../../engineering/network-boundaries/7-release-the-network-design-under-an-explicit-failure-model.md#NBD_07)  •  [OPS §5](../../operations/recovery-transition/5-calculate-the-recovery-critical-path-and-data-point.md#OPS_05)

<!-- SOURCE-BLOCK SDP:64 END -->

<!-- SOURCE-BLOCK SDP:65 BEGIN -->

<!-- SOURCE-BLOCK SDP:65 END -->

[Previous chapter](4-turn-dependencies-into-explicit-service-interfaces.md) · [Chapter index](README.md) · [Next chapter](6-release-the-architecture-as-an-accountable-engineering-contract.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0030 — Admit demand against every surviving-capacity bottleneck](../../adr/0030-admit-demand-against-every-surviving-capacity-bottleneck.md)

<!-- END GENERATED DECISION LINKS -->
