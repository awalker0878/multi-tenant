# Initial VMware-to-OpenStack route feasibility

This procedure supports P00.04, R01 and G00.04. Its purpose is to decide whether the selected first application can use the preferred application rebuild/restore method and what implementation must prove. It does not qualify a production route. The method decision belongs to ADR-014 in the [decision register](../../decisions/decision-register.md); full native qualification uses [Q07](../campaigns/q07-first-offline-migration.md).

## Candidate and decision boundary

The candidate is the synthetic [Permit Desk](../../product/application-walkthrough.md) application: one Linux web workload, one Linux database workload, database records and attachment data, separate OZ/RZ placements and declared shared-service dependencies. The preferred first method is `application_rebuild_restore`: recreate the application on clean OpenStack resources from pinned artifacts and configuration, then transfer and restore its complete consistently captured state. Final source quiescence/fencing and cutover remain an offline application transition; this does not claim warm or live migration.

This recommendation follows the current P00 method assessment and the user’s 2026-10-04 clarification. It replaces the earlier cold-conversion-first proposal. The old branch’s `REBUILD_RESTORE` driver provides reference information, not inherited implementation, selected versions or qualification. ADR-014 remains `DESIGN` / `PROPOSED` until feasibility and accountable review occur. `cold_guest_disk_conversion_import` remains a separate P09 option for workloads that require whole-VM movement.

Record the source/target installation and enabled backends; source/target guest and application/database runtimes; reproducible deployment artifacts; datasets, volume/mount mappings and consistency requirements; configuration and secret references; network/service dependencies; staging and retained-source requirements. Unknown fields remain open feasibility inputs. A running target VM or successful backup command is insufficient to freeze this tuple.

## Inputs and responsibilities

| Input | Required content | Accountable role |
| --- | --- | --- |
| Native facts | Read-only inventory, installed/API/backend versions, source VM/resource identities, target project/topology, required guest/device properties and permitted effects | VMware/OpenStack platform owners |
| Rebuild definition | Pinned guest/application/dependency artifacts, deployment procedure, configuration/secret references, service/identity treatment and database compatibility | Application/guest owners |
| Application fixture | Dataset/writer manifest, database-aware consistent capture, attachment/metadata treatment, correctness queries and business-effect suppression | Application/data owner |
| Authority scope | Permitted reads, isolated fixture changes, resource limits, endpoints, campaign stop, source fencing and cleanup authority | Platform and security owners |
| Acceptance measures | Allowed outage/data loss, measured deployment/transfer/restore budgets, target readiness and recovery conditions | Application and SRE owners |
| Independent review | Observer access, current writer exclusion and evidence custody, including captured data/configuration and key restrictions | Qualification and security leads |

## Assessment sequence

1. Inventory every application component, dataset, configuration dependency, identity, scheduled task and external writer. Reconcile the logical manifest to source/native identities and explain unmatched or shared resources.
2. Reproduce the application from pinned artifacts on a clean isolated target. Verify selected guest/application/database versions and required libraries, configuration, certificates, service accounts and mounts. Identify any undocumented state that prevents a reliable rebuild.
3. Review source/target feature and identity constraints: special/shared devices, licensing, host-bound keys, application/database versions, encryption and required metadata. Give every relevant feature a tested treatment or explicit exclusion.
4. Design one consistent capture boundary covering database records and attachments with their required permissions/metadata and keys. Define how ingress, background tasks and all external writers are quiesced or fenced. Copying a live database directory is not assumed safe.
5. Design target quarantine, approved network/service mappings, identity treatment and configuration reconstruction. Rehearsal must suppress real mail, scheduled jobs and other external business effects.
6. Run bounded deployment, capture, transfer and restore experiments on approved fixtures. Record actual commands, artifact/tool versions, source/output digests, consistency markers, resource use and application observations. Preserve failures and recovery attempts.
7. Interrupt capture/transfer/restore, corrupt a test artifact and lose an effect acknowledgement. Establish safe resume, full restart or held reconciliation from actual target/data state; no blind re-execution or partial dataset activation.
8. Rehearse final source quiescence/fencing and capture/restore, target validation and separately admitted write enablement/traffic switching. Record the last accepted source write and first possible/accepted target write independently.
9. Demonstrate pre-target-write source return and selected post-target-write recovery separately against meaningful state. If authorized execution is unavailable, record the exact missing experiment and authority rather than claiming recovery.
10. Review results with platform, application, security and qualification owners. Accept the bounded candidate, require a specific experiment, explicitly select a different method or reject the route.

