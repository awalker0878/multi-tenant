# vSphere VM snapshot readback

`tools/vsphere_observe.py` uses the Virtual Infrastructure JSON API with the
explicit `8.0.3.0` release schema. It reads only the `config`, `runtime` and
`resourcePool` properties of enumerated `VirtualMachine` managed object IDs.
It does not discover VMs, log in, mutate configuration or control power.

Use the common [native readback envelope](../../NATIVE_READBACK.md), platform
`vmware`, profile `vsphere-vi-json-8.0.3.0-vm-snapshot`, and no `task`. Each resource
contains `kind: vm`, `moid` and `expected`. The expected object contains the three
property responses, restricted to the fields enforced by `validate()`. Accept
the mapping from managed object ID to BIOS `uuid` (the Terraform VM ID) and
vCenter `instanceUuid` independently. A VM name or portable tenant label is
insufficient proof of ownership.

The snapshot includes the accepted config `changeVersion`, CPU/memory, full
hardware device inventory, host, resource pool, power and explicit stable runtime
flags. This profile supports vmxnet3 NICs on opaque NSX or distributed-port
backings and persistent flat-v2 disks with UUID, datastore and slot identities.
All native fields of every device are compared, including backing and connection
flags. Unsupported devices or disk chains require engineering review. Other
configuration fields, including guest initialization material, are outside this
profile and are not journaled. The complete controller/device list must come
from accepted native evidence, never synthesized to match a fixture.

Validate without network contact:

```sh
python3 tools/vsphere_observe.py /private/site/vsphere-manifest.json
```

For an authorized read, inject the site's short-lived read-only session through
`VCENTER_SESSION` and provide `--read-authorized-target`, `--expected-origin`,
`--ca-file`, and a new private `--output`. The session must be issued through the
VI `SessionManager` login mechanism; a vAPI session is not assumed interchangeable.
The GET transport verifies TLS, refuses redirects and bounds response/polling
work. A missing property, unsupported shape, changed identity/revision or drift
holds the observation. Missing Boolean fields are not defaulted to false.

Each sample reads all three properties twice and requires matching selected
snapshots; two stable rounds are required. This detects observed concurrent
changes but is not an atomic snapshot or a native writer fence. A configuration
match cannot determine task completion, resolve an uncertain Terraform apply,
authorize retry, prove NSX membership/enforcement, or establish HA/recovery.

