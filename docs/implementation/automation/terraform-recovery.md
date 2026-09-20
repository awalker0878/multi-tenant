# Review a held vSphere Terraform attempt

`tools/terraform_recovery_review.py` joins the saved execution evidence, current
durable ledger head and [vSphere VM activity observations](vsphere-readback.md).
It writes an immutable private review packet. It never clears the ledger, runs
Terraform, changes native infrastructure or authorizes replay.

This first receipt-binding profile supports existing VMs in one VMware workload
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

Disk/NIC/firmware and other unchanged settings remain subject to their independent
native baseline and ownership evidence. This profile does not translate the full
provider schema or establish NSX/network associations. The separate clone-tree
observer can collect result/source evidence, but cannot use this existing-VM
review path to adopt a newly created resource.

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

```sh
python3 tools/terraform_recovery_review.py \
  --bundle /private/operator/held-attempt \
  --ledger /private/shared-ledger \
  --manifest /private/operator/vsphere-activity.json \
  --readback /private/operator/vsphere-report.json \
  --context /private/operator/recovery-context.json \
  --output /private/operator/new-recovery-review.json
```

All inputs must be owner-only private artifacts. The new output must be outside
the repository, bundle and ledger. The tool checks sealed input/backend/plan
bytes, scope, native VM coverage, current held head, immutable start/result
records and context/report bindings. It takes the existing local executor lock
while reading and writing the separate review packet, refuses a concurrent
executor and rechecks the head. This lock makes the local review consistent; it
is not native fencing and does not cover another tool or a delayed platform task.

Even `READY_FOR_OPERATOR_RECOVERY_REVIEW` leaves the exact ledger hold and attempt
history intact. The packet retains bound hashes, native ID mappings and the
recomputed triage result with all mutation/activation flags false. Review it with
state/backend, native owner and data-owner evidence. Complete operation-wide
reconciliation and separately approved forward action remain required. No source
of authority, signature service, native fence or ledger-release mechanism is
created by supplying JSON records.
