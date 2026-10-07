# Q07 — First offline migration

Q07 verifies R22–R24, with service/policy/retirement obligations from R20/R21/R25. It supports P08.01–P08.06 and G08.01–G08.04. The selected first direction is VMware→OpenStack; method and exact tuple must be decided through [initial route feasibility](../feasibility/initial-route.md). Reverse, warm and live routes are separate claims.

## Scope and ownership

Application/data owners define correctness and acceptable outage/data objectives. Platform owners authorize source/target effects and fencing; lifecycle coordinates; an independent observer verifies ordered native outcomes. E3 requires the complete native application path, including both recovery boundaries. E2 rehearsal of workflow logic cannot replace E3 route qualification.

Use the [application walkthrough](../../product/application-walkthrough.md), [Q04 fault procedure](q04-durable-execution.md), [Q05 service checks](q05-native-provisioning.md) and [Q06 policy procedure](q06-policy-equivalence.md). Native source-operation authority must be explicit; matching discovered names is insufficient.

## Preparation

The initial route provisions OpenStack through native APIs and migrates VMware VMs with `native_api_export_import`: approved guest preparation, application consistency and source-writer fencing, powered-off `ExportVm`/NFC disk export, verified native manifests, and native destination image/volume/compute import. The installed tuple must support the exported disks, firmware and guest drivers. Unsupported routes remain held. There is no converter, application native export/import or alternate migration path. Native provisioning and migration require separate Q05/Q06 and Q07 qualification.

## Case matrix

| Case | Action or injected fault | Required observation | Evidence |
| --- | --- | --- | --- |
| Q07.01 | Reconcile source readiness, reproducible target deployment/configuration, encryption, consistent-capture method, dataset/metadata and dependency inventory | All required scope is represented; unsupported or unknown mandatory features block migration | Source/profile reconciliation and denial cases |
| Q07.02 | Rehearse the exact method in isolation with production effects suppressed | Guest and application become usable without unintended mail, jobs, traffic or writers | Rehearsal topology, suppression probes and application checks |
| Q07.03 | Import the target application and restore consistently captured datasets according to the explicitly selected method | Dataset, metadata, identity treatment and all mapped resources match declared acceptance | Deployment/restore logs, consistent-capture manifests, digests and native readback |
| Q07.04 | Interrupt transfer or exhaust the bounded staging budget | Transfer safely resumes or restarts as declared; partial data cannot activate; budget uncertainty remains held | Fault timeline, storage observations and recovery record |
| Q07.05 | Attempt cutover with stale approval, unfenced source or another active writer | Final sync/activation is denied until independent fencing and current authority are proven | Authority/fencing denial matrix |
| Q07.06 | Quiesce/fence source and other writers, final-sync, validate target, then enable traffic/writes | Observed order prevents split brain; final accepted source data reaches target before first permitted target write | Timestamped writer/traffic observations and final integrity checks |
| Q07.07 | Fail before any target business write and invoke approved rollback | Source resumes only after target is fenced and authoritative checks show no target divergence | Boundary proof, rollback order and application read/write check |
| Q07.08 | Commit a known target write, inject failure, then execute selected post-write recovery | Accepted target changes are preserved through source-return reconciliation or forward recovery; old source is not blindly restarted | Known-write marker, recovery dataset diff and fence history |
| Q07.09 | Measure full outage and data result; exercise service/policy paths after migration | Actual application outage/data objectives and Q05/Q06 requirements pass, including restore | Timing definition, measured results and referenced service/policy evidence |
| Q07.10 | Review retained source and attempt premature deletion/release | Source/data/keys remain until separate retention and retirement criteria are met | Retention inventory, denial and later authorized retirement receipts |

## Execution and observations

Define outage start/end in application terms before execution, including the last accepted source transaction and first valid target service availability. Record the first target business write explicitly; successful VM boot or traffic enablement alone does not define data divergence.

Use an independent source/other-writer fence observation. A successful shutdown API response does not prove that an external database client, scheduler or restored stale instance cannot write.

Run both recovery cases against meaningful state. In Q07.08, verify the deliberately committed target record and attachment survive the selected recovery, with relationships/metadata intact. A source restart that discards that record fails the campaign.

## Pass criteria and evidence

All approved datasets, identities, policy/service requirements and recovery cases must pass for the selected exact method. Missing fencing, unknown completion, failed data integrity or an unproved post-write recovery boundary blocks route qualification regardless of a successful nominal migration.

Preserve tuple/profile/artifact identities, plans/approvals, consistency manifests, transfer/import observations, known-write markers, source/target comparisons, traffic/fence timelines, timings and recovery decisions. Bind E3 evidence to each G08 criterion under the [status rules](../../implementation/status-model.md).

## Cleanup and reruns

Keep source and target fenced/retained according to the final authoritative recovery state. Separate cleanup authority from cutover authority and reconcile all allocations before release. Requalify affected cases after changes to the method, guest/disks, consistency/fencing, network, services or recovery procedure.