Interfaces: Broadcom's [VM config](https://developer.broadcom.com/xapis/virtual-infrastructure-json-api/latest/sdk/vim25/release/VirtualMachine/moId/config/get/),
[runtime](https://developer.broadcom.com/xapis/virtual-infrastructure-json-api/latest/sdk/vim25/release/VirtualMachine/moId/runtime/get/)
and [session authentication](https://developer.broadcom.com/xapis/virtual-infrastructure-json-api/latest/api-security-schema/)
documentation, with field availability checked against the
[govmomi 0.49.0 types](https://github.com/vmware/govmomi/blob/v0.49.0/vim25/types/types.go)
pinned by vSphere provider 2.12.0. These references and repository HTTPS fixtures
do not qualify an installed vCenter/ESXi/NSX tuple.

## Task reconciliation evidence

`tools/vsphere_task_observe.py` adds GETs for enumerated `Task/{moId}/info`
properties. Use profile `vsphere-vi-json-8.0.3.0-vm-tasks` with the same VM
resources and a `task` object containing `execution_record_ref` and `records`.
Each record has `moid`, `vm_moid`, `description_id`, `queued_at` and
`event_chain_id`, copied from independently accepted native execution evidence.
The supported monolithic descriptions are `VirtualMachine.powerOn`,
`VirtualMachine.powerOff` and `VirtualMachine.reconfigVm`. Do not guess a task ID
from a VM name or select a convenient successful historical task.

Every observed VM must have a task record, and every task must name an observed
VM. Task identity, entity, operation, queue time and event chain must all match.
Pending, failed, cancelled, missing, contradictory or composite task observations
hold. A successful task requires ordered queue/start/completion timestamps,
no fault and no non-void result. Parent/foreign-root task chains, clone workflows
and result-bearing operations require separate reconciliation. Task properties
are read before and after VM snapshots; terminal regression or changed completed
task evidence is held across rounds. Arbitrary faults/results are not recorded.

The report marks only the enumerated completed tasks as observed. It does not
prove the task list is complete, fence another writer, release an uncertain
execution ledger, authorize replay/repair, or turn task success into application
readiness. Retain the report with the original execution receipt, approved
inputs, native task trail and state/backend evidence. An operator must reconcile
the entire operation before separately authorizing any forward action.

The offline `tools/recovery_review.py` now accepts the exact-task profile. It
requires VM and task coverage, recomputes task outcomes from bounded selected
witnesses at each sample's time, and rejects rehashed contradictory summaries.
Snapshots alone remain insufficient for completion review. The normal fencing,
quarantine, containment, freshness and generation checks still apply; every result
retains `may_apply: false`. Witnesses exclude native fault text and arbitrary
results. Recollect older reports that lack the new witness fields.

The [TaskInfo API](https://developer.broadcom.com/xapis/virtual-infrastructure-json-api/latest/sdk/vim25/release/Task/moId/info/get/)
defines the observed fields; the pinned
[govmomi VM simulator](https://github.com/vmware/govmomi/blob/v0.49.0/simulator/virtual_machine.go)
provides the supported task description identifiers. Actual site commissioning
must verify their native behavior and the installed API tuple.

## Bounded task trees and child-history checks

`tools/vsphere_task_tree_observe.py` uses profile
`vsphere-vi-json-8.0.3.0-task-tree-history`. It retains the accepted VM resources
and supported power/reconfiguration operations. The `task` object adds
`task_manager_id` and `coverage_ref`; every task record adds `parent_task_id`
(null for a root) and `root_task_id`. Enumerate at most 20 tasks, including every
accepted child, with an acyclic ancestry confined to its observed VM. The native
parent/root links and timestamps must match. Clone/result-bearing operations,
tasks on other native entity types and unreviewed internal operations remain held.

This profile also queries native history with `parentTaskKey` set to **all**
accepted task IDs, including leaves. It uses only three session-collector POST
methods: create the filtered collector, read successive pages, and destroy that
collector. No VM power/configuration, task cancel, unfiltered inventory query or
arbitrary POST interface is supplied. A new collector begins at the oldest item;
the reader drains through an explicit empty page. A short page is not treated as
completion. Six pages, 20 entries per page, 100 total entries, the shared request
limit and a 120-second transport budget bound collection. Duplicated, oversized,
incomplete or failed pages and cleanup failures hold the observation. After a
lost collector-creation reply or process stop, the session owner must reconcile
remaining session collectors; the tool does not rediscover or retry creation.

Child-history scans bracket task/VM reads. Both scans must match the exact
expected non-root task set and the direct task witnesses. Missing or additional
children hold; parent success cannot hide a pending or failed child. Two stable
rounds are still required. Campaign v5 and offline recovery review support this
profile, including recomputation of history coverage from its bounded witnesses.

The coverage reference must independently establish installed API applicability,
task-history retention and the observer's visibility into every relevant native
task. These queries prove only the visible accepted task graph; they cannot fence
another writer, detect all unrelated operations on the VM, or prevent a future
child submission. Keep actual writer exclusion and operation-wide reconciliation
as separate required evidence. No ledger is cleared and no power action is issued.

### Activity on the exact existing VMs

Profile `vsphere-vi-json-8.0.3.0-vm-task-activity` adds a check for separate root
tasks omitted from the accepted tree. It supports the same existing-VM power and
reconfiguration task records, and adds `task.activity_since`: the exact interrupted
attempt start timestamp. Offline recovery review requires this timestamp to equal
`context.attempted_at`. It must precede or equal every accepted task's queue time.
This profile is separate from clone/source reconciliation below.

For each accepted VM, the collector uses that exact `VirtualMachine` reference
and entity recursion `self`, with no user, parent, root or event-chain restriction:

1. Read all visible queued/running tasks, without a time cutoff. Older pending
   work must remain visible.
2. Read success/error tasks with `completedTime` beginning at `activity_since`.
   Work queued before the attempt but completed afterward must remain visible.

These scans bracket the child-history and direct task/VM reads. Before and after
activity must contain exactly the accepted task set, including roots, agree with
the direct task witnesses, and remain stable. Additional or omitted tasks hold.
A task crossing from pending to completed between queries appears twice and holds
as uncertain; the reader does not silently deduplicate it. Wrong entities,
contradictory filter results and future/reversed timestamps also hold. Offline
review recomputes these checks from the selected witnesses at each sample's time.

Only the three collector methods described above are used. Each activity scan
allows at most 100 entries across its queries; the per-collector page bounds and
shared request/time budgets still apply. A busy VM may exceed these limits and
require a separate native investigation; narrowing visibility to obtain a match
is not an acceptable fallback. Campaign v5 supports this profile.

This detects **visible task activity**, not all native changes. Installed task
retention, RBAC visibility and filter behavior require independent qualification.
Synchronous operations without tasks, other entities, hidden/expired records and
work submitted after the scan are outside its coverage. It does not implement
writer exclusion, issue power actions, or establish complete lifecycle recovery.
Keep the external writer fence and operation-wide reconciliation requirements.

Filter semantics: [entity scope](https://developer.broadcom.com/xapis/virtual-infrastructure-json-api/latest/data-structures/TaskFilterSpecByEntity/),
[`self` recursion](https://developer.broadcom.com/xapis/virtual-infrastructure-json-api/latest/data-structures/TaskFilterSpecRecursionOption_enum/),
[time bounds](https://developer.broadcom.com/xapis/virtual-infrastructure-json-api/latest/data-structures/TaskFilterSpecByTime/)
and [completion-time selection](https://developer.broadcom.com/xapis/virtual-infrastructure-json-api/latest/data-structures/TaskFilterSpecTimeOption_enum/).
Published interfaces and local fixtures do not qualify the installed API tuple.

Interfaces: [task filter](https://developer.broadcom.com/xapis/virtual-infrastructure-json-api/latest/data-structures/TaskFilterSpec/),
[collector creation](https://developer.broadcom.com/xapis/virtual-infrastructure-json-api/latest/sdk/vim25/release/TaskManager/moId/CreateCollectorForTasks/post/),
[page reads](https://developer.broadcom.com/xapis/virtual-infrastructure-json-api/latest/sdk/vim25/release/TaskHistoryCollector/moId/ReadNextTasks/post/),
[initial cursor](https://developer.broadcom.com/xapis/virtual-infrastructure-json-api/latest/sdk/vim25/release/HistoryCollector/moId/RewindCollector/post/)
and [collector cleanup](https://developer.broadcom.com/xapis/virtual-infrastructure-json-api/latest/sdk/vim25/release/HistoryCollector/moId/DestroyCollector/post/).
The session-local collector changes are separate from infrastructure mutations.

## Template clone result and source coverage

The same task-tree command additionally supports
`vsphere-vi-json-8.0.3.0-clone-tree-history`. This profile observes an already
identified clone; it never submits `CloneVM_Task` or discovers a destination by
name. Each destination requires exactly one accepted `VirtualMachine.clone` root
record. It adds `source_moid`; `vm_moid` remains the destination. A successful
task must name the source as its entity and return the exact destination VM
managed reference. Missing, foreign or unsupported results remain held. Pending
clones cannot claim a result, and clone success cannot hide pending child work.

Add `task.sources`, a bounded list of `moid` and `expected` objects. Each expected
object contains `_typeName: VirtualMachineConfigInfo`, `uuid`, `instanceUuid`,
`template: true` and the accepted `changeVersion`. Source identities must be
distinct from destinations and observed twice around the task/history/VM reads.
Unstable identity/revision, changed template status and missing child history hold.
Offline review recomputes both source and result witnesses; campaign v5 supports
this profile. Destination device/placement/power coverage remains unchanged.

Accept source UUID/revision, destination binding and task trail independently.
The source snapshot does not attest image contents or prove the template was
unchanged at clone submission. vCenter task descriptions and history visibility
must be qualified on the actual installed tuple; do not silently map simulator
aliases to native operations. The pinned govmomi simulator calls its clone task
`VirtualMachine.cloneVm`, which is not accepted as an alias by this profile.
Unrecorded internal task types, chained clones, non-template sources and other
cross-entity operations still require separate coverage. No state adoption,
ledger release, native fencing, replay or power control is supplied.

The [CloneVM task contract](https://developer.broadcom.com/xapis/virtual-infrastructure-json-api/latest/sdk/vim25/release/VirtualMachine/moId/CloneVM_Task/post/)
defines the successful result as the new VM; Broadcom's
[native clone diagnostic](https://knowledge.broadcom.com/external/article/427645/scheduled-vm-clone-task-fails-with-error.html)
identifies the native clone operation. The profile remains an unqualified
candidate until native TaskInfo captures establish its exact applicability.
