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

The [TaskInfo API](https://developer.broadcom.com/xapis/virtual-infrastructure-json-api/latest/sdk/vim25/release/Task/moId/info/get/)
defines the observed fields; the pinned
[govmomi VM simulator](https://github.com/vmware/govmomi/blob/v0.49.0/simulator/virtual_machine.go)
provides the supported task description identifiers. Actual site commissioning
must verify their native behavior and the installed API tuple.
