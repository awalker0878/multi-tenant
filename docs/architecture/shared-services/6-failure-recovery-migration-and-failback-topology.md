# 6. Failure, recovery, migration and failback topology

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/05_Reference_v1_4/05_Shared_Services_Data_and_Recovery_v1_4.docx) · [Chapter index](README.md)

> **Source:** SVC — Draft v1.4. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 2257e6f3badac48b07989244fbfae96643d68cc6633b28e9799a14733bccea3a -->
<a id="__RefHeading___Toc8885_1525915568"></a>
<a id="SVC_s_006"></a>

Parent architecture: [RA §14](../reference/14-availability-multi-site-operation-and-recovery-topology.md#RA_s_014)  •  [RA §27](../reference/27-recovery-migration-and-retirement.md#RA_s_027)

Recovery follows the dependency and authority graph, not just the order in which VMs appear in inventory. Declare the failure scope, prevent ambiguous writers, and establish trusted management before restoring dependent platforms and workloads. A control-plane outage, security-edge outage, storage partition and complete site loss have different effects. The actual versioned implementation must support the claimed behaviour. \[[B2](07-references-parent-basis-and-external-context.md#SVC_src_B2) §§14, 27\]


<a id="source-table-81"></a>

| Failure scenario | Reference secure operating state | Recovery authority and dependency |
| --- | --- | --- |
| Primary management/control lost | No new untracked changes; existing workload behaviour only as proven by the selected stack. | Management owner restores independent trust/access and reconciles native state. |
| Security edge member/path lost | Remaining qualified path enforces policy; otherwise affected traffic fails closed. | Edge owner restores routing/session ownership without introducing a bypass. |
| Storage/network partition | Do not promote a second writer on ambiguous ownership. | Data/platform owner establishes fencing, quorum and selected recoverable state. |
| KMS/identity/name dependency lost | No uncontrolled substitute credentials, plaintext or guessed name/address allocation. | Relevant service owner invokes approved continuity/recovery path. |
| Site lost | Recover in an already authorized target footprint; no emergency route leaking. | Incident/continuity authority coordinates data, trust, platform and exposure owners. |

The dependency order is: authority and writer exclusion; independent console/privileged access and minimum time/name/trust/key access; trusted configuration/state/catalogue recovery; transport/platform/storage baseline; edge and necessary service endpoints under deny; data and endpoints in approved recovery domains; positive/negative and recovered-data acceptance; controlled exposure/name activation; observation and cleanup. Some tasks can run in parallel, but a dependent activation cannot precede its accepted prerequisite.


<a id="source-table-84"></a>

| Migration/failback milestone | Required decision | Unsafe shortcut to exclude |
| --- | --- | --- |
| Target preparation | Same security/service constraints; supported image/data compatibility and enough surviving capacity. | Use an ineligible host or weaker boundary because the target is temporary. |
| Transfer window | Approved endpoints/protocol, consistency method, bandwidth and temporary-access expiry. | A permanent shared migration VRF connecting unrelated domains by default. |
| Final consistency and cutover | Record last recoverable point, exclude old writer, verify target and switch controlled names/exposure. | Assume two independent writable copies are safe because both are reachable. |
| Post-target writes | Data owner decides forward repair, reverse synchronization or another restore. | Revert to stale source by restarting it or restoring an old state file. |
| Failback and cleanup | New consistency point, reverse direction, accepted source health and withdrawal of obsolete access/copies. | Leave temporary keys, routes, permissions or old external endpoints active. |

Persistent hypervisor mobility and storage replication transports may remain after the migration. Temporary cross-domain transfer grants do not. Track these separately in the interface and lifecycle records so cleanup does not break normal platform operation or leave an enduring transition bypass. Measure recovery and exit effort against the service definition; record excluded dependencies and actual breaches honestly.

Related engineering: [Stateful failure paths](../../engineering/fabric/3-worked-inter-zone-routing-and-enforcement-schedule.md#NET_s_003)  •  [Independent bootstrap](../../implementation/provisioning-strategy/2-day-0-and-steady-state-commissioning-without-circular-dependencies.md#PROV_s_002)  •  [Failure and portability qualification](../../assurance/site-qualification/5-qualification-stages-applicability-and-evidence.md#QUAL_s_005)

[Previous chapter](5-backup-capture-independent-protection-and-isolated-restore.md) · [Chapter index](README.md) · [Next chapter](07-references-parent-basis-and-external-context.md)

<!-- BEGIN GENERATED DECISION LINKS -->

## Related decision records

- [ADR-0011 — Default to site-local domains and routed recovery](../../adr/0011-default-to-site-local-domains-and-routed-recovery.md)

<!-- END GENERATED DECISION LINKS -->
