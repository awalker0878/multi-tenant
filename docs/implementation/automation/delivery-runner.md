# Persistent delivery execution

`tools/delivery_run.py` executes an ordered dependency graph through existing
resource owners. It supplies coordination, exact handoffs, durable completion
and process restart recovery. It does not issue approvals or establish native
fencing. Each Terraform, guest, power, IPAM, DNS, campaign and edge adapter retains
its own validation, credentials, scope, private evidence and uncertainty ledger.

## Workflow contract

A private `hosting-delivery/1` plan contains `source_commit`, `operation_id`, a
positive integer `generation`, `scope` and `steps`. Scope has exactly
`environment_key`, `site_key`, `platform`, `tenant_key` and `wsd_key`. The platform
is `openstack`, `nutanix` or `vmware`. Each step has `id`, `kind` and `needs`, an
explicit list of earlier step IDs. IDs are unique; cycles, missing dependencies,
unregistered kinds and disconnected later stages are refused. The plan is
immutable once started. Use a higher generation for a subsequent completed
change; an uncertain generation cannot be bypassed with a new operation name.

The graph describes the reviewed delivery scope. It is not proof that the graph
contains every architectural gate. Review it against the
[delivery sequence](delivery-process.md) and selected offer. An ordinary WSD
graph includes admission, domain plan/apply and native acceptance, workload
plan/apply, narrow bootstrap and native acceptance, guest plan/apply, required
service bindings and acceptance, pre-activation campaign, separately approved
edge policy and post-activation campaign. Commissioning and retirement use their
own reviewed graphs and must not depend on successful ordinary activation.

```json
{
  "format": "hosting-delivery/1",
  "source_commit": "<actual-clean-commit>",
  "operation_id": "change-001",
  "generation": 1,
  "scope": {
    "environment_key": "lab", "site_key": "site-01", "platform": "openstack",
    "tenant_key": "tenant-01", "wsd_key": "wsd-01"
  },
  "steps": [
    {"id": "admission", "kind": "acceptance", "needs": []},
    {"id": "domain-plan", "kind": "terraform_plan", "needs": ["admission"]},
    {"id": "domain-apply", "kind": "terraform_apply", "needs": ["domain-plan"]}
  ]
}
```

This abbreviated example is not an activation graph or an executable native
target. It deliberately supplies no installed IDs, credentials or authority.

## Stage packets and review handoffs

Publish `<step-id>.json` in the private inbox when that stage's actual inputs
and authority are available. Each packet has exactly:

| Field | Value |
| --- | --- |
| `format` | `hosting-delivery-step/1` |
| `plan_sha256` | `tools.readback_core.digest(plan)` |
| `step_id` | Exact selected step ID |
| `dependencies` | Map from every `needs` ID to `tools.readback_core.digest(its completed receipt)` |
| `parameters` | Typed parameters from the adapter table below |
| `files` | Map from adapter input names to `{ "path": "/absolute/private/file", "sha256": "<SHA256-of-file-bytes>" }` |

The runner returns `WAITING_STAGE_INPUTS` with the next step and exact dependency
digests when its packet is missing. This lets a change platform collect a newly
generated saved plan, obtain its actual approval, then publish the apply packet.
No approval for an unknown future plan is generated. File bytes are checked
again immediately before dispatch. Binaries use absolute paths plus separate
`<binary>_sha256` parameters and retain their owner's pinned-runtime checks.

