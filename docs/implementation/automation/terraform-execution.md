# Reviewed Terraform execution

`tools/terraform_run.py` prepares a private saved-plan bundle for one registered
WSD domain or workload root. This is an operator tool for an already selected,
authorized native target. Hosted PR checks never invoke it against a platform.

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

The contact handoff uses format `hosting-terraform-contact/1` and contains
`source_commit`, the six-field output `scope`, `operation_id`, positive integer
`generation`, `input_sha256`, `backend_sha256`, `valid_from`, `valid_until` and
`change_ref`. Its contact window must be current and no longer than one hour.
The runner consumes this record from the trusted operator/change system. The
file is not a signature and the runner does not authenticate its issuing human;
protect its custody and restrict who can invoke the runner with native credentials.

The credential JSON currently permits `TF_VAR_platform_password`,
`TF_HTTP_USERNAME` and `TF_HTTP_PASSWORD`. No implicit Terraform CLI flags,
workspace, endpoint overrides, provider development overrides or debug logging
are inherited. Nutanix and VMware WSD roots are supported; OpenStack cloud-file
custody is an explicit remaining executor dependency.

```sh
python tools/terraform_run.py \
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

## Delivery boundary

The initial increment implements preparation only. Saved-plan application,
durable execution history and uncertain-outcome handling follow as separate
increments. No native campaign or production activation is claimed. Existing
quarantine, retention and field-ownership constraints remain effective.

See [WSD deployment](wsd-deployment.md), [delivery process](delivery-process.md)
and [acceptance gates](acceptance.md). Terraform documents the sensitive contents
and exact-plan workflow in its [plan reference](https://developer.hashicorp.com/terraform/cli/commands/plan).