## Feasibility checks

| Check | Required observation | Implementation consequence |
| --- | --- | --- |
| F01 — Complete capture | Every dataset, required configuration/secret reference and writer appears in the manifest and consistency boundary | Missing state or unidentified writers block method acceptance |
| F02 — Reproducible application | Clean target deployment produces the selected application with declared dependencies, mounts and approved identity treatment | Resolve undocumented state or select a different method explicitly |
| F03 — Data correctness | Restored records, attachment digests, metadata and relationships match the captured consistent source | Differences require investigation before route selection |
| F04 — Isolation | Rehearsal target cannot send production mail, trigger jobs or receive production traffic | Add enforced isolation and business-effect controls |
| F05 — Resource budget | Deployment, capture, transfer, restore, validation and retained source fit measured time/storage/bandwidth constraints | Revise placement/budget or reject candidate |
| F06 — Recovery boundary | Source can remain fenced; target writes are identified; accepted writes have a defined preservation path | No post-write recovery mechanism means no migration commitment |
| F07 — Unsupported features | Every relevant application/guest/storage/network/identity feature has a tested treatment or explicit exclusion | Profile and UI must block affected requests |

## Decision record

Record the exact candidate tuple and fixture provenance, observed findings by F01–F07, tested and untested assumptions, evidence IDs, method decision, exclusions, required implementation and Q07 cases. Identify actual reviewers and dates only when review occurs. E0 documents the assessed design; E1/E2 describes actual bounded experiments at their true environment level. Read-only native observations cannot alone establish migration support.

For unresolved access or input, record its responsible role, required fact or experiment, unblock condition and next action in the delivery register. G00.04 cannot pass on an untested route assertion. Preserve useful contract work while the bounded feasibility question is resolved.

## Separate whole-VM option

P09 may qualify `cold_guest_disk_conversion_import` for workloads whose requirements need VM/disk preservation. That scope must separately establish firmware/device/driver compatibility, full disk/snapshot/backing chains, encryption/vTPM treatment, approved conversion/export/import tools, target boot, application correctness and both recovery boundaries. The [P00 review](../../implementation/p00-route-and-operations-review.md) retains primary-source transport/output constraints for that work. Do not use the first rebuild/restore result to advertise whole-VM support, or make an unselected converter experiment a blocker for rebuilding the first application.

## Retest triggers and current inputs

Reassess affected findings when the method, platform/backend, guest/application/database versions, deployment/configuration artifacts, capture/restore tooling, encryption, dataset consistency mechanism or recovery strategy changes. Carry forward an unaffected finding only with a scoped impact review; never transfer qualification from the earlier branch.

The [2026-10-04 route and operating review](../../implementation/p00-route-and-operations-review.md) records the completed desk assessment, RT01–RT10 input inventory and RF01–RF11 experiment design. Installed tuples, fixture bytes and lab authority have not been supplied, and every native experiment remains **NOT RUN**. RI01–RI06 define the finite input handoff; they must be reflected in the canonical register before gate review.

Every supplied tuple fact needs status, source/digest, observation time, scope and owner. Preserve `UNKNOWN` separately from false and from observed incompatibility. Execute only the selected, approved bounded experiment, and retain both successful and failed outcomes.
