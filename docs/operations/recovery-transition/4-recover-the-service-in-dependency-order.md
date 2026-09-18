# 4. Recover the service in dependency order

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/03_Implementation/Operations_Recovery_and_Transition_Playbook.docx) · [Chapter index](README.md)

> **Source:** OPS — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: d935614ed1639f56859dfe29bc226af4cfced35bafeb7d544440577ddaa95a09 -->
<a id="OPS_04"></a>

Recovery begins with authority and trusted access, not with powering on every available copy of a VM.

Design basis and related records: [SVC §6](../../architecture/shared-services/6-failure-recovery-migration-and-failback-topology.md#SVC_s_006)  •  [RA §27](../../architecture/reference/27-recovery-migration-and-retirement.md#RA_s_027)  •  [IT §5](../../templates/implementation-mop/5-recovery-exercise-and-data-acceptance.md#IT_05)


<a id="source-table-48"></a>

| Recovery stage | Required action | Exit observation |
| --- | --- | --- |
| 1. Establish authority | Declare scope and recovery owner; preserve evidence and prevent ambiguous concurrent writers. | The selected data/service recovery point and writer authority are explicit. |
| 2. Recover minimum trust | Establish approved management/OOB, name/time/identity and access to protected keys and recovery material. | Recovery does not depend solely on the failed encrypted or management platform. |
| 3. Rebuild foundations | Recover accepted configuration, inventory/state, transport, storage and platform control; then denied security and service paths. | Actual resources, support tuple, routes, quorum and shared dependencies match the recovery design. |
| 4. Restore isolated service | Recover owned data, images and required identities/services into eligible domains. | Useful consistency markers, valid credentials/keys and permitted/denied paths are verified. |
| 5. Activate and observe | Obtain required acceptance, switch approved service access and observe the live path. | Writer control, service outcome and achieved recovery targets are recorded. |
| 6. Stabilize and plan return | Re-establish protection, reconcile emergency grants, and plan failback separately. | No temporary path or stale privilege remains without an accountable approved lifetime. |

An isolated restore may reveal compromised configuration, missing keys, stale identities or an unusable consistency point. Keep the result restricted until the responsible owners resolve those conditions. A successful file read is not application acceptance; the service/data owner supplies meaningful restored-state checks.

Avoid recovery loops: the only key to unlock storage cannot be stored only on that locked storage; the sole backup catalogue cannot be reachable only through a destroyed controller. Record a tested dependency cut and custodial recovery method, without publishing secrets in the kit.

Continue with: [OPS §5](5-calculate-the-recovery-critical-path-and-data-point.md#OPS_05)  •  [QCP §5](../../assurance/qualification-campaign/5-separate-safe-failure-service-continuity-and-recovery.md#QCP_05)

[Previous chapter](3-run-maintenance-and-recover-interrupted-changes.md) · [Chapter index](README.md) · [Next chapter](5-calculate-the-recovery-critical-path-and-data-point.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0031 — Discover uncertain native outcomes instead of blind replay or rollback](../../adr/0031-discover-uncertain-native-outcomes-instead-of-blind-replay-or-rollback.md)

<!-- END GENERATED DECISION LINKS -->
