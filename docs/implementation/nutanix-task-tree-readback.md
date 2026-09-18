# Observe a recorded Nutanix task tree

**Scope:** bounded, read-only observation of a recorded platform operation and its
selected VPC/subnet resources. The [engineering profile](../engineering/nutanix-task-tree-readback.md)
is the prerequisite; this is not permission to enable a native endpoint or cancel work.

## Accepted operation handoff

The platform writer or its accountable operator must preserve the actual task IDs,
parent relationships, operation names, creation interval and affected resources from
the change record. Keep independently controlled evidence for the expected native
tenant, object fields, ETags, current change generation, writer control and quarantine.
Neither a supplied graph nor a signed-looking record name proves its own authority.

The optional profile is `nutanix-networking-prism-v4.3-task-tree`. Common manifest
fields and resource expectations remain those of the [existing reader](../NATIVE_READBACK.md).
The `task` section contains:

| Field | Meaning |
|---|---|
| `ext_id`, `operation` | Exact recorded root identity and expected native operation |
| `created_after`, `created_before` | Accepted task-creation interval with timezone; not a new approval lifetime |
| `entity_ids` | Exact selected VPC/subnet resource set affected by the root |
| `descendants` | 1–15 explicit child records, each containing `ext_id`, `operation`, `parent_ext_id` and exact `entity_ids` |

Children may reference only the root or another listed child. Cycles, unknown parents,
duplicate IDs, more than four parent/child levels and cross-native-tenant resource
sets are rejected before contact. An empty child entity list is an explicit expectation,
not permission to ignore an unknown effect. There is no wildcard or arbitrary URL.

[The disabled example](../../examples/nutanix_task_tree_observation.json.example) uses
synthetic identities, operation labels and empty fixture IP data. It is an assertion
shape, not a deployable engineering design. Its fixed dates are not reusable approvals.
It defaults to no native contact and must not be enabled by changing one Boolean alone.

## Validate without contact

```sh
python tools/nutanix_observe.py examples/nutanix_task_tree_observation.json.example
```

Expected result: `INPUT_VALID_NO_CONTACT`. This checks shape and the six planned exact
GET targets in that four-task/two-resource example. It observes no native state.
The existing single-task example and profile retain their original behaviour.

For separately authorized native reading, obtain the accepted manifest, origin and CA
bundle, inject `NUTANIX_USERNAME` and `NUTANIX_PASSWORD` through the approved runner,
and use the existing explicit contact command. Never put credential values in files,
command arguments or review comments. A documentation `.invalid` endpoint is refused.

```sh
python tools/nutanix_observe.py /secure/accepted-tree.json \
  --read-authorized-target --expected-origin https://pc.site.invalid:9440 \
  --ca-file /secure/approved-ca.pem --output /secure/observation-new.json
```

The target above is intentionally unusable. Actual target selection remains an owner
and security decision. The default three bounded rounds are observations, not automatic
native retries. The command returns nonzero on pending/unknown/failed/different state.
Use a new output name for a new deliberate observation; an existing output is never
silently overwritten. An interruption leaves an incomplete journal, not a successful
readback reconstructed from old evidence.

## Review partial and uncertain outcomes

A 404 does not prove deletion or non-execution. A failed child can coexist with real
resources and a successful parent. Missing child coverage, changed task identity,
unexpected diagnostics or unsupported batch metadata requires owner investigation.
Do not fill missing entries with guessed IDs, discard extra affected entities, relax
the count requirement or resubmit the operation to obtain a cleaner report.

The offline `recovery_review.py` command accepts the new profile through the same
manifest/readback/context procedure. It now independently rechecks the bounded task
witness and history at each recorded observation time, as well as existing report integrity, age, owner scope and control
records. An accepting review result is still only `READY_FOR_OPERATOR_RECOVERY_REVIEW`;
all apply/delete/activate flags remain false. Keep the current incident restriction
and preserve data. Repair, import, cancellation and retirement need their own accepted
native procedure and responsible writer.

## Local verification campaign

```sh
python -m unittest tests.test_nutanix_task_tree -v
python lab/run_task_tree_lab.py --execute
```

Both use the existing disposable loopback HTTPS fixture. The first includes graph,
identity, complete-child and entity sets, limits, response types, timestamps, state
transitions, version conflicts, report tampering, credential handling and actual CLI
input/output regressions. The second executes 18 connected readback/recovery cases,
including the CLI with a real polling delay. Payloads and task transitions are
scripted; external fencing/quarantine records are deliberately simulated.

The CLI campaign writes a NEW private `build/reports/local_task_tree_readback.json`
with exact implementation hashes and per-case requests, task/resource witnesses and
recovery results. It includes successful and expected-hold cases; a case passes only
when both observed readback and recovery disposition equal its declared expectations.
No raw native diagnostic text or fixture credentials are exported. The full repository
unit suite reruns its overlapping cases separately; counts are not additive native
acceptance coverage.

CI runs this fixed campaign in the unprivileged repository job alongside documentation
and unit checks. Terraform/Ansible and routed IPv4/IPv6 jobs remain independent. Exact
PR and post-merge artifact identities determine release status, not an old successful
run or a self-declared source record. Native compatibility, full inventory and actual
writer fencing remain not run until the separately approved native campaign exists.

[Engineering and exclusions](../engineering/nutanix-task-tree-readback.md) · [Interrupted change procedure](../INTERRUPTED_CHANGE_RECOVERY.md)

The [native-reference commissioning kit](native-reference/README.md) remains the planning and ownership context. This reader supplies only its declared task/resource observation; it does not populate the kit’s NOT_RUN native assertion groups with scripted laboratory results.
