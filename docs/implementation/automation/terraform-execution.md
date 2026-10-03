# Reviewed Terraform execution

`provisioner/execution/terraform_run.py` prepares a private saved-plan bundle for one registered
WSD domain or workload root. This is an operator tool for an already selected,
authorized native target. Hosted PR checks never invoke it against a platform.

`provisioner.execution.terraform_catalog` reads the explicitly registered writer scopes
from `terraform/catalog.json` without assuming a fixed count. The former tools module
is deleted; all consumers use the package owner. Its bounded JSON/path checks and
clean incremental build behavior are documented in the
[package catalog contract](../../engineering/terraform-catalog-runtime.md).

## Plan preparation

Use a clean committed checkout, the pinned Terraform executable and private
owner-only storage outside the repository. Supply the root's accepted inputs,
an HTTP backend mapping, an externally issued contact handoff and a credential
environment. All JSON files must be owned by the runner user with mode 0600;
the existing parent output directory must be mode 0700. Symlinks and overwrites
are rejected. Input and backend digests are SHA-256 of the exact file bytes.

The backend JSON contains `state_key`, `address`, `lock_address`,
`unlock_address`, `lock_method` and `unlock_method`. The state key is
`environment/site/platform/tenant/wsd/phase`. Endpoints require HTTPS, explicit
locking and one reviewed server authority. Backend service access controls,
encryption at rest, recoverability and ownership must already be commissioned.

The contact handoff uses format `hosting-terraform-contact/2` and contains
`source_commit`, the six-field output `scope`, `operation_id`, positive integer
`generation`, `input_sha256`, `backend_sha256`, `environment_sha256`,
`cloud_sha256`, `ca_sha256`, `valid_from`, `valid_until` and
`change_ref`. Its contact window must be current and no longer than one hour.
The runner consumes this record from the trusted operator/change system. The
file is not a signature and the runner does not authenticate its issuing human;
protect its custody and restrict who can invoke the runner with native credentials.

The cloud/CA digest is `null` when that optional file is absent. Version 1
contact records are rejected because they did not bind external credential/trust
inputs. Native command timeouts are capped by the remaining contact window.

The credential JSON permits `TF_VAR_platform_password`,
`TF_HTTP_USERNAME` and `TF_HTTP_PASSWORD`. No implicit Terraform CLI flags,
workspace, endpoint overrides, provider development overrides or debug logging
are inherited. All three WSD platform families are supported by the executor.

For OpenStack, supply `--cloud` with a private JSON document containing exactly
one `clouds` entry named by `openstack_cloud`. The profile fields are
`auth_type: v3applicationcredential`, `verify: true`, an explicit `region_name`,
`interface: internal` or `public`, and `auth` containing the HTTPS `auth_url`,
`application_credential_id` and `application_credential_secret`. Use scoped
application credentials from the actual project authority. Arbitrary YAML,
imported vendor profiles and external file references are rejected. The executor
copies the profile into the operation and supplies empty secure/public overlays
so ambient profiles cannot replace its account or project. This follows the
pinned provider dependency's [cloud discovery implementation](https://github.com/gophercloud/utils/blob/8f6f0255f600/openstack/clientconfig/utils.go).

For an enterprise trust anchor, supply a private `--ca-bundle` PEM file; its
bytes are bound by contact authority and the bundle. Ambient TLS overrides are
not inherited. Credential or trust changes require a new reviewed plan.

```sh
python -m provisioner.execution.terraform_run \
  --catalog-id nutanix-wsd-domains \
  --inputs /private/operator/inputs.json \
  --backend /private/operator/backend.json \
  --authority /private/operator/contact.json \
  --environment /private/operator/credentials.json \
  --terraform /opt/terraform/bin/terraform \
  --output /private/operator/run-001 \
  --read-authorized-target
```

Preparation copies committed Terraform source, initializes only the selected
backend with read-only provider locks, creates a locked saved plan and derives
its JSON through that same engine's `show -json`. It runs the existing restricted
plan reviewer. Blocked changes cannot produce an executable bundle. Findings
requiring review remain visible and are not automatically approved.

The resulting bundle binds the source commit, exact source/runtime files,
Terraform binary, input/backend/credential artifacts, binary plan, derived plan
JSON and review. Plans, credential files, native endpoints and full logs remain
private. Console output includes only status and the bundle digest. Preserve
failed operation directories for review; never promote them by editing their
contents.

## Saved-plan application

