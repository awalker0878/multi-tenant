# 3. Run maintenance and recover interrupted changes

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/03_Implementation/Operations_Recovery_and_Transition_Playbook.docx) · [Chapter index](README.md)

> **Source:** OPS — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: d935614ed1639f56859dfe29bc226af4cfced35bafeb7d544440577ddaa95a09 -->
<a id="OPS_03"></a>

Classify a change by its effects on service, boundaries and data—not by the repository or tool that performs it.

Design basis and related records: [RA §25](../../architecture/reference/25-change-brownfield-adoption-and-configuration-ownership.md#RA_s_025)  •  [PROV §5](../../implementation/provisioning-strategy/5-concurrency-ownership-and-failed-execution.md#PROV_s_005)  •  [IK §8](../../implementation/delivery-guide/8-interrupted-work-brownfield-adoption-and-change.md#IK_08)


<a id="source-table-38"></a>

| Stage | Owner action | Stop or re-evaluate when |
| --- | --- | --- |
| Bound the change | Identify affected native objects, consumers, supported tuple, surviving load and approved window. | Authority is missing, a shared dependency is undisclosed, or recovery is unproven. |
| Freeze artifacts and ownership | Bind the accepted configuration/plan, actual state and credentials to one execution owner. | Another writer changes the target or approval-sensitive input after review. |
| Observe execution | Use supported native completion signals and capture actual side effects. | The response is lost, timeout expires or the executor lease ends without confirmed native completion. |
| Resolve uncertainty | Freeze competing writes; inspect native tasks, resources and data state; choose resume, forward repair or supported compensation. | A delayed task can still complete or compensation might delete shared or newly written data. |
| Reaccept and hand over | Recheck affected controls, capacity and data; record as-built and remaining defects. | Required observations are stale or incident containment has not been explicitly released. |

A prior state snapshot does not revert the actual infrastructure. Similarly, credential revocation may prevent a new API call without cancelling work already accepted by a native system. Record the remaining task and resource identity, then obtain the owning team’s recovery decision before a new execution competes with it.

For brownfield adoption, discover current routes, policies, data attachments, ownership and dependencies first. Review the non-destructive import/adoption scope and remove conflicting writers deliberately. Adoption is not conformance, and it is not permission to replace existing VMs, disks or gateways.

An authorized incident block takes precedence over ordinary configuration reconciliation until the incident authority releases it. Repair must not restore an old allow path merely because it remains in source.

Continue with: [PBS §9](../../engineering/platform-build/9-release-a-native-build-package-that-can-be-independently-reviewed.md#PBS_09)  •  [QCP §5](../../assurance/qualification-campaign/5-separate-safe-failure-service-continuity-and-recovery.md#QCP_05)

[Previous chapter](2-specify-dependency-loss-before-it-becomes-an-incident.md) · [Chapter index](README.md) · [Next chapter](4-recover-the-service-in-dependency-order.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0028 — Protect backup administration and prove isolated usable restore](../../adr/0028-protect-backup-administration-and-prove-isolated-usable-restore.md)

<!-- END GENERATED DECISION LINKS -->
