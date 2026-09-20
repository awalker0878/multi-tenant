# AHV VM and recorded task readback

This optional observer supplies bounded evidence for W16/W17 after a recorded VM
operation. It combines the existing [AHV VM expectations](nutanix-vm-readback.md)
with the [Prism task witness checks](../nutanix-task-tree-readback.md). It never
submits a power or reconfiguration command, discovers tasks, fences a writer,
adopts state, clears an execution ledger or grants activation authority.

## Accepted scope

Use the explicit profile `nutanix-ahv-v4.2-prism-v4.3-task-tree` with
`tools/nutanix_vm_task_observe.py`. The installed product tuple and observation
role must support **both** the VMM v4.2 VM interface and Prism v4.3 task interface.
The separate readers' SDK references describe these wire contracts; composing
them does not establish installed compatibility. There is no version negotiation
or fallback. Keep unsupported shapes on hold for engineering review.

Retain the snapshot manifest's common fields and exact `resources`: native VM and
tenant identities, independently accepted strong ETags, host/cluster/project,
categories, ON/OFF power, CPU/memory, NIC and retained-disk expectations. Add this
exact `task` object from the accountable writer's original change trail:

| Field | Required binding |
| --- | --- |
| `ext_id`, `operation` | Actual recorded root task ID and exact native operation label |
| `created_after`, `created_before` | Accepted timezone-bearing task-creation interval; covers every listed task |
| `entity_ids` | Every selected VM UUID exactly once; no foreign resource |
| `descendants` | 0–15 records with exactly `ext_id`, `operation`, `parent_ext_id`, `entity_ids` |

Zero descendants explicitly means a single recorded task. Each descendant must
belong to this root's acyclic graph, with at most four parent/child levels. Child
entities must be an explicit subset of the selected VMs; an empty set is checked
as empty, not ignored. All VMs must share one native tenant. Mixed-entity tasks,
batch jobs, incomplete native child/entity lists, omitted identities and unknown
operations cannot be treated as successful VM-only work. Record the actual
supported operation labels; synthetic fixture labels are not vendor contracts.

## Collection and review

Without contact, validate the private accepted manifest:

```sh
python tools/nutanix_vm_task_observe.py /private/accepted-ahv-tasks.json
```

For an independently authorized read, set `contact_enabled: true`, inject scoped
read-only `NUTANIX_USERNAME` and `NUTANIX_PASSWORD` through the site's secret
system, and provide the exact accepted origin, CA and a new private output:

```sh
python tools/nutanix_vm_task_observe.py /private/accepted-ahv-tasks.json \
  --read-authorized-target --expected-origin https://actual-prism-host \
  --ca-file /private/prism-ca.pem --output /private/new-ahv-task-readback.json
```

Only exact VM GETs and URL-encoded recorded task GETs are allowed. Each round
reads tasks in parent-first order, then all VMs, then tasks in reverse order.
The before/after witness checks identity, operation, ancestry, complete child and
affected-entity sets, creation/completion chronology and terminal state. A failed
GET is not retried and response links are not followed. Native diagnostic text
and unselected guest material are excluded from reports.

Two stable complete rounds with matching VM configuration are needed for
`READBACK_MATCH_NOT_QUALIFIED`. A successful parent cannot hide a pending or failed
child; VM match cannot hide task uncertainty. Task identity changes or terminal
regression hold. Each resource has `task_completion_observed: true` only when the
recorded graph is complete; configuration drift can still hold that report.
The [snapshot-only profile](nutanix-vm-readback.md) retains its false completion flag.

The offline [interrupted-change reviewer](../../INTERRUPTED_CHANGE_RECOVERY.md)
accepts this profile and recomputes every task witness, history and completion
flag. Its context's `attempted_at` must equal `task.created_after`; the upper
creation bound must be no later than readback start. Current writer-fence,
quarantine, generation, containment and data-preservation requirements still
apply. `READY_FOR_OPERATOR_RECOVERY_REVIEW` permits review only. It does not join
AHV observations to the saved Terraform plan or durable attempt ledger; the
[held-attempt integration](terraform-recovery.md) remains vSphere-specific.

[Campaigns v3 and v4](target-qualification.md) select this reader from the bound
workload manifest's exact profile. Existing VM ownership, subnet/address and Flow
membership checks remain required. The task report is included in the combined
before/after hashes. A pending, failed, unknown or drifting result stops the
campaign; do not replace it with a snapshot-only manifest to bypass the hold.

## Qualification boundary

The loopback TLS/CLI regressions cover complete/single tasks, pending/failure,
missing and foreign entities, truncation, terminal regression, VM drift, private
output, tampered witnesses and actual campaign child processes. These are scripted
API responses. They do not exercise native power control or guest traffic.

Qualify the exact installed tuple and real task attribution/visibility in the
[site commissioning procedure](site-commissioning.md). This profile sees only
enumerated tasks: unrelated, hidden, expired, later, cross-entity or synchronous
work remains outside its coverage. Actual cross-writer fencing, operation-wide
reconciliation, native state recovery, security/HA and application-consistent
restore remain required. Local evidence must not populate native acceptance indexes.