Review the complete private plan and every finding. An externally controlled
`hosting-terraform-approval/1` record must identify `bundle_sha256`,
`review_sha256`, `operation_id`, `generation`, `valid_from`, `valid_until` and
`change_ref`. The review digest covers the entire review JSON, including findings
requiring independent engineering/native evidence. The record consumes actual
change approval; it does not manufacture that approval. The maximum apply window
and plan age are one hour. Apply from the same clean source revision and binary.

```sh
python -m provisioner.execution.terraform_apply \
  --bundle /private/operator/run-001 \
  --approval /private/operator/approved.json \
  --terraform /opt/terraform/bin/terraform \
  --ledger /private/operator/execution-ledger \
  --execute-approved-change
```

Before admitting a new attempt, the executor now replays every immutable
start/completion pair in the backend scope. Missing starts, missing results,
orphan results, changed identity/scope, overlapping chronology and a missing or
inconsistent head all hold. This includes interruption after the durable start
but before head publication: a renamed operation cannot bypass that window.
Historical completion is checked without renewing its apply authority.

The ledger directory must already exist with mode 0700. All writers using this
executor must use the same durable ledger and canonical backend address. A
POSIX advisory lock serializes this executor's writers for that backend, while
Terraform's backend lock protects state. The executor records and fsyncs a
started/unknown outcome **before** invoking the exact saved binary plan. No new
plan, automatic retry, destroy, force-unlock or rollback is invoked during apply.

A timeout, interrupt, failed apply, missing output or mismatched output leaves
the scope held for independent native reconciliation. A process killed before
it can record failure leaves its durable started/unknown record. Reusing the
same operation/generation is rejected even from a copied bundle. A successful
apply captures scope-checked outputs for the next phase and remains explicitly
`APPLIED_REQUIRES_NATIVE_ACCEPTANCE`.

These filesystem locks do not fence another tool or a native task still running
after a controller dies. Actual cross-writer exclusion, native task discovery,
approved reconciliation and controlled ledger recovery must be integrated with
the selected platform/change service before unattended execution. There is no
automatic command to clear an uncertain record. Do not delete a ledger to retry.

The [vSphere held-attempt reviewer](terraform-recovery.md) can bind current native
task-tree and VM activity observations to the exact saved plan, known existing VM
identities and current immutable attempt records. The activity window must equal
the immutable attempt start; known-task-only profiles cannot substitute for it.
It writes a separate private packet under the
existing executor lock and leaves every ledger byte unchanged. Creates, replacements,
deletes and unknown identities require separate ownership/adoption reconciliation.

## Delivery boundary

This increment supplies restricted plan/apply execution and durable attempt
records. OpenStack bootstrap/withdrawal additionally requires the
[exact transition contract](openstack-bootstrap.md), passed to preparation with
`--transition`; it is sealed and rechecked at apply. The same argument accepts
the [VMware/Nutanix transition contract](platform-lifecycle.md) for NSX domain
connectivity/service rules, Flow domain service rules and AHV workload power/NIC changes. Those records
also preserve all non-lifecycle input values and bind prior native identities.
This does not install a
backend, qualify a platform, commission edge connectivity, activate production,
authenticate approval signers, or prove native recovery. Retention and field-ownership constraints remain
effective. Success must be followed by independent native observation and the
remaining service gates.

## Handoff into workloads and guests

Successful domain runs can feed workload compilation without editing native ID
maps by hand. Each run's bundle, result, exact output bytes, scope, operation and
generation are checked. Domain inputs must match the current environment intent;
missing, duplicate, foreign, uncertain or older-than-24-hour runs are rejected.

```sh
python -m provisioner.execution.wsd_handoff \
  --environment /private/operator/environment.json \
  --domain-run /private/operator/tenant-01-domains \
  --domain-run /private/operator/tenant-02-domains \
  --output /private/operator/workload-drafts
```

For VMware, also supply the independently observed NSX-segment/vCenter-network
map through `--vmware-bindings`. The compiler never guesses that association.
Generated inputs remain disabled and quarantine acceptance references remain
empty. Terraform outputs do not replace native observation or capacity/IPAM
authority. The handoff retains the source and execution provenance for each WSD.

After a separately reviewed workload apply and accepted bootstrap/access handoff:

```sh
python -m provisioner.execution.guest_inventory /private/operator/guest-access.json \
  --workload-run /private/operator/tenant-01-workloads \
  --output /private/operator/guest-inventory
```

This verifies the successful workload receipt before using the existing pinned
SSH and observed machine-identity checks. Building an inventory still does not
open SSH or activate a service.

See [WSD deployment](wsd-deployment.md), [delivery process](delivery-process.md)
and [acceptance gates](acceptance.md). Terraform documents the sensitive contents
and exact-plan workflow in its [plan reference](https://developer.hashicorp.com/terraform/cli/commands/plan).
