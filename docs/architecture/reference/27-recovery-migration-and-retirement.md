# 27. Recovery, migration and retirement

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/00_Reference_Architecture_v1_4.docx) · [Chapter index](README.md)

> **Source:** RA — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: e50894d7f7b87cef50a283399b85925c8a96c5b9cd0428ce71ca0143d9be8d19 -->
<!-- SOURCE-BLOCK RA:374 BEGIN -->

<a id="__RefHeading___Toc3692_865363315"></a>
<a id="RA_s_027"></a>

<!-- SOURCE-BLOCK RA:374 END -->

<!-- SOURCE-BLOCK RA:375 BEGIN -->

## Recovery and incident containment

<!-- SOURCE-BLOCK RA:375 END -->

<!-- SOURCE-BLOCK RA:376 BEGIN -->

Containment is scoped to the affected workload, domain, service binding, external exposure or platform capability. Use the narrowest effective boundary while checking dependencies such as identity, DNS, logging and backup. The incident authority can suspend ordinary provisioning, isolate endpoints or withdraw exposure without redesigning the physical fabric. Emergency blocks remain effective until explicitly released and reconciled into the approved configuration.

<!-- SOURCE-BLOCK RA:376 END -->

<!-- SOURCE-BLOCK RA:377 BEGIN -->

Recovery begins by selecting authority and fencing ambiguous writers. Restore trusted OOB/management and minimum identity/time/name/key access, then source/configuration/state/catalogue records, then fabric/platform/storage and security services. Recover data and workloads into authorized isolated target domains. Validate integrity, consistency, required services and security before changing production exposure. Record achieved RTO/RPO and any exclusions rather than equating a completed VM restore with a recovered service.

<!-- SOURCE-BLOCK RA:377 END -->

<!-- SOURCE-BLOCK RA:378 BEGIN -->

## Cross-platform migration

<!-- SOURCE-BLOCK RA:378 END -->

<!-- SOURCE-BLOCK RA:379 BEGIN -->

A migration builds the target infrastructure from the same hosting requirements using the target stack’s realization. It then transfers data and workload state through an explicitly approved temporary connection. Guest drivers, firmware/boot mode, virtual security devices, storage format, application consistency, identity, certificates, keys, DNS, backup and operating procedures are all checked. Terraform creates target resources and connectivity; specialized transfer, conversion or application recovery tooling moves state.

<!-- SOURCE-BLOCK RA:379 END -->

<!-- SOURCE-BLOCK RA:380 BEGIN -->

The cutover establishes a final consistency point, prevents conflicting writers, verifies the target, changes service access and observes stability. A rollback after writes on the target may require reverse synchronization or another recovery operation; it is not necessarily safe to start the old VM. Temporary transfer access expires or is explicitly converted into an approved steady-state service. Live migration within a vendor pool remains separate from this cross-platform transition.

<!-- SOURCE-BLOCK RA:380 END -->

<!-- SOURCE-BLOCK RA:381 BEGIN -->


<a id="source-table-381"></a>

| Lifecycle phase | Completion condition |
| --- | --- |
| Target preparation | Eligible pools, domains, service bindings, keys and protection exist under deny |
| Transfer and consistency | Approved source/target scopes, integrity checks, defined data-consistency point and bounded transition access |
| Cutover | Writer fencing, target tests, authorized name/exposure change and operating ownership |
| Stabilize and failback/exit | Measured service behaviour, tested return/exit feasibility and documented residual dependencies |
| Source retirement | No obsolete live routes, policy, credentials or public exposure; retained copies remain explicitly owned |

<!-- SOURCE-BLOCK RA:381 END -->

<!-- SOURCE-BLOCK RA:382 BEGIN -->

<!-- SOURCE-BLOCK RA:382 END -->

<!-- SOURCE-BLOCK RA:383 BEGIN -->

## Retirement and retained data

<!-- SOURCE-BLOCK RA:383 END -->

<!-- SOURCE-BLOCK RA:384 BEGIN -->

Retirement is not a blind Terraform destroy. First identify shared resources, dependent services, required exports/backups and retention holds. Preserve the access needed to satisfy those obligations before withdrawing live service. Remove public and discretionary access, retire workload resources, remove obsolete domain attachments/routes and DNS/DHCP records, revoke identities/certificates/secrets and release addresses through quarantine. Delete a shared domain only when it has no remaining authorized dependents.

<!-- SOURCE-BLOCK RA:384 END -->

<!-- SOURCE-BLOCK RA:385 BEGIN -->

Reconcile snapshots, replicas, backups, caches and key lifetimes. Sanitize only resources approved for reuse or disposal, with method and verification evidence. Retained copies move to an accountable retention scope with their necessary keys and controlled recovery access. Final records distinguish the live service being retired from all data being destroyed. Reusing a name, IP address or disk must not inherit stale authority.

<!-- SOURCE-BLOCK RA:385 END -->

<!-- SOURCE-BLOCK RA:386 BEGIN -->

Periodic recovery and exit exercises validate the architecture across more than one qualified platform. Measure operational effort, downtime, transfer capacity, policy equivalence and unsupported dependencies. Results drive changes to placement, service classes and procurement rather than a claim that an open disk format alone eliminates lock-in.

<!-- SOURCE-BLOCK RA:386 END -->

<!-- SOURCE-BLOCK RA:387 BEGIN -->

Related engineering: [SVC §4 — Storage, copies and retained-data ownership](../shared-services/4-storage-copies-and-retained-data-ownership.md#SVC_s_004)  •  [SVC §6 — Failure, recovery, migration and failback topology](../shared-services/6-failure-recovery-migration-and-failback-topology.md#SVC_s_006)  •  [PROV §6 — Brownfield adoption, growth and retirement](../../implementation/provisioning-strategy/6-brownfield-adoption-growth-and-retirement.md#PROV_s_006)

<!-- SOURCE-BLOCK RA:387 END -->

[Previous chapter](26-operating-model-capacity-and-observability.md) · [Chapter index](README.md) · [Next chapter](28-architecture-acceptance-and-verification.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0012 — Distinguish persistent platform transports from temporary migration access](../../adr/0012-distinguish-persistent-platform-transports-from-temporary-migration-access.md)
- [ADR-0017 — Separate reference adoption, technical qualification and authorization](../../adr/0017-separate-reference-adoption-technical-qualification-and-authorization.md)
- [ADR-0032 — Keep incident containment above routine reconciliation](../../adr/0032-keep-incident-containment-above-routine-reconciliation.md)
- [ADR-0033 — Separate live-service retirement from retained-data disposal](../../adr/0033-separate-live-service-retirement-from-retained-data-disposal.md)

<!-- END GENERATED DECISION LINKS -->
