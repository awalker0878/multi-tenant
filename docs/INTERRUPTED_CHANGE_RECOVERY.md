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
entity coverage require native-owner investigation; this release has no discovery
or speculative resend capability.

NSX configuration reads bracket realization status. Nutanix task reads bracket
resource reads. Stable samples strengthen attribution, but they are not a native
transaction or proof of total inventory completeness. Inspect the selected-field
coverage and add independent route/enforcement/data checks before any later change.

## Review the three records together

The [offline reviewer](../tools/recovery_review.py) consumes the accepted manifest,
the new readback report and an independently controlled interrupted-change context.
It validates exact source/operation/tenant/domain binding, manifest/report digests,
time order, observation freshness, expected generations, and the observation history.
It recomputes the result rather than accepting a forged final status string.

The external control records carry scope, time and evidence references for writer
fencing and quarantine, plus current containment. They need genuine native-owner
and operating evidence. This tool verifies **record consistency**, not signatures,
actual fencing or approval authenticity. Host clock integrity and artifact-access
protection remain prerequisites.

| Result | Meaning and next accountable action |
|---|---|
| `KEEP_INCIDENT_CONTAINMENT` | An active incident restriction takes precedence; ordinary convergence must not undo it. |
| `HOLD_CONTAINMENT_UNKNOWN` | Establish current containment authority before continuing. |
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
