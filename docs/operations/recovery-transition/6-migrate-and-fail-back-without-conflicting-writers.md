# 6. Migrate and fail back without conflicting writers

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/03_Implementation/Operations_Recovery_and_Transition_Playbook.docx) · [Chapter index](README.md)

> **Source:** OPS — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: d935614ed1639f56859dfe29bc226af4cfced35bafeb7d544440577ddaa95a09 -->
<a id="OPS_06"></a>

Provisioning target infrastructure and transferring existing workload state are separate activities with separate owners.

Design basis and related records: [RA §27](../../architecture/reference/27-recovery-migration-and-retirement.md#RA_s_027)  •  [PROV §6](../../implementation/provisioning-strategy/6-brownfield-adoption-growth-and-retirement.md#PROV_s_006)  •  [QCP §7](../../assurance/qualification-campaign/7-compare-vendor-realizations-without-assuming-migration.md#QCP_07)


<a id="source-table-69"></a>

| Transition stage | Controlled work | Decision before proceeding |
| --- | --- | --- |
| Discover and prepare | Map current data, drivers/boot, virtual devices, identity/keys, network dependencies and accepted target. | The target supports the required service and recoverable data format; unresolved extensions are explicit. |
| Transfer under bounded access | Use the approved capture/transfer method, scoped temporary route/policy and integrity checks. | Data consistency method, bandwidth/window, authority and cleanup owner are accepted. |
| Final consistency and writer change | Select final data point; control old writers; validate target state and service dependencies. | One attributable writer authority exists before target production writes. |
| Cut over and observe | Change only approved DNS/exposure/service access; verify the actual client path and protection. | Operating owner accepts current evidence and the point at which simple rollback ceases to be safe. |
| Return or retire | Reconcile new writes before failback; otherwise retire the source under retention policy. | Reverse synchronization/recovery is supported; old data is not restarted as a competing current copy. |

Before target writes, return to the source may be possible if the original state and authority remain valid. After target writes, restarting the old copy can lose or fork data. The runbook identifies that point of no simple rollback and the required reverse transfer or recovery process. “Rollback” must state its data implications.

Temporary cross-domain transfer access is time-bound and reviewed. Persistent vendor live-mobility and storage-replication transports remain provider infrastructure with their own controlled membership; they are not recreated for each migration just to satisfy a temporary-access rule.

A composite service actively using several stacks is a distinct architecture. Account for cross-stack latency, security edges, identity, shared-service loss and ownership before claiming it provides the same resilience as one bounded cell.

Continue with: [OPS §7](7-retire-live-service-separately-from-retained-data.md#OPS_07)  •  [IT §8](../../templates/implementation-mop/8-migration-retirement-and-retained-data.md#IT_08)

[Previous chapter](5-calculate-the-recovery-critical-path-and-data-point.md) · [Chapter index](README.md) · [Next chapter](7-retire-live-service-separately-from-retained-data.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0033 — Separate live-service retirement from retained-data disposal](../../adr/0033-separate-live-service-retirement-from-retained-data-disposal.md)

<!-- END GENERATED DECISION LINKS -->
