# Interrupted infrastructure change: observed-state triage

This procedure covers the difficult case in which a runner, API reply or control
connection fails after a change might have reached the native platform. It extends
backlog I09 while preserving the architecture's separate configuration owners,
quarantine, retained data and initial-readiness-before-production gates.

## Stabilize before interpreting a completed task

Stop ordinary change scheduling for the affected owned scope. Determine whether
another executor or delayed native task can still write. A stopped Terraform
process or an unlocked backend alone does not establish that all native work has
stopped. Do not remove a state lock, cancel a task, import an object, replay a create,
withdraw incident containment or delete partial resources merely because a response
was lost. Those are separately authorized changes.

Preserve the original approved plan, request/task identifiers, state generation,
operation time, last security-significant change and evidence. Protect existing
data and held copies. Establish actual, scoped quarantine and writer-fencing
procedures through the responsible owners. Where supported native fencing is not
available, report that limitation and keep the operation on hold; a record saying
VERIFIED cannot itself stop a writer.

## Obtain independent native observations

Use [native readback](NATIVE_READBACK.md) with the exact accepted object/task IDs and
expected configuration/version tokens. It must observe the intended target and
operation, not a resource with a similar display name. Do not fill expected values
from the same unreviewed response being tested. Missing task IDs or incomplete
entity coverage require native-owner investigation. The bounded
[vSphere task-tree profile](implementation/automation/vsphere-readback.md) queries
child history only for accepted task IDs and requires the exact accepted child
set. Its separate existing-VM activity variant also queries pending tasks without
a time cutoff and tasks completed since the interrupted attempt, including
unrecorded roots. Extra or omitted activity holds. Its template-clone variant binds
the accepted source and returned destination identities while retaining child
coverage holds. These profiles do not adopt unknown tasks or supply general inventory discovery or
speculative resend capability.

NSX configuration reads bracket realization status. Nutanix task reads bracket
resource reads. Stable samples strengthen attribution, but they are not a native
transaction or proof of total inventory completeness. Inspect the selected-field
coverage and add independent route/enforcement/data checks before any later change.

The separate [AHV VM/task profile](implementation/automation/nutanix-vm-task-readback.md)
checks an explicitly recorded Prism graph around VMM VM snapshots. Offline review
recomputes its task witnesses and completion flags, requires the creation window
to start at the context's attempted change, and retains fencing/quarantine holds.
It does not discover competing tasks or join AHV evidence to the Terraform ledger.
The separate [AHV activity profile](implementation/automation/nutanix-vm-activity-readback.md)
adds bounded per-VM queries for visible pending work of any age and work completed
since the attempt. Offline review recomputes complete pages, counts, selected
task fields and agreement with direct GETs. Extra or incomplete activity holds;
it does not establish native writer exclusion or complete inventory visibility.

The [Flow task/activity profile](implementation/automation/nutanix-flow-activity-readback.md)
applies the same bounded Prism activity checks to exact owned policies, with
strong-ETag policy snapshots and a full-shape verdict. Mixed policy/category/VPC
operations remain outside its scope. A matching snapshot cannot hide pending,
failed or extra work, or substitute for live enforcement/fencing evidence.

## Review the three records together

The [offline reviewer](../provisioner/execution/recovery_review.py) consumes the accepted manifest,
the new readback report and an independently controlled interrupted-change context.
It validates exact source/operation/tenant/domain binding, manifest/report digests,
time order, observation freshness, expected generations, and the observation history.
It recomputes the result rather than accepting a forged final status string.

The external control records carry scope, time and evidence references for writer
fencing and quarantine, plus current containment. They need genuine native-owner
and operating evidence. This tool verifies **record consistency**, not signatures,
actual fencing or approval authenticity. Host clock integrity and artifact-access
protection remain prerequisites.

Fencing and quarantine must be verified after the attempted operation/latest
security change and no later than the readback start. If either control was
verified after sampling began, collect a fresh report under the established
controls; an older matching snapshot cannot resolve that timing gap.

For a held VMware Terraform workload attempt, use the
[saved-plan/ledger binding reviewer](implementation/automation/terraform-recovery.md)
to join these records to the immutable attempt. This additional profile supports
known existing VMs and CPU/memory/topology updates only, compares planned native
configuration, requires VM activity coverage beginning at the immutable attempt
start, and always preserves the ledger hold. It now also binds retained disk
UUIDs/paths/layout and planned NIC identities to sealed inputs, and requires a
fresh native port-attachment report connecting network MoID, switch/portgroup,
port occupant/cookie, VM/NIC, host and MAC. Both reports must be collected after
fencing/quarantine verification. The supported layout and two extra private
network inputs are specified in the runbook. Older known-task-only profiles or
reports without the new witnesses cannot substitute for this coverage. Clone
result evidence still needs separate creation/state ownership reconciliation.

For a held Nutanix workload attempt, the same reviewer supports existing AHV
power/NIC transitions with the activity profile and original sealed lifecycle
record. It binds selected planned configuration, retained disk/NIC identities,
member inputs and the original attempt window. Historical validity is evaluated
at attempt time; expired authority cannot be used for a new apply. Unsupported
changes, creation/adoption or incomplete bindings hold. Every review leaves all
ledger records intact and grants no recovery action or activation authority.