| Kind | Parameters | Mandatory files | Optional files |
| --- | --- | --- | --- |
| `openstack_quota` | None | `request`, `authority`, `token`, `ca` | None |
| `remote_owner` | `ssh`, `ssh_sha256` | `job`, `target`, `ssh_key`, `ssh_certificate` | None |
| `restic` | `action`, `restic`, `restic_sha256`, `target` | `config`, `credentials` | `ca_bundle`; restore also requires `receipt`, `manifest`, `restore_authority` |
| `capacity` | `action`, `database` | `request`, `authority` | `native_ids`; reserve pairs `inputs`, `sizing` to bind actual workload demand |
| `acceptance` | `purpose` | `acceptance` | None |
| `terraform_plan` | `catalog_id`, `terraform`, `terraform_sha256` | `inputs`, `backend`, `environment`, `authority` | `references`, `cloud`, `ca_bundle`, `transition` |
| `terraform_apply` | `prepared_step` | `approval` | None |
| `workload_inputs` | `domain_steps`, `selected_input` | `environment` | `vmware_bindings` |
| `platform_transition` | `prior_step`, `stage` | `inputs`, `acceptance` | None |
| `guest_plan` | `workload_step`, `python`, `python_sha256`, `ssh`, `ssh_sha256`, `mode`, `max_seconds` | `access`, `references`, `ssh_key`, `ssh_certificate` | None |
| `guest_apply` | `prepared_step` | `approval` | None |
| `vsphere_power` | None | `request`, `authority`, `session` | `ca_file` |
| `target_campaign` | `ssh`, `ssh_sha256` | `plan`, `authority` | None |
| `edge_policy` | `nft`, `nft_sha256`, `mode` | `spec`, `authority` | None |
| `edge_containment` | `nft`, `nft_sha256` | `spec`, `authority` | None |
| `ipam` | `action` | `request`, `authority`, `token_file` | `ca_bundle` |
| `dns` | `action` | `allocation`, `confirmation`, `job`, `scope`, `authority`, `token_file`, `tsig_file` | `ca_bundle`, `registration_job`, `registration_scope` |
| `dns_propagation` | `dns_step` | `config`, `secrets` | None |

`prepared_step` must be a direct dependency of the correct plan kind.
`workload_step` must be a direct Terraform apply dependency. The runner checks
that the original execution outputs still equal the retained handoff copies.
`domain_steps` names the exact direct apply dependencies for this WSD in the
supplied full environment intent; `selected_input` selects one compiled workload
input key. The compiler validates the complete environment before selecting the
exact tenant/WSD of this delivery. Operators can pass the same accepted two-tenant
reference environment to each WSD graph without editing it into partial inputs.
The handoff retains the complete environment digest and selected scope; native
receipts from another WSD still cannot satisfy this graph.
The stage emits `inputs.json`, `scopes.json` and `handoff.json`. Workload drafts
remain disabled until actual scope/input review enables the requested build.
`platform_transition` takes a direct prior apply dependency and `stage` equal to
`bootstrap` or `prepared`; it emits `transition.json` for the next saved-plan
preparation. The common adapter dispatches the existing OpenStack, Nutanix or NSX
transition contract and preserves each owner's field/resource restrictions.
Guest operation IDs are deterministically derived from delivery operation plus
step ID; their generation matches the delivery. Terraform and other owners keep
their exact independently approved native operation identities. Files retain
the schemas documented in each owner's runbook. IPAM and DNS share one native
allocation ledger. Edge and backup work must execute on their accepted native
machine; a coordinator does not bypass local machine/namespace checks. Use the
[remote owner worker](remote-owner-worker.md) for separately hosted edge and
restic jobs; its forced command accepts only exact privately staged jobs.

`dns_propagation` consumes its direct `dns_step` dependency's original job,
scope and completed primary result. It authenticates the selected primary,
secondary and recursive views before the service/retirement acceptance gate.
Its interrupted operation is read-only and can resume without another UPDATE.
See [DNS propagation](dns-propagation.md) for view selection and renewed read
authority; success never releases DNS tombstones or authorizes address reuse.

`restic` uses `action: backup` with a null `target`, or `action: restore`
with a new absolute isolated destination. The backup configuration binds the
source machine, repository ID, executable and export consistency owner. Restore
requires the exact capture receipt and manifest plus current authority binding
the destination and an independent machine. The stage retains the receipt,
execution context and capture manifest. A crash after a durable owner receipt
can recover those copies without another backup or restore. Missing receipts
hold the stage; the runner never guesses a snapshot or overwrites a destination.
See [restic recovery](restic-recovery.md) for repository/key responsibilities.

The `openstack_quota` stage applies the accepted project-level quota change
for the delivery's exact environment/site/tenant and OpenStack source. Quotas
belong to the tenant project, so their owner ledger is shared across WSD graphs.
It does not reserve physical capacity or grant a role. Place the completed quota
handoff behind admission and before allocation that consumes the entitlement.
See [OpenStack quotas](openstack-quotas.md) for native driver acceptance.

