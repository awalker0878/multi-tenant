# 4. Turn dependencies into explicit service interfaces

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/01_Architecture/Service_Design_and_Decision_Development.docx) · [Chapter index](README.md)

> **Source:** SDP — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 133c2512e904737c1f410106fd1b421fba8309965af0621785b250402fb9214e -->
<!-- SOURCE-BLOCK SDP:46 BEGIN -->

<a id="SDP_04"></a>

<!-- SOURCE-BLOCK SDP:46 END -->

<!-- SOURCE-BLOCK SDP:47 BEGIN -->

A dependency is not complete until its consumer, producer, permitted operation, failure effect and recovery owner are identified.

<!-- SOURCE-BLOCK SDP:47 END -->

<!-- SOURCE-BLOCK SDP:48 BEGIN -->

Design basis and related records: [RA §9](../../architecture/reference/9-shared-services-ingress-and-controlled-egress.md#RA_s_009)  •  [RA §13](../../architecture/reference/13-identity-cryptography-and-service-trust.md#RA_s_013)  •  [SVC §1](../../architecture/shared-services/1-shared-service-placement-and-consumption-boundaries.md#SVC_s_001)  •  [EK §5](../../engineering/delivery-guide/5-management-and-shared-service-interfaces.md#EK_05)

<!-- SOURCE-BLOCK SDP:48 END -->

<!-- SOURCE-BLOCK SDP:49 BEGIN -->


<a id="source-table-49"></a>

| Actual consumer | Consumed function | Separate authority / failure question |
| --- | --- | --- |
| Guest resolver client | Approved DNS endpoint and required transports. | Who administers resolver policy, supplies the reply path and recovers name service? |
| Host or storage service | Key use needed for encrypted storage or restart. | Is key recovery independent of the encrypted resources it must unlock? Do not invent a guest KMS flow. |
| Backup executor / data mover | Scoped capture API and the selected data-transfer path. | Which identity can delete retained copies or reduce protection? Which catalogue and keys survive a primary loss? |
| Infrastructure administrator | Management API or controlled hardware recovery. | Which protected origin, target scope and emergency authority apply? Workload reachability does not grant this authority. |

<!-- SOURCE-BLOCK SDP:49 END -->

<!-- SOURCE-BLOCK SDP:50 BEGIN -->

<!-- SOURCE-BLOCK SDP:50 END -->

<!-- SOURCE-BLOCK SDP:51 BEGIN -->

For each row supply the producer’s accepted service statement: endpoint identity, consumed resource scope, protocol/authentication profile, capacity and limits, loss behaviour, supported versions, change notification, recovery ownership and acceptance evidence. The consumer receives the facts it needs, not the producer’s administrator credential or full state file.

<!-- SOURCE-BLOCK SDP:51 END -->

<!-- SOURCE-BLOCK SDP:52 BEGIN -->

Record location constraints separately for live data, copies, telemetry, diagnostics, management, support access and keys. The architecture enforces decisions supplied by the responsible authorities; a site name or private circuit is not a substitute for those decisions. Shared endpoint addresses also do not prove independent service backends.

<!-- SOURCE-BLOCK SDP:52 END -->

<!-- SOURCE-BLOCK SDP:53 BEGIN -->

Handoff quality test: the dependent team can explain what stops, what continues and who can restore the service when this producer is unavailable.

<!-- SOURCE-BLOCK SDP:53 END -->

<!-- SOURCE-BLOCK SDP:54 BEGIN -->

Continue with: [PBS §8](../../engineering/platform-build/8-publish-shared-service-handoffs-without-sharing-authority.md#PBS_08)  •  [OPS §2](../../operations/recovery-transition/2-specify-dependency-loss-before-it-becomes-an-incident.md#OPS_02)

<!-- SOURCE-BLOCK SDP:54 END -->

<!-- SOURCE-BLOCK SDP:55 BEGIN -->

<!-- SOURCE-BLOCK SDP:55 END -->

[Previous chapter](3-develop-a-boundary-architecture-decision.md) · [Chapter index](README.md) · [Next chapter](5-make-capacity-on-demand-and-exit-economically-explainable.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0010 — Expose shared services through scoped consumption endpoints](../../adr/0010-expose-shared-services-through-scoped-consumption-endpoints.md)

<!-- END GENERATED DECISION LINKS -->