For a held Nutanix domain attempt, the reviewer also supports existing Flow
service bootstrap/withdrawal with the explicit policy activity profile. It binds
the sealed transition and exact prior policy/category/VPC identities, service
intent and retained deny IDs to the original saved plan and immutable attempt.
Only explicitly computed new service-rule IDs may be unknown in that plan.
Unrelated domain resources must be resolved no-ops. No new policy/state adoption,
ledger release or replay authority is created.

For a held VMware domain attempt, the same reviewer binds the explicit
[NSX domain observer](implementation/automation/nsx-domain-readback.md) to the
sealed lifecycle transition and saved plan. It checks prior Tier-1, segment,
group and policy identities, restricted service intent, retained/generated rule
IDs and current realization evidence. Unsupported selectors in either native
snapshot hold. NSX task inventory and cross-writer exclusion are not supplied;
independent fencing, quarantine, operation-wide reconciliation and ledger holds
remain mandatory.

| Result | Meaning and next accountable action |
|---|---|
| `KEEP_INCIDENT_CONTAINMENT` | An active incident restriction takes precedence; ordinary convergence must not undo it. |
| `HOLD_CONTAINMENT_UNKNOWN` | Establish current containment authority before continuing. |
| `HOLD_NETWORK_NOT_UNDER_CONTROLS` | Held vSphere review found attachment sampling before verified fence/quarantine; collect fresh attachment evidence. |
| `HOLD_WRITER_NOT_FENCED` | The executor may still run, or the scoped/current fencing record is insufficient. |
| `HOLD_SUPERSEDED_CHANGE` | Current generation differs from the attempted change; obtain a new comparison/decision. |
| `HOLD_QUARANTINE_NOT_VERIFIED` | Matching object state does not establish safe connectivity. |
| `WAIT_FOR_NATIVE_TASK` | The known task or intent publication is pending; do not replay the operation. |
| `INSPECT_PARTIAL_FAILURE` | The native task failed/canceled; inspect retained resources and data before a repair design. |
| `RECONCILE_DIVERGENCE` | The selected configuration differs; review ownership and actual effects before any new mutation. |
| `HOLD_NATIVE_UNCERTAINTY` | Missing/unstable/unknown evidence cannot decide the outcome. |
| `HOLD_INVALID_EVIDENCE` | Missing, stale, future-dated, contradictory or unbound records; recollect or resolve them. |
| `READY_FOR_OPERATOR_RECOVERY_REVIEW` | Supplied records satisfy the implemented consistency checks; an operator still decides the next authorized action. |

Every result has `may_apply=false`, `may_delete=false`, and `may_activate=false`.
There is no success branch that executes Terraform or calls a native mutation API.

A `READY_FOR_OPERATOR_RECOVERY_REVIEW` result is still below the [native reconciliation assurance gate](engineering/native-readback-writer-fencing-and-reconciliation-assurance.md). Before a repair/import/resume decision can be treated as current, the separate assurance record must prove exact installed-interface applicability, accepted task/entity coverage, real scoped writer fencing, current containment state and the same operation generation. The gate records an accountable reconciliation decision but never executes it.
The default freshness cap is 300 seconds, configurable 1–900 seconds: a local tool
bound, not a policy mandate. Site owners must set a suitable stricter campaign and
check whether configuration changed again after observation.

## Recovery decision and subsequent change

An accountable owner chooses one of: preserve and wait; collect missing evidence;
reconcile the actual resource and state records; propose a scoped forward repair;
or undertake an approved disposal/retirement. The owner assesses data writes,
shared objects, retained copies, current edge routes, identities and operational
consequences. A new mutation needs its own accepted current plan and authorization.

Do not restore an old Terraform state file and call it infrastructure rollback.
State restoration only changes the tool's record; it does not revert native objects
or data. Do not assume a task cancellation reverses earlier side effects. With
new data writes, a safe return may require a distinct recovery/transfer procedure.

Keep G3 production activation separate. Accepted configuration, reported realization
and this review cannot replace platform qualification, required initial G4 readiness,
route/security verification, service ownership or issued operating authorization.

## Local fault campaign and limits

`python lab/run_readback_lab.py --execute` runs only a disposable local HTTPS fixture.
Its 16 cases cover NSX publication lag, config races, changed permissions, stale intent
and incomplete enforcing-system coverage; Nutanix completion, task lag/failure/404,
foreign native tenant, ETag conflict and incomplete entity coverage; and missing
fencing, active containment and superseding generations.

The HTTP/TLS/parser/observer/reviewer code is real. The published response shapes
are scripted. External fence/quarantine records are **simulated**. No native task
was submitted, canceled or replayed; no native failure, HA, fencing or packet-policy
qualification is claimed. Unit tests add malformed response, transport, certificate,
secret handling, list order, identity and evidence tampering cases.

[Campaign evidence](../quality/local_native_readback.json) ·
[Context example](../examples/recovery_context.json.example) ·
[Backlog](../sources/implementation_backlog.csv)
