# OpenStack native adapter components

Owner: Lifecycle/Infrastructure. Scope: P07.02 and the P07.05 uncertain-effect
boundary. These components do not complete P07 or authorize a native campaign.
Use the [commissioning procedure](openstack-commissioning.md) and
[completion packet](../../implementation/p07-completion-review.md) together.

## Delivered boundary

The Lifecycle worker now supplies a saved-plan process adapter, worker-owned
PostgreSQL attempt journal, exact-ID Nova/Neutron/Cinder readback and a reusable
Terraform module. The read-only `lifecycle-native-inspect` command composes the
actual tooling and readback adapters. `SavedPlanExecution` supplies the tested
effect protocol through its typed current-authority port. The subsequent
[native workflow control](native-workflow-control.md) supplies durable Lifecycle
grants, an internal boundary handler and the worker TLS client. Commissioned
current-owner composition, provider fencing and product native dispatch are still
required before that path can be enabled.
P06 remains simulation-only. There is no CLI apply, auto-replan, force-unlock,
automatic retry, activation or retirement option.

## Protected runtime inputs

Inventory API collection and Console review remain the source of installed facts
and manual inputs. The native worker consumes their protected commissioning
export, not a checked-in environment template. Do not copy credentials or native
state into Git, job output or chat. Binding fields are the product tenant, site,
application, job, operation, attempt, campaign and executor IDs; Keystone project;
custody epoch; plan/bundle hashes; workspace; state lineage/serial; and expiry.
Keystone's compact 32-character project/user IDs and canonical UUIDs are supported.

The runtime export contains `terraform_executable`, `bundle_root`, `environment`,
`credential_files` and `observer`. The observer contains `user_id`,
`writer_user_id` and four `endpoints`: `identity`, `compute`, `network`, `volume`.
Each endpoint names a trusted HTTPS `base_url`, literal `address`, `ca_file` and
the same scoped read-only `token_file`. Catalog prefixes are preserved. Returned
links, redirects and environment proxies never choose readback destinations.
The native credential owner must independently confirm observer permissions and
separation; distinct configured IDs alone do not establish receiving acceptance.

The private, pre-initialized Terraform bundle contains `bundle.json`, the saved
binary plan, `.terraform.lock.hcl`, all module/provider bytes and backend metadata.
Its manifest uses schema version 1, exact Terraform version/executable hash,
`saved_plan`, canonical `plan_json_sha256`, `environment_sha256`, exhaustive
relative `files` hashes and a `resources` mapping of address to `kind`/`expected`.
No unlisted files, symlinks, nonregular inputs or group/world-writable files are
accepted. The commissioning execution environment must supply read-only artifact
mounts and controlled provider egress; hashing alone does not enforce those controls.

Public environment values are allowlisted. OS application credential ID/secret
come only from absolute protected files. Ambient provider credentials,
`TF_CLI_ARGS`, insecure TLS flags and plugin overrides are not inherited. The
exact root dependency lock remains the installation selection. The module's broad
compatibility declaration is not an execution-time version pin.

## Inspection and readback

```sh
lifecycle-native-inspect --binding /protected/binding.json --runtime /protected/runtime.json
lifecycle-native-inspect --binding /protected/binding.json --runtime /protected/runtime.json --observe
```

The first command checks actual executable/module/provider/plan bytes, workspace,
state lineage/serial, reviewed JSON and resource semantics. The initial adapter
supports an HTTPS HTTP backend with explicit lock/unlock endpoints. HTTP uses its
default workspace with a separately scoped backend per managed application.
Other backend adapters remain unsupported. A supplied backend record does not
prove custody, locking, fencing or recovery qualification.

The current plan interpreter admits only reviewed creates of servers, ports and
volumes. It rejects replacement/deletion/update, imports/moves, drift, deferred or
incomplete plans, unexpected providers/resources and provisioners. Ownership
markers use stable tenant/application IDs; embedding the saved-plan digest into
the plan itself would introduce a circular identity.