If a quota stage loses its result, publish `<step-id>.recovery-authority.json`
as `hosting-openstack-quota-recovery/1` with `request_sha256` and
`files`. The files object binds exactly `authority`, `token`, `ca`
using the ordinary absolute private path and byte-digest shape. The renewed
authority must be observe-only for the original request. This supports expired
credential replacement without changing the approved project, actor, endpoint,
roles or limits. A pending native change is observed, never reissued.

The stage retains its actual authority and result before publishing completion.
A lost coordinator marker can recover those bytes without retaining old
credentials or issuing more native writes. It checks that the shared native
quota history is still completed at this same request; later/pending generations
hold the old handoff. Finished delivery receipts are historical records, so
subsequent allocation still needs current admission and enforcement evidence.

## Accepted gates and renewal

The acceptance file is `hosting-delivery-acceptance/1`, with `plan_sha256`,
`step_id`, `scope`, `dependencies`, `purpose`, `valid_from`, `valid_until` and
`acceptance_ref`. Purposes are `admission`, `domain`, `bootstrap`, `services`,
`activation`, `post_activation`, `recovery` or `retirement`. Plan, scope, step,
purpose and every predecessor digest must match the gate's packet. The issuing
change system remains responsible for the actual independent acceptance.

Acceptance windows last at most one hour and are checked before every dependent
stage, including transitive dependencies. To renew a long-running workflow,
publish `<gate-id>.renewal.json` containing the same acceptance record with a
current window and current external acceptance reference. All other fields must
remain identical. Renewal adds an immutable journal event; it never replaces the
original evidence or executes the gate again. An expired reference cannot be
renewed merely because its historical tests once passed: obtain current native
evidence as required by the owning gate.

## Execution and recovery

```sh
python tools/delivery_run.py --plan /private/delivery.json \
  --inbox /private/inbox --ledger /private/delivery-ledger --execute
```

Use the same command after supplying a missing packet or restarting the
controller. All directories must be owner-only and outside the checkout. The
runner serializes one WSD scope, journals intent before dispatch and preserves
the owner's completion artifacts before publishing a completed stage. Replayed
history checks every event's hash chain and every completed artifact's bytes.
Successful stages are not re-executed. A crash after durable owner completion
but before coordinator publication resumes by publishing that same completion.
If an owner was interrupted before that durable completion, keep the hold and
use its independent recovery procedure; the coordinator does not rerun it.

For Terraform and guest applies, the runner can also recover an owner that
finished before the coordinator's completion marker was written. It verifies the
original bundle, exact source/scope, retained outputs or guest statistics, and
the shared owner's complete attempt history and latest head before publishing
the handoff. A failed/unknown owner result or a later superseding operation holds.
For vSphere power, restart resumes native task observation only; it cannot send
a second power request. If needed, publish `<step-id>.recovery-authority.json`
with current power observation authority for the identical original request.
Lost response task IDs use the separately accepted
[native task mapping](vsphere-power.md) before the runner resumes observation.

Native owner ledgers live under the shared `owners` directory, outside individual
workflow generations. A new graph, scope directory or output folder therefore
does not silently create a fresh owner ledger. All controllers must share this
protected durable store. File locks and hash chains do not fence platform
automation or authenticate a privileged filesystem custodian. Back up journals,
sealed execution bundles and external acceptance records together.

The final state is `DELIVERY_EXECUTED_REQUIRES_ACCEPTANCE`. Native acceptance and
production activation remain false in coordinator summaries; actual exposure,
lease and qualification facts come from the relevant owner evidence. In
particular, completion does not keep an expiring edge lease alive. A failed
post-activation campaign requires the separate edge owner's authorized withdrawal.
The optional [delegated incident handler](incident-containment.md) performs that
withdrawal on selected failures or missing verification inputs while keeping
the forward workflow held. It does not depend on successful graph completion.
Cross-host dispatch and controller-host-loss handling remain separate from this
local failure hook.
