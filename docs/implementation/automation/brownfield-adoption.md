# Brownfield discovery, ownership transfer and Terraform adoption

Brownfield onboarding is an ownership transfer, not a shortcut around normal
provisioning controls. Existing infrastructure must be discovered and protected
before Terraform state becomes authoritative.

The repository implements this in two layers:

1. `tools/adoption.py` reviews native ownership, recovery, state protection and
   the intended non-destructive handover;
2. `tools/terraform_adoption.py` prepares and, only after a separate approval,
   performs exact Terraform state imports under the same backend writer lock used
   by normal Terraform apply.

Neither layer declares the adopted service qualified or production-ready.

## 1. Adoption ownership record

A `hosting-adoption/1` plan binds one source revision, WSD scope, state boundary
and complete resource set.

Each resource records:

- Terraform/native address and resource type;
- exact native identity;
- current and target owner;
- `retain_existing` or `handover_to_terraform`;
- whether the resource is shared;
- `observe_only` or `terraform_import`;
- exact import ID when Terraform will assume ownership;
- current and desired configuration digests;
- `no-op` or explicit `update`;
- change class and bounded update fields;
- discovery and recovery evidence references;
- the old-writer fence when ownership moves to Terraform.

The current/desired hashes are hashes of the **accepted normalized configuration
projection used by the owning engineering process**. They are not hashes of raw
vendor responses or Terraform plan JSON. Exact Terraform plan bytes are bound
separately by the adoption bundle and approval.

Shared resources cannot be transferred by this contract. They remain under their
existing owner and are consumed through accepted references/data sources. A
Terraform handover requires the old writer to be fenced before import.

## 2. Evidence required before import

`hosting-adoption-evidence/1` binds the exact adoption-plan digest and requires:

- the exact backend/state key;
- verified state backup and writer locking;
- complete evidence for every reviewed resource;
- unchanged native identity, owner and normalized current configuration;
- a verified recovery path;
- a supported import/adoption mechanism;
- no replacement, deletion or new exposure;
- the old writer inactive for resources being transferred;
- the retained owner still active for resources not being transferred.

The review emits
`ADOPTION_READY_FOR_EXPLICIT_IMPORT_AND_PLAN_REVIEW`, an exact list of imports,
retained owners and any explicit deltas. It still sets
`may_import_automatically: false`, `may_apply: false`,
`may_replace: false` and `may_delete: false`.

Standalone review:

```sh
python tools/adoption.py \
  --plan /private/adoption-plan.json \
  --evidence /private/adoption-evidence.json \
  --output /private/adoption-review.json
```

The command requires the plan's exact clean source revision.

## 3. Prepare the Terraform adoption bundle

The import executor reuses the registered WSD composition, pinned Terraform
binary, private HTTP backend, scoped credentials and trust model from the normal
reviewed Terraform executor.

Preparation requires:

- accepted WSD inputs;
- the exact backend and state key named by the adoption plan;
- private credentials and optional OpenStack cloud/CA material;
- the adoption plan and evidence;
- `hosting-terraform-adoption-contact/1` authority.

The contact record binds source, six-field Terraform scope, operation/generation,
input/backend/credential/cloud/CA digests, the exact adoption-review digest and a
current change window.

```sh
python tools/terraform_adoption.py prepare \
  --catalog-id vmware-wsd-workloads \
  --inputs /private/inputs.json \
  --backend /private/backend.json \
  --environment /private/credentials.json \
  --authority /private/adoption-contact.json \
  --adoption-plan /private/adoption-plan.json \
  --adoption-evidence /private/adoption-evidence.json \
  --terraform /opt/terraform/bin/terraform \
  --output /private/adoption-run-001 \
  --read-authorized-target
```

Preparation initializes the exact backend and creates a saved **pre-import** plan.
Every handover address must appear as one configured `create` because it is not
yet in state. Every other managed resource must be `no-op`. Moved, deposed or
already-importing records hold. The existing restricted plan reviewer still runs;
a blocked plan cannot become an adoption bundle.

Preparation does not import anything.

## 4. Execute explicitly approved imports

A separate `hosting-terraform-adoption-approval/1` binds:

- adoption bundle digest;
- adoption review digest;
- pre-import plan digest;
- pre-import review digest;
- operation/generation;
- current validity window;
- change reference.

Execution uses the same backend-scoped writer lock as normal Terraform apply.
Before the first import it durably records
`STARTED_OUTCOME_UNKNOWN`. A process failure or uncertain result therefore
blocks both later adoption and ordinary Terraform apply until the state/native
outcome is reconciled.

```sh
python tools/terraform_adoption.py execute \
  --bundle /private/adoption-run-001 \
  --approval /private/adoption-approval.json \
  --terraform /opt/terraform/bin/terraform \
  --ledger /private/terraform-ledger \
  --execute-approved-import
```

Only the exact reviewed resource addresses and import IDs are passed to
`terraform import`. There is no shell expansion, arbitrary argument surface,
automatic force-unlock, state removal, destroy or import retry.

If any command fails or the process is interrupted, the result is held as
`HOLD_ADOPTION_RECONCILIATION_REQUIRED`. The executor never retries an import
whose outcome may be uncertain.

## 5. Mandatory post-import plan

After every import succeeds, the executor creates a fresh saved plan from the
new state.

For each adopted object:

- a reviewed no-op adoption must now be exactly `no-op`;
- an explicit delta must remain exactly `update`;
- changed top-level fields may not exceed the adoption plan's bounded
  `allowed_update_fields`.

Every unrelated managed resource must remain `no-op`. Create, delete,
replacement, moved/deposed ownership, hidden import state or an unreviewed field
change holds the operation.

The existing restricted plan reviewer is also run over this post-import plan.
Successful state adoption ends at
`ADOPTED_REQUIRES_EXACT_DELTA_PLAN_REVIEW`.

That status **does not apply the delta**. Run the ordinary reviewed Terraform
plan/apply process with a new operation/generation if a separately approved
change is still required.

## 6. Delivery-runner stages

The persistent coordinator supports:

- `adoption_review` — ownership/evidence review only;
- `terraform_adoption_plan` — exact pre-import Terraform bundle preparation;
- `terraform_adoption_apply` — explicitly approved state import.

The apply stage depends on its exact preparation stage. A completed import can be
recovered read-only if the coordinator loses only its final handoff publication.
A held/unknown import is never redispatched by recovery.

## Remaining W24 native work

This increment implements the repository-side ownership and Terraform import
path. W24 still requires actual platform/service evidence for each offered
brownfield environment, including:

- complete physical/logical dependency discovery;
- accepted old-writer fencing on the real management system;
- actual provider import support and installed-version semantics;
- native identity/configuration readback after adoption;
- canary operation and service/security verification;
- recovery from an intentionally interrupted import/change;
- same-service re-creation and portable data/workload transition where offered;
- synchronization, cutover, failback and stale-source fencing for any offered
  migration/recovery service.

A state record is never substituted for those results.
