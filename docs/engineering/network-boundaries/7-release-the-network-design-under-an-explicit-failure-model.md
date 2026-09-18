# 7. Release the network design under an explicit failure model

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/02_Engineering/Network_and_Boundary_Detailed_Engineering.docx) · [Chapter index](README.md)

> **Source:** NBD — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 7a86351d7f4be320e48d3112485bbab4b0f5b4a79cd0e420a823c793a708733a -->
<!-- SOURCE-BLOCK NBD:79 BEGIN -->

<a id="NBD_07"></a>

<!-- SOURCE-BLOCK NBD:79 END -->

<!-- SOURCE-BLOCK NBD:80 BEGIN -->

Security continuity and availability are separate acceptance dimensions. A denied unauthorized flow may be correct while an allowed flow’s outage still fails the service target.

<!-- SOURCE-BLOCK NBD:80 END -->

<!-- SOURCE-BLOCK NBD:81 BEGIN -->

Design basis and related records: [NET §6](../fabric/6-management-paths-and-interface-handover.md#NET_s_006)  •  [QUAL §3](../../assurance/site-qualification/3-capacity-service-envelopes-and-growth-triggers.md#QUAL_s_003)  •  [QCP §5](../../assurance/qualification-campaign/5-separate-safe-failure-service-continuity-and-recovery.md#QCP_05)

<!-- SOURCE-BLOCK NBD:81 END -->

<!-- SOURCE-BLOCK NBD:82 BEGIN -->


<a id="source-table-82"></a>

| Failure or change | Secure design expectation | Separate service evidence |
| --- | --- | --- |
| One edge member or uplink lost | No uninspected backup route or implicit permit; approved state handling remains enforced. | Established and new-session interruption, surviving load and convergence against the adopted target. |
| Routing or attachment inconsistency | Unverified endpoints remain restricted; no temporary shared transit to finish commissioning. | Which dependent services are unavailable and how the correct path is restored. |
| Service-side return path lost | Do not use another tenant context as a generic fallback. | Loss scope, detection, safe repair and successful post-repair replies. |
| Management or telemetry loss | No new privilege or permit path; invoke the approved access/logging loss policy. | Existing operation, buffers, evidence gaps and recoverability of the required control. |

<!-- SOURCE-BLOCK NBD:82 END -->

<!-- SOURCE-BLOCK NBD:83 BEGIN -->

<!-- SOURCE-BLOCK NBD:83 END -->

<!-- SOURCE-BLOCK NBD:84 BEGIN -->

A proposed capacity example illustrates the release decision. If surviving inspected capacity is 8 Gbit/s, an explicitly defined operating reserve is 1.5 Gbit/s, and existing commitment is 5.5 Gbit/s, only 1 Gbit/s remains for new demand. A 1.2 Gbit/s request is 0.2 Gbit/s above that bound even when compute is available. These are local example values, not product benchmarks.

<!-- SOURCE-BLOCK NBD:84 END -->

<!-- SOURCE-BLOCK NBD:85 BEGIN -->

Repeat admission for packets per second, sessions, route/context limits, NAT ports where used, log rate and service dependencies. Do not add unlike units or subtract commitments twice. The actual engineering record uses measured sustained performance with enabled security features under the selected failure/load scenario.

<!-- SOURCE-BLOCK NBD:85 END -->

<!-- SOURCE-BLOCK NBD:86 BEGIN -->

Release stops when any mandatory path, return route, limit, owner or observation is unresolved. Intrusive testing requires a separately authorized scope and restoration procedure.

<!-- SOURCE-BLOCK NBD:86 END -->

<!-- SOURCE-BLOCK NBD:87 BEGIN -->

Continue with: [QCP §5](../../assurance/qualification-campaign/5-separate-safe-failure-service-continuity-and-recovery.md#QCP_05)  •  [OPS §2](../../operations/recovery-transition/2-specify-dependency-loss-before-it-becomes-an-incident.md#OPS_02)

<!-- SOURCE-BLOCK NBD:87 END -->

[Previous chapter](6-issue-an-interface-control-and-handoff-record.md) · [Chapter index](README.md)
