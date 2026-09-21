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
| `capacity` | `action`, `database` | `request`, `authority` | `native_ids` |
| `acceptance` | `purpose` | `acceptance` | None |
| `terraform_plan` | `catalog_id`, `terraform`, `terraform_sha256` | `inputs`, `backend`, `environment`, `authority` | `references`, `cloud`, `ca_bundle`, `transition` |
| `terraform_apply` | `prepared_step` | `approval` | None |
| `guest_plan` | `workload_step`, `python`, `python_sha256`, `ssh`, `ssh_sha256`, `mode`, `max_seconds` | `access`, `references`, `ssh_key`, `ssh_certificate` | None |
| `guest_apply` | `prepared_step` | `approval` | None |
| `vsphere_power` | None | `request`, `authority`, `session` | `ca_file` |
| `target_campaign` | `ssh`, `ssh_sha256` | `plan`, `authority` | None |
| `edge_policy` | `nft`, `nft_sha256`, `mode` | `spec`, `authority` | None |
| `ipam` | `action` | `request`, `authority`, `token_file` | `ca_bundle` |
| `dns` | `action` | `allocation`, `confirmation`, `job`, `scope`, `authority`, `token_file`, `tsig_file` | `ca_bundle`, `registration_job`, `registration_scope` |

`prepared_step` must be a direct dependency of the correct plan kind.
`workload_step` must be a direct Terraform apply dependency. The runner checks
that the original execution outputs still equal the retained handoff copies.
Guest operation IDs are deterministically derived from delivery operation plus
step ID; their generation matches the delivery. Terraform and other owners keep
their exact independently approved native operation identities. Files retain
the schemas documented in each owner's runbook. IPAM and DNS share one native
allocation ledger. Edge and backup work must execute on their accepted native
machine; a coordinator does not bypass local machine/namespace checks.

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
post-activation campaign requires the separate edge owner's authorized withdrawal;
do not make that incident action wait for successful completion of the delivery
graph. A crash before the owner completion marker, autonomous containment and
cross-host dispatch remain separate integration work.
