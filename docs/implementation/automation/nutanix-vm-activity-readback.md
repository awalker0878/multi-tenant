# AHV visible VM task activity

This optional W16/W17 observer extends the [recorded VM/task reader](nutanix-vm-task-readback.md)
with bounded activity queries for every accepted VM. It can detect visible work
outside the recorded graph and supplies the activity evidence required by the
[held AHV lifecycle reviewer](terraform-recovery.md). It never submits native
commands, adopts tasks/state, releases a ledger or establishes writer exclusion.

`provisioner/execution/nutanix_entity_activity.py` performs the bounded Prism v4.3
entity-activity queries shared with the
[Flow activity observer](nutanix-flow-activity-readback.md). It carries no
writer-exclusion or recovery authority, and the installed-target filter,
ordering, count and RBAC completeness must be qualified for each entity kind.

## Accepted profile and query

Use `nutanix-ahv-v4.2-prism-v4.3-vm-task-activity` with
`provisioner/execution/nutanix_vm_activity_observe.py`. The manifest has the same fields as the
recorded VM/task profile. Its task graph must still be explicitly enumerated.
`task.created_after` is also the activity cutoff; `created_before` must be no
later than observation start. For interrupted-change review, the lower bound
must equal the original attempt time, including when older pending work exists.

Each round queries the Prism v4.3 task collection for each exact VM, samples the
recorded tasks and VM state, then repeats those activity queries. The fixed OData
predicate selects tasks affecting that VM which are either nonterminal or have
completed at or after the cutoff. Pending work has no creation-time cutoff and
the query has no task-owner filter. A caller cannot provide arbitrary filters,
URLs, sort fields or pagination links.

The reader requests ascending task `extId`, zero-based pages of 25 rows, at most
four pages per VM and at most 100 rows across all VM queries in each phase. A
shared task counts against the aggregate limit each time it occurs in a VM query.
Collection totals must remain constant; every expected page and row must be
present, sorted and unique within that query. Query diagnostics, unsupported
statuses, contradictory affected entities/timestamps, changed totals, missing
pages and any exceeded limit hold the observation. Existing request/time limits
also apply. Failed GETs are not retried and response links are never followed.

The exported activity witness contains only task identity, operation, status,
creation/completion times and complete affected-entity IDs. Each VM's activity
must equal the explicitly recorded tasks affecting that VM, agree with their
direct GET witnesses, and remain unchanged across the sample. An extra task
holds even if it completed successfully and the VM matches. The collector does
not silently add it to the accepted graph. Task diagnostics and guest content
are excluded from the report.

## Collection and offline review

Validate without native contact:

```sh
python -m provisioner.execution.nutanix_vm_activity_observe /private/accepted-ahv-activity.json
```

For an independently authorized read, set the manifest's `contact_enabled: true`,
inject scoped read-only `NUTANIX_USERNAME` and `NUTANIX_PASSWORD` through the site
secret service, and provide the exact origin, CA and new private output:

```sh
python -m provisioner.execution.nutanix_vm_activity_observe /private/accepted-ahv-activity.json \
  --read-authorized-target --expected-origin https://actual-prism-host \
  --ca-file /private/prism-ca.pem --output /private/new-ahv-activity-report.json
```

Two complete stable rounds are required. The additional `task-activity` resource
records activity coverage and keeps `task_completion_observed: false`; the VM
resources independently carry the recorded graph's completion result. The
[offline recovery reviewer](../../INTERRUPTED_CHANGE_RECOVERY.md) recomputes both
sets of witnesses and retains the external fencing, quarantine, generation and
containment requirements. Report/context consistency does not authenticate those
external controls.

[Campaigns v3/v4](target-qualification.md) dispatch this profile from the bound
workload manifest, preserve exact ownership/subnet/Flow bindings and include the
report in their combined before/after hashes. Unknown, pending, failed, changed
or extra activity stops the campaign. The snapshot and recorded-task profiles
remain separate choices; neither substitutes for activity in held AHV review.

## Installed-target qualification

The SDK defines the task-list endpoint, query parameters and response metadata.
It does not establish that a selected installation supports this reader's exact
affected-entity/status/completion predicate, `extId` ordering or filtered total
semantics. Qualify these assumptions, pagination, task retention and cross-writer
RBAC visibility on the actual VMM v4.2/Prism v4.3 tuple before accepting evidence.
An unsupported response holds; there is no API negotiation or weaker fallback.

Loopback TLS and offline regressions use scripted responses. Even on a qualified
target, activity queries do not establish absence of hidden, expired, future,
synchronous or cross-entity work that is not attributed to the selected VMs.
Actual native writer exclusion and operation-wide reconciliation remain required.
Follow the [commissioning cases](site-commissioning.md); local results cannot
populate native acceptance indexes or prove HA/security/application recovery.

Wire-contract references: vendor
[Tasks API](https://github.com/nutanix/ntnx-api-golang-clients/blob/prism-go-client/v4.3.1/prism-go-client/api/tasks_api.go),
[list request](https://github.com/nutanix/ntnx-api-golang-clients/blob/prism-go-client/v4.3.1/prism-go-client/models/prism/v4/request/tasks/list_tasks_request.go)
and [response metadata](https://github.com/nutanix/ntnx-api-golang-clients/blob/prism-go-client/v4.3.1/prism-go-client/models/common/v1/response/response_model.go).