The module supplies multiple workloads/NICs, fixed IPv4/IPv6 inputs, independent
compute/storage placement, explicit security groups and boot-from-volume mappings.
All application ports start administratively down. Config drives can deliver
pre-approved image metadata without opening application traffic. Boot volumes have
`prevent_destroy` and `delete_on_termination=false`. This is infrastructure
preparation, not a guest hardening profile, allocation receipt or service integration.

Readback validates the current observer's Keystone project/user and token expiry,
then reads exact state IDs with Compute 2.1 and Volume 3.0. Token rotation requires
another scope read. Native project, ownership markers, disk/NIC mappings, fixed
addresses, security groups and quarantine state must match. A hidden Cinder project
attribute uses the validated project-scoped token plus exact object ID and ownership
metadata; actual observer visibility still requires native qualification.

Missing IDs, 404, duplicate/tainted/deposed state, changed attributes, incomplete
state or inaccessible APIs remain held. Even `observed_present` means only that
the specified infrastructure fields were observed. It never reports application
readiness, safe absence, permission to retry or traffic activation.

## Durable effects and recovery limits

Apply `workers/lifecycle/migrations/native/001_attempts.sql` as a separately
administered `native_owner` to its owned database after creating a login-only
`native_runtime` role. Runtime receives only INSERT/SELECT and sequence usage.
It cannot update/delete claims, remove workspace holds or rewrite observations.
Do not run migrations with runtime credentials or use the Lifecycle database.

Before any effect, the owning protocol checks current authority and commits a
unique operation/attempt plus state-lineage hold. Competing, rebound, expired and
previously attempted work cannot launch another create. Execution invokes the
exact saved plan with state locking, zero lock wait and bounded parallelism. No
apply-time plan, target, extra variables or unlocked apply can be supplied.
Output is private and bounded; receipts never retain Terraform stdout/stderr.

Authority is checked again immediately before process launch and while it runs.
Deadline, output overflow or lost authority kills the complete local provider
process group. **Polling and process death do not fence an already accepted
provider operation.** Current native grant redemption, provider-side request
fencing, independent state custody and restored-journal reconciliation remain
required before product native dispatch may be enabled. No local claim implements
that missing authority or qualifies backend recovery.

On loss, restart, partial failure or failed readback, retain the hold. Read-only
observation remains available after write authority expires. The component has no
runtime path to release a hold or claim sealed absence. Recovery, managed change,
activation and retirement need their separately approved workflows and original
native observations; do not delete journal rows to make a retry possible.

## Verification

`scripts/p07/qualify_native.py` runs worker quality checks, real PostgreSQL
competition/privilege/reconnect tests, real TLS with synthetic API responses,
subprocess cancellation and saved-plan command checks. It also verifies a pinned
Terraform 1.13.5 binary and OpenStack provider 3.4.0 dependency lock, validates the
module and exercises a mocked multi-workload plan. Those are development test
artifacts, not a selected or E3-qualified installation tuple. The hosted P07
workflow requires persistence tests to run without skips and retains original logs.
The [verified component index](../../../verification/p07/native-components/qualification-index.json)
retains 112 passing worker tests, all ten command logs, three P06 browser regression
campaigns and development image admission. Original failed observations and their
corrections remain separately identified.

References: [saved-plan apply semantics](https://developer.hashicorp.com/terraform/cli/commands/apply),
[plan JSON](https://developer.hashicorp.com/terraform/internals/json-format),
[Nova API](https://docs.openstack.org/api-ref/compute/),
[Neutron API](https://docs.openstack.org/api-ref/network/v2/),
[Cinder API](https://docs.openstack.org/api-ref/block-storage/v3/) and
[provider resources](https://github.com/terraform-provider-openstack/terraform-provider-openstack/tree/main/docs/resources).
