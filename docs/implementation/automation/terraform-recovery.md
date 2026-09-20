# Review a held Terraform native attempt

`tools/terraform_recovery_review.py` joins the saved execution evidence, current
durable ledger head and supported vSphere/AHV VM or Flow policy activity observations.
It writes an immutable private review packet. It never clears the ledger, runs
Terraform, changes native infrastructure or authorizes replay.

## Existing vSphere VM configuration

The [vSphere profile](vsphere-readback.md) supports existing VMs in one VMware workload
scope. The saved plan must contain exactly the owned member VM addresses, with
known unchanged BIOS UUIDs and only no-op/update actions. Every native observation
must cover those same UUIDs. Unknown creates, replacements, deletes, extra managed
resource types and partial identity coverage require separate ownership/adoption
reconciliation; do not substitute guessed IDs to obtain a review result.

The reviewer compares planned name, vCPU count, cores per socket, memory in MB
and resource-pool MoID with the accepted native expectations and sealed member
inputs. This profile permits only CPU/memory/topology updates; other requested
changes, unresolved values, drift, moved addresses and adoption hold. Known
native MoID/UUID/revision/power metadata must agree when present. A computed
revision may be unknown in the plan; independent current readback still requires
an accepted exact revision. Matching VM UUIDs alone is insufficient.

Retained disks now require exact native device keys/UUIDs, relative VMDK paths,
capacity, datastore and controller/slot bindings. The supported current-module
layout is one SCSI controller on bus 0, `disk0` at unit 0 and optional `data0` at
unit 1. Capacities must equal the sealed member inputs; native backing must be
persistent, thin, explicitly not eagerly scrubbed and `sharingNone`, with no
parent snapshot. Planned `keep_on_remove` must remain true and `attach` false.
Storage policy IDs must agree across plan and sealed inputs; this does not prove
native SPBM compliance, encryption or useful-data recovery. Unknown/missing disk
identities and unsupported layouts hold, even when before/after plan values agree.

The existing VM must be powered on with one connected vmxnet3 NIC and a native
generated/assigned MAC. Its planned key, MAC, adapter and network MoID must match
the accepted VM and sealed `quarantine_network_id`; static-MAC configuration is
outside this profile. Also collect the separate
[native attachment report](vmware-network-binding.md) with profile
`vsphere-vi-json-8.0.3.0-nsx-port-attachments`. Pass the private manifest/report
through `--network-manifest` and `--network-readback`. They must share the VM
report's vCenter origin, operation, tenant/WSD, engineering and target bindings.

The reviewer resolves each planned network MoID through the observed portgroup
and switch to its exact native backing keys. It checks port key/cookie, connected
VM/NIC, host and runtime MAC against the accepted VM. Native keys are not assumed
equal to Terraform network MoIDs. Shared portgroups are allowed only with complete
distinct owned occupants; extra ports or unused groups hold. Opaque/standard
networks, powered-off/disconnected VMs and unsupported layouts require separate
review. No guessed key-to-MoID conversion or snapshot-only fallback is supplied.

Both reports must be fresh, postdate the attempt/security change and have been
collected after the same current fence/quarantine verification. Attachment
witnesses are recomputed offline; missing witnesses, drift, stale or unbound
reports refuse the packet. `HOLD_NETWORK_NOT_UNDER_CONTROLS` requires new network
sampling if its collection began before those controls were verified, even if
the later VM sample matches. Recollect older reports without the witness fields.
The packet binds both report/manifest hashes and the native attachment mapping.

