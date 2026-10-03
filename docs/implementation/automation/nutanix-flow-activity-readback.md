# Flow policy task activity and held-attempt review

`provisioner/execution/nutanix_flow_activity_observe.py` composes the exact
[Flow policy snapshot](nutanix-flow-readback.md) with a recorded Prism task graph
and bounded visible task queries. Its explicit profile is
`nutanix-microseg-v4.2-prism-v4.3-policy-task-activity`. The installed target must
support both microseg v4.2 and Prism v4.3. Failure never selects a weaker profile.
The bounded Prism v4.3 entity-activity queries come from the shared
`provisioner/execution/nutanix_entity_activity.py`.

## Accepted scope and read sequence

Use the same common envelope and policy resources as the snapshot profile, plus
`task` with exactly `ext_id`, `operation`, `created_after`, `created_before`,
`entity_ids` and `descendants`. Task IDs and exact operation labels come from the
original writer trail and independent native-owner review, not guessed names.
Each descendant supplies `ext_id`, `parent_ext_id`, `operation` and `entity_ids`.
The root must affect exactly the selected policy UUIDs; descendants may affect
only that set. Mixed policy/category/VPC/VM operations require separate review.
The accepted graph contains 1–16 tasks, no cycles, and at most four levels of
parent-child edges. The creation window is ordered and ends before observation.
For recovery, its lower bound must equal the immutable original attempt start.

Each round reads:

1. Visible task pages for every selected policy.
2. Every recorded task, in parent-first order.
3. Exact policy configuration and strong ETag.
4. Every recorded task again, in reverse order.
5. Visible task pages for every selected policy again.

Only fixed GETs are permitted: exact microseg policy paths, exact Prism task
paths, and `/api/prism/v4.3/config/tasks` with a generated filter. The filter
selects the policy through `entitiesAffected`, pending work without an age cutoff,
and terminal work completed since `created_after`. It orders by `extId asc` and
uses `$page`/`$limit`: 25 records per page, at most four pages per policy and 100
aggregate rows per before/after phase, counting shared tasks in each policy query.
Metadata totals must be constant, pages complete, IDs sorted and unique, statuses
recognized, and affected-entity counts complete. Response links are never followed.
There is no caller-provided query, native task discovery/adoption, cancellation,
policy write or replay. Existing transport/round/request/deadline limits also apply.

Activity must exactly equal the recorded tasks affecting each policy and agree
with direct task identities, operations, timestamps, statuses and full entities.
Missing, extra or changing activity holds. Successful tasks still require complete
ancestry/children, accepted chronology and no diagnostics requiring review.
Pending, failed and uncertain work retain their distinct hold outcomes.

## Private collection and review

Validate without contacting any endpoint:

```sh
python3 -m provisioner.execution.nutanix_flow_activity_observe /private/site/flow-activity.json
```

After scoped read authorization, inject `NUTANIX_USERNAME` and `NUTANIX_PASSWORD`
and collect with the independently accepted origin and trust root:

```sh
python3 -m provisioner.execution.nutanix_flow_activity_observe /private/site/flow-activity.json \
  --read-authorized-target --expected-origin https://accepted-prism.example.invalid \
  --ca-file /private/site/native-ca.pem --output /private/operator/new-flow-report.json
```

The example origin is a placeholder, not site inventory. `contact_enabled` must
be explicitly true in the accepted manifest. Preserve the private report, which
contains selected task witnesses, page counts and policy hashes/shape verdicts,
not complete response bodies or diagnostic text. Offline review recomputes task
and activity witnesses and checks the policy digest, ETag and full-shape verdict.
A hidden alternate selector cannot be dismissed by changing only the summary to
MATCH. These are consistency checks, not signatures or authenticated collection.
Older reports without policy witnesses must be recollected.

[Campaign v4](target-qualification.md) selects either the snapshot or activity
reader from the bound Flow manifest. It preserves domain/category/VPC/VM ownership
checks and binds network, AHV and Flow result hashes before and after traffic.
The snapshot profile continues to make no task-completion claim.

The [held-attempt reviewer](terraform-recovery.md) supports existing Nutanix domain
bootstrap/withdrawal only with this activity profile and the original sealed
transition, input, JSON plan, binary saved plan and durable attempt. It binds every
owned policy, name, category/VPC, exact service intent and retained deny IDs.
New service-rule IDs may be generated only where the original plan explicitly
marks that ID unknown; no policy identity or security configuration may be unknown.
Retained rules require known matching IDs. Unrelated domain resources must be
exact resolved no-ops. Snapshot-only evidence, creation/adoption, replacement,
deletes, incomplete coverage and other mutations are held. Review preserves all
ledger bytes and mutation/activation flags remain false.

## Installed qualification still required

The pinned [Nutanix provider's Flow resource](https://github.com/nutanix/terraform-provider-nutanix/blob/v2.4.2/nutanix/services/networkingv2/resource_nutanix_network_security_policies_v2.go)
uses task references for policy updates and computed rule IDs. The
[microseg policy API](https://github.com/nutanix/ntnx-api-golang-clients/blob/microseg-go-client/v4.2.2/microseg-go-client/api/network_security_policies_api.go)
and [Prism Tasks API](https://github.com/nutanix/ntnx-api-golang-clients/blob/prism-go-client/v4.3.1/prism-go-client/api/tasks_api.go)
define the selected interfaces. Their source does not qualify the installed
filter, ordering, filtered totals, policy attribution or cross-writer RBAC visibility.

Commissioning must prove those semantics, task/history retention, strong ETags,
actual provider defaults/rule identities, and pending/late/failed/mixed-entity cases.
Hidden or expired work, synchronous operations, other entities and future writes
remain outside these observations. Neither an empty activity result nor successful
tasks establish native writer exclusion, policy enforcement or safe activation.
Actual fencing/quarantine, healthy allowed/denied traffic controls, policy precedence,
withdrawal and HA/application recovery must be accepted independently. A blocked
fence or unqualified target keeps the operation held.
