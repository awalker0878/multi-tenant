# Retained-VM power execution

`provisioner/execution/vsphere_power.py` owns power for an existing VMware VM. Terraform retains
VM configuration, disk and NIC ownership. NSX retains policy/segment ownership;
the edge owner retains exposure. This command never creates, replaces, migrates,
reconfigures or deletes a VM. Its completion is execution evidence, not activation.

## Selected native interface

The first executable profile uses VI JSON 8.0.3.0 `PowerOnVM_Task` with the exact
observed host reference, and `PowerOffVM_Task` with no body. This is a deliberate
compatibility profile matching the repository's VM/task observers. Broadcom
deprecates the single-VM power-on interface on vCenter in favor of
`Datacenter.PowerOnMultiVM_Task`. The latter can return DRS recommendations and
additional tasks; silently treating its parent completion as VM completion is
not supported. A site selecting this profile must accept the older method on
its installed tuple and its actual placement behavior. The request's host is
not a native compare-and-swap or a guarantee against automatic placement.

Only non-template, non-FT VMs with an exact connected managed snapshot are
accepted. Suspended VMs, snapshots/linked disks, unsupported devices and native
runtime questions remain outside this profile. Power-off requires separately
accepted data quiescence; this API is not a graceful guest shutdown. Before
either transition, independently establish writer exclusion and effective
NSX/edge containment, including automated HA/DRS actions and other sessions.

## Private request and authority

The request is a JSON object with these exact fields:

| Field | Contract |
| --- | --- |
| `format` | `hosting-vsphere-power/1` |
| `source_commit` | Exact clean repository commit, 40 lowercase hexadecimal characters |
| `generation` | Positive integer, monotonically increasing for this native VM |
| `snapshot` | One enabled `vsphere-vi-json-8.0.3.0-vm-snapshot` manifest, including complete retained devices and the pre-transition power state |
| `desired_power` | `poweredOn` or `poweredOff`, opposite to that snapshot |
| `task_manager_id` | Exact accepted native TaskManager ID |

The separately issued authority has `format` equal to
`hosting-vsphere-power-authority/1`, `request_sha256` computed using
`provisioner.execution.readback_core.digest`, `valid_from`, `valid_until` (at most one hour),
`change_ref`, `writer_fence_ref`, `containment_ref`, `placement_ref` and
`data_quiesce_ref`. The last field is a nonempty reference for power-off and
JSON null for power-on. References record custody of independently accepted
site evidence; supplying strings does not establish a fence or issue approval.

Store request, authority and the shared ledger outside the checkout, owner-only.
Inject the accepted session through `VCENTER_SESSION_TOKEN`; it is never stored
in the journal. TLS verification is mandatory, with an optional private CA.

```sh
python -m provisioner.execution.vsphere_power --source-root /opt/hosting-source --request /private/power.json \
  --authority /private/power-authority.json --ledger /private/native-ledger \
  --ca-file /private/vcenter-ca.pem --execute-approved-change
```

## Durable execution and recovery

The ledger key is canonical origin plus native VM ID, independent of operation
name, tenant label or generation. All cooperating runners must use this same
durable store. The file lock coordinates those runners only. Protect and back
up the immutable event chain with the change system; hashes detect internal
inconsistency but do not authenticate a privileged custodian or detect deletion
of an entire journal tail.

The writer compares two pre-transition VM snapshots and checks visible pending
and crossing completed tasks. It fsyncs `STARTED` before the one native power
POST, persists the returned task ID, then binds operation, VM, native queue time
and event chain. Successful completion requires terminal task success, two
matching VM snapshots and exact visible task activity. Power and NIC runtime
connection state may change, and the config revision may increment; disk
identity/backing/capacity, NIC backing/start policy, resource pool, host and all
other selected fields must remain unchanged. Arbitrary fault text and task
results are excluded from the journal.

Pending tasks and interrupted reads resume without a second power POST:

```sh
python -m provisioner.execution.vsphere_power --source-root /opt/hosting-source --request /private/power.json \
  --authority /private/current-power-authority.json --ledger /private/native-ledger \
  --ca-file /private/vcenter-ca.pem --resume
```

Issue current observation authority for the same request if the earlier window
expired. A returned task ID can be bound after interruption. If the response
was lost before its ID was persisted, this command holds until an independent
native recovery owner maps the exact attempted request to its actual task.
A renamed operation or higher generation cannot bypass it.
No automatic retry, inferred no-op, task cancellation or rollback is supplied.
Successful duplicate invocation returns the retained receipt without contacting
the VM again. It does not imply that historical state is still current.

For a lost response, supply `--resume --reconcile-task /private/task-mapping.json`.
The mapping has `format: hosting-vsphere-power-reconciliation/1`,
`request_sha256`, `started_event_sha256`, `task_id`, `valid_from`, `valid_until`,
`task_mapping_ref`, `writer_fence_ref` and `containment_ref`. The start-event
digest uses `provisioner.execution.readback_core.digest` over the exact immutable `STARTED`
event, including sequence and prior-event binding. Preserve the actual accepted
mapping file with the external recovery record. The command checks its current
window and the native task's VM, operation, queue chronology, event chain and
nonfailed state before attaching the task to the held attempt. A matching VM
power state alone cannot assign a task, and the tool never searches for the
latest task or chooses a candidate on the operator's behalf. A reconciled task
still must pass the ordinary completion, retained-device and activity checks.
The journal distinguishes independently reconciled IDs from IDs returned by the
original write and records renewed observation authority digests.

The receipt is `POWER_CHANGED_REQUIRES_NATIVE_ACCEPTANCE`, with native acceptance
and production activation both false. Feed its task binding and VM snapshot into
the separate [native observation campaign](target-qualification.md). Run actual
boot/shutdown, lost response, late task, controller interruption, HA/DRS competing
writer, retained-data and containment tests on the installed tuple before use.

Primary API references:
[VM power-on](https://developer.broadcom.com/xapis/virtual-infrastructure-json-api/latest/sdk/vim25/release/VirtualMachine/moId/PowerOnVM_Task/post/),
[VM power-off](https://developer.broadcom.com/xapis/virtual-infrastructure-json-api/latest/sdk/vim25/release/VirtualMachine/moId/PowerOffVM_Task/post/),
[datacenter power-on](https://developer.broadcom.com/xapis/virtual-infrastructure-json-api/latest/sdk/vim25/release/Datacenter/moId/PowerOnMultiVM_Task/post/).