Firmware, image trust and other unchanged settings retain their independent
baseline and ownership requirements. This profile does not translate the entire
provider schema or establish effective NSX domain membership/DFW enforcement;
the separate campaign v7 still checks owned NSX segment associations and traffic.
The selected plan mappings follow the pinned provider's
[disk readback](https://github.com/vmware/terraform-provider-vsphere/blob/v2.12.0/vsphere/internal/virtualdevice/virtual_machine_disk_subresource.go),
[device keys/addresses](https://github.com/vmware/terraform-provider-vsphere/blob/v2.12.0/vsphere/internal/virtualdevice/virtual_machine_device_subresource.go)
and [NIC network resolution](https://github.com/vmware/terraform-provider-vsphere/blob/v2.12.0/vsphere/internal/virtualdevice/virtual_machine_network_interface_subresource.go).
Actual installed schema/visibility and response semantics still require qualification.
The separate clone-tree observer can collect result/source evidence, and the separate
`vsphere-vi-json-8.0.3.0-clone-task-activity` profile additionally observes visible
work on both source and destination. Neither can use this existing-VM review path
to adopt a newly created resource. A matching clone activity report leaves all
ledger bytes held; creation/state ownership and approved forward action remain
separate native-owner decisions.

Preserve the original bundle and shared durable ledger. Prepare current observations
with profile `vsphere-vi-json-8.0.3.0-vm-task-activity`, the original operation ID,
portable tenant/WSD, native provider origin and accepted independent target bindings.
This checks the accepted tree and child history as well as visible pending work
and work completed since the attempt on those exact VMs. The review refuses older
profiles that observe only the accepted tree. `task.activity_since` must equal the
immutable ledger attempt start; a shorter or shifted window is refused. Additional
activity holds review even if the accepted tasks succeeded and the VM matches.
Accepted task queue times must not predate the attempt. The interrupted-change context must name the exact
binary saved-plan digest, attempted generation/time and original change reference.
Its current generation, genuine native writer-fence, quarantine and incident
containment evidence still determine the triage result.
Verify fencing and quarantine before starting readback; a control observation
that postdates the report's start requires fresh native sampling.

## Existing AHV power/NIC lifecycle

For a Nutanix workload attempt, use
`nutanix-ahv-v4.2-prism-v4.3-vm-task-activity` from the
[AHV activity reader](nutanix-vm-activity-readback.md). Snapshot or recorded-task-only
evidence is refused. `task.created_after` must equal the immutable ledger attempt
start; the upper task-creation bound must not postdate report start. Additional
visible activity holds even when the recorded tasks and VM configuration match.

The bundle must also contain the original sealed `transition.json` for an
existing-VM bootstrap or return to `prepared`. The reviewer binds its digest,
scope, member inputs, native IDs and power/NIC-only plan to the original attempt.
It compares planned name, power, CPU/memory, cluster/project/category, exact NIC
identity/MAC/model/subnet/address/connection and retained disk identities,
SCSI slots, sizes and storage containers with the accepted native expectations.
Known host and tenant metadata must agree when present. Every owned member and
VM must be covered exactly once; unresolved configuration, drift, imports,
creates, replacements, deletes, unrelated updates and partial coverage hold.
Other unchanged provider settings still require their independent baseline.

The selected state fields follow the pinned
[Nutanix 2.4.2 VM provider](https://github.com/nutanix/terraform-provider-nutanix/blob/v2.4.2/nutanix/services/vmmv2/resource_nutanix_virtual_machine_v2.go).
Synthetic plan tests do not qualify the installed provider/API pair. Capture
actual reviewed plans and native revisions during commissioning.

Historical transition validity is checked at the immutable attempt time. An
expired record can therefore be reviewed if it was valid when the attempt began.
This does not extend its authority: current prepare/apply paths still check the
current clock, and this reviewer has no apply, replay or ledger-release action.
The context must bind the binary saved-plan digest, attempted generation/time
and original change reference. Current containment, real native fencing and
quarantine still govern the recomputed triage result.

## Existing Flow service lifecycle

For a Nutanix domain attempt, use the explicit
[Flow task/activity profile](nutanix-flow-activity-readback.md). It requires policy
snapshots, recorded Prism tasks and complete bounded visible activity, with the
same original-attempt window and current independent controls as AHV recovery.
The sealed `transition.json` must describe bootstrap or return to `prepared` for
existing owned policies. The reviewer binds its historical validity, scope,
member inputs, prior policy/category/VPC IDs and the saved rule-only plan.

Every policy must retain its known native ID and module-derived name. Type,
ENFORCE state, VPC scope, category, hit logging, disabled IPv6 bypass, both deny
rules and exact sorted service intent must match the native expectations. The
original deny IDs and any retained service IDs must be known and unchanged.
A new service-rule ID can be observed where the original plan explicitly marks
only that computed ID unknown. This does not adopt a new policy into state.
Known service IDs must match; unresolved security fields and contradictory masks
hold. Existing category/VPC/subnet resources may occur only as exact resolved
no-ops. Other mutations, imports, moved addresses, replacements, deletes and
partial policy coverage require separate engineering/ownership reconciliation.

Selected mappings follow the pinned
[Flow provider resource](https://github.com/nutanix/terraform-provider-nutanix/blob/v2.4.2/nutanix/services/networkingv2/resource_nutanix_network_security_policies_v2.go).
Other unchanged provider settings keep their independent baseline requirements.
Actual installed defaults and task/entity/query semantics still need qualification.
Historical review does not renew apply authority or release the ledger.

## Private review packet

For vSphere, supply the VM/task and native attachment evidence:

```sh
python3 tools/terraform_recovery_review.py \
  --bundle /private/operator/held-attempt \
  --ledger /private/shared-ledger \
  --manifest /private/operator/vsphere-activity.json \
  --readback /private/operator/vsphere-report.json \
  --network-manifest /private/operator/port-attachments.json \
  --network-readback /private/operator/port-attachment-report.json \
  --context /private/operator/recovery-context.json \
  --output /private/operator/new-recovery-review.json
```

For AHV or Flow, use the same command with its activity manifest/report and
**omit both network options**. vSphere attachment inputs cannot qualify Nutanix.

All inputs must be owner-only private artifacts. The new output must be outside
the repository, bundle and ledger. The tool checks sealed input/backend/plan
bytes (and the Nutanix lifecycle artifact), scope, native object coverage, current held
head, immutable start/result records and context/report bindings. It takes the
existing local executor lock while reading and writing the separate review packet, refuses a concurrent
executor and rechecks the head. This lock makes the local review consistent; it
is not native fencing and does not cover another tool or a delayed platform task.

Even `READY_FOR_OPERATOR_RECOVERY_REVIEW` leaves the exact ledger hold and attempt
history intact. The packet retains bound hashes, native ID mappings and the
recomputed triage result with all mutation/activation flags false. Review it with
state/backend, native owner and data-owner evidence. Complete operation-wide
reconciliation and separately approved forward action remain required. No source
of authority, signature service, native fence or ledger-release mechanism is
created by supplying JSON records.
