# 26. Operating model, capacity and observability

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/00_Reference_Architecture_v1_4.docx) · [Chapter index](README.md)

> **Source:** RA — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: e50894d7f7b87cef50a283399b85925c8a96c5b9cd0428ce71ca0143d9be8d19 -->
<a id="__RefHeading___Toc3690_865363315"></a>
<a id="RA_s_026"></a>

Operations are organized around delivered services and shared infrastructure boundaries. Network engineering owns transport and physical attachment authority; platform engineering owns qualified vendor capacity; security-edge operations owns boundary realization; storage, identity, backup and logging teams own their services. The tenant service owner supplies workload requirements, acceptance and data obligations. The provisioning service coordinates these responsibilities rather than acquiring all their privileges.

A managed service may transfer guest or application operational tasks to the provider, but the responsibility is explicit. The architecture supplies compute, network, storage and declared service controls; it does not claim to prove application business logic or record-level authorization. Guest patching, application secrets, consistency and restored-data acceptance need a named owner. Unresolved mandatory responsibilities prevent handover.


<a id="source-table-367"></a>

| Operating measure | Required distinction or action |
| --- | --- |
| Capacity | Separate ordered, staged, commissioned, available, reserved and consumed capacity; record stranded capacity and its cause |
| Performance | Measure compute/storage/edge/service paths with realistic load and enabled security features, including the agreed failure |
| Quota and noisy neighbours | Apply accountable tenant limits and reservations across compute, data, routes, sessions, logs and APIs |
| Health | Distinguish platform/control availability, data-path enforcement and workload service health |
| Change and support | Track actual versions, configuration ownership, support expiry, maintenance and known limitations |
| Evidence and incidents | Correlate domain/workload identity with policy, route, storage, identity and privileged-action records |

The capacity plan uses measured surviving capability rather than nominal installed totals. Edge sizing includes packets per second, new and concurrent sessions, inspection cost, NAT-port pressure where applicable, logical-context limits and logging. Storage sizing includes rebuild and retained-copy load. Provider API rate limits and address/attachment pool exhaustion are operational bottlenecks too. Expansion is forecast before the service breaches its safe admission limit.

Collect independently attributable infrastructure evidence: privileged operations, configuration changes, route and domain membership, endpoint policy decisions, data-copy operations, key use, backup administration and provisioning execution. Log time and receipt time support correlation when a source clock is unreliable. Stable tenant/WSD/domain identifiers are more useful than names that change during reorganization or migration. The organizational logging baseline governs centralized collection and access. \[[S11](34-appendix-d-sources-and-review-status.md#RA_src_S11)\]

Logging is not unlimited payload collection. Apply classification, minimization, tenant-scoped access, integrity and retention. Define buffering, loss indication and safe operating behaviour when central collection is unavailable. Monitoring the ZIP from within the compromised tenant alone is not independent enforcement evidence. The reference prefers service-health and policy-path checks that do not require exposing management interfaces to workloads.

Handover includes the as-built topology, owner/escalation, service parameters, failure dependencies, recovery procedures, access model, backup and key custody, capacity limits, monitoring, support status and active exceptions. The service owner accepts the actual delivered envelope rather than a generic claim that the Terraform run was successful.

Related engineering: [QUAL §3 — Capacity, service envelopes and growth triggers](../../assurance/site-qualification/3-capacity-service-envelopes-and-growth-triggers.md#QUAL_s_003)  •  [QUAL §7 — Operating accountability, handover and change](../../assurance/site-qualification/7-operating-accountability-handover-and-change.md#QUAL_s_007)

[Previous chapter](25-change-brownfield-adoption-and-configuration-ownership.md) · [Chapter index](README.md) · [Next chapter](27-recovery-migration-and-retirement.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0030 — Admit demand against every surviving-capacity bottleneck](../../adr/0030-admit-demand-against-every-surviving-capacity-bottleneck.md)
- [ADR-0034 — Classify change by architectural impact rather than file location](../../adr/0034-classify-change-by-architectural-impact-rather-than-file-location.md)
- [ADR-0037 — Define independent telemetry and collection-loss behaviour](../../adr/0037-define-independent-telemetry-and-collection-loss-behaviour.md)

<!-- END GENERATED DECISION LINKS -->
