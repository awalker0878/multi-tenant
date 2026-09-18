# 2. Specify dependency loss before it becomes an incident

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/03_Implementation/Operations_Recovery_and_Transition_Playbook.docx) · [Chapter index](README.md)

> **Source:** OPS — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: d935614ed1639f56859dfe29bc226af4cfced35bafeb7d544440577ddaa95a09 -->
<!-- SOURCE-BLOCK OPS:26 BEGIN -->

<a id="OPS_02"></a>

<!-- SOURCE-BLOCK OPS:26 END -->

<!-- SOURCE-BLOCK OPS:27 BEGIN -->

Loss behaviour is different for established traffic, new operations and recovery. Record all three using the actual supported implementation.

<!-- SOURCE-BLOCK OPS:27 END -->

<!-- SOURCE-BLOCK OPS:28 BEGIN -->

Design basis and related records: [RA §14](../../architecture/reference/14-availability-multi-site-operation-and-recovery-topology.md#RA_s_014)  •  [SVC §6](../../architecture/shared-services/6-failure-recovery-migration-and-failback-topology.md#SVC_s_006)  •  [IK §8](../../implementation/delivery-guide/8-interrupted-work-brownfield-adoption-and-change.md#IK_08)

<!-- SOURCE-BLOCK OPS:28 END -->

<!-- SOURCE-BLOCK OPS:29 BEGIN -->


<a id="source-table-29"></a>

| Dependency loss | Existing / new operation | Recovery and authority condition |
| --- | --- | --- |
| Platform manager or runner | Existing data plane follows the qualified behaviour; new uncertain changes pause. | Discover accepted native tasks before restart. Do not infer that a timed-out action stopped. |
| IPAM / naming | Existing addresses and records follow their accepted lease/continuity policy; no guessed new allocation. | Restore authoritative history and reconcile reservations, DNS and actual resources before reuse. |
| Identity / privileged access | No automatic unrestricted local-account fallback for new administrative work. | Use the approved scoped emergency path; retain logs and revoke recovery grants after use. |
| KMS / certificate trust | Running access, cached keys and restart behaviour follow measured scope; no plaintext fallback. | Recover authorized keys/trust independently of resources that require them; preserve retained-copy access. |
| Logging / evidence collection | Enforcement remains; buffering and loss alerts follow the selected profile. | Record missing intervals and apply approved operating restrictions, rather than fabricate complete logs. |
| Storage, edge or site partition | Fail-safe enforcement and writer control precede any promotion or alternate path. | Select the authorized survivor/restore scope; verify capacity, consistency and current policy. |

<!-- SOURCE-BLOCK OPS:29 END -->

<!-- SOURCE-BLOCK OPS:30 BEGIN -->

<!-- SOURCE-BLOCK OPS:30 END -->

<!-- SOURCE-BLOCK OPS:31 BEGIN -->

For each dependency record a named recovery owner, invocation conditions, observable safe state, local evidence location, dependent services and the point at which fresh acceptance is needed. A common identity or key service can couple otherwise separate sites; different site labels do not remove that dependency.

<!-- SOURCE-BLOCK OPS:31 END -->

<!-- SOURCE-BLOCK OPS:32 BEGIN -->

“Fail closed” does not mean destroy workloads or data. It means unavailable authority must not create new permission or bypass. Existing-service continuity follows the approved control and risk conditions.

<!-- SOURCE-BLOCK OPS:32 END -->

<!-- SOURCE-BLOCK OPS:33 BEGIN -->

Continue with: [QCP §5](../../assurance/qualification-campaign/5-separate-safe-failure-service-continuity-and-recovery.md#QCP_05)  •  [OPS §4](4-recover-the-service-in-dependency-order.md#OPS_04)

<!-- SOURCE-BLOCK OPS:33 END -->

<!-- SOURCE-BLOCK OPS:34 BEGIN -->

<!-- SOURCE-BLOCK OPS:34 END -->

[Previous chapter](1-operate-service-outcomes-rather-than-isolated-components.md) · [Chapter index](README.md) · [Next chapter](3-run-maintenance-and-recover-interrupted-changes.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0029 — Keep recovery trust material independent of the platform it unlocks](../../adr/0029-keep-recovery-trust-material-independent-of-the-platform-it-unlocks.md)
- [ADR-0032 — Keep incident containment above routine reconciliation](../../adr/0032-keep-incident-containment-above-routine-reconciliation.md)

<!-- END GENERATED DECISION LINKS -->
