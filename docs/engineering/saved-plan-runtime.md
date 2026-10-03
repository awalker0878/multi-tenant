# Package-owned saved-plan and lifecycle runtime

Reviewed 3 October 2026, continuing the operator/readback dependency migration.

| Implementation | Installed owner | Authority boundary |
|---|---|---|
| Restricted saved-plan review | `provisioner.execution.plan_review` | Conservative offline findings; no approval |
| Flow rule binding | `provisioner.execution.flow_policy` | Existing exact rule semantics; no native mutation |
| OpenStack transition record | `provisioner.execution.openstack_transition` | Exact prior outputs/inputs and accepted stage |
| Platform transition record | `provisioner.execution.lifecycle_transition` | Existing plan/native identity binding |
| Terraform plan preparation | `provisioner.execution.terraform_run` | Existing scoped contact authority and explicit native-read opt-in |
| Saved-plan application | `provisioner.execution.terraform_apply` | Existing exact approval, durable start and uncertainty ledger |
| Execution output handoff | `provisioner.execution.wsd_handoff` | Prior receipt/current intent checks; not Service Ready |

All active consumers moved to the implementations. Old paths are deleted and
registered as retired, not wrappers. Use `python -m` with the installed module.
The existing preparation and apply commands additionally take `--source-root`:

```sh
python -m provisioner.execution.terraform_run --help
python -m provisioner.execution.terraform_apply --help
```

Outside marked source development, absence of an explicit checkout is a hold before
private inputs or native effects. The selected checkout still must be clean and
match the contact/approval source commit. `source_integrity.verify_runtime` also
compares running package-owned Python/data and execution-resource bytes and sets
with that checkout, including package-referenced qualification documents. This
prevents attributing an installed executor to unrelated clean source. Reads are
bounded, reject links and preserve files. Third-party dependency validation,
signature trust, hostile-writer exclusion and native qualification remain separate.

Package/resource locations never become a fallback native execution checkout.
Source snapshots, Terraform/provider credentials, owner-only artifacts, plan and
transition identities, backend locking, durable starts, uncertain completion and
independent native/guest acceptance retain their original contracts. No old record
is imported or silently reauthorized; lifecycle default removal still requires the
retained-state conversion and reconciliation gates.

Installed-wheel tests block all legacy imports, exercise conservative review, prove
missing/mismatched source refuses before I/O, and verify explicit checkout argument
forwarding. Source-binding tests cover changed/extra/missing/linked/bounded code and
resources. Existing plan, transition, execution, handoff, guest-source and controller
regressions retain their positive and negative assertions.

B05 remains open for other execution owners and installed service composition; B23
native transactional composition, B48 conversion and final native/operating
acceptance are not closed by this relocation.

## Verification boundaries

The preceding operator/readback revision's architecture run
[37129861885](https://github.com/awalker0878/multi-tenant/actions/runs/37129861885)
failed in the Ansible job because its role still constructed the retired Neutron
path dynamically. Package, repository, Terraform, PostgreSQL/control-plane and
Temporal recovery jobs passed there; that overall run remains failed. This
continuation migrates that exact role path and the local Ansible gate passes.

The first saved-plan full regression exposed source-fixture use of the retired
transition `ROOT` attribute and architectural guards that misclassified relocated
native owners as generic code. Fixtures now take the canonical source root. The
guards pin exact pre-existing native branches and one saved-plan ledger owner;
arbitrary branches/journals remain refused. Original failed results remain failed,
and final source-specific reruns are recorded separately.

Final local verification: 4,396 regression tests, zero failures/errors, 123 skipped
integration tests; 80 modeled route checks passed. The actual Ansible syntax,
local staging/idempotence/check-mode and no-contact negative campaign passed. The
installed wheel check and its 15 distribution tests passed, including package/source
binding and stale-build retirement. Documentation, repository and retirement gates
passed. PostgreSQL/native integration skips are not passing native acceptance.

The final ledger guard additionally pins the single existing `flock` call to
`scope_ledger`; a focused rerun verifies it. Hosted CI remains the final exact-commit
verification after publication. No site, native workload or production dataset was
contacted in this continuation.
