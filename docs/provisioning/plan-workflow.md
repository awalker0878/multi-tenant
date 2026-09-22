# Plan workflow

The command line is a transport. Every command calls the same core library the
pipeline uses; no command decides policy, placement, allocation or authority for
itself. `apply` exists so the refusal is explicit and machine-readable, not so a
change can be made.

Entry point: `python -m provisioner.cli.main <command> <request.yaml>`
Module: `provisioner/cli/`
Result format: `hosting-cli-result/1`

## Commands

| Command | Does | Exit `0` | Exit `2` |
| --- | --- | --- | --- |
| `validate` | syntax, schema, semantics, standards | `VALID` | `REFUSED` with every diagnostic |
| `resolve` | normalize, resolve profiles, validate, policy | `RESOLVED` | `REFUSED` |
| `plan` | the whole pipeline through compilation | `PLANNED_DISABLED_NOT_AUTHORIZED` | `REFUSED` |
| `status` | where the plan stands in the lifecycle | plan status plus reached/held stages | `REFUSED` |
| `verify` | compare observations against the plan | report status | `REFUSED` |
| `evidence` | record the review evidence for a plan | `RECORDED` | `REFUSED` |
| `apply` | always refuses | — | `EXECUTION_REFUSED_REPOSITORY_PLAN_ONLY` |

Exit `3` is an internal failure (an unreadable file, an unknown platform name).

## Options

| Option | Applies to | Meaning |
| --- | --- | --- |
| `--inventory PATH` | all | reviewed inventory; defaults to the non-authoritative fixture |
| `--profiles-root PATH` | all | alternate catalog root; the repository catalogs are the default |
| `--no-compile` | `plan` | resolve the environment document without invoking the compiler |
| `--approved-plan DIGEST` | `apply` | the digest the caller claims was approved |
| `--approvals PATH` | `apply` | recorded external approvals bound to a plan digest |
| `--observations PATH` | `verify` | native observations document |

## `plan`

Produces a `hosting-provisioning-plan/1` document containing the normalized
request, the resolution, the policy summary, the placement decision (with every
rejected candidate), the resolved desired state, the environment document, the
compiled file list, the compile plan scopes, the Terraform and Ansible scopes, the
compiler phases, the delivery plan and the conformance report.

`Plan.digest` is the SHA-256 of the request digest plus the rendered environment
document, so two requests that differ only in an unused field still share a digest
while any real change produces a new one. Two different requests never collide.

Compiler phases:

| Phase | Status |
| --- | --- |
| `domains` | `COMPILED_DISABLED_NOT_AUTHORIZED` |
| `workloads` | `HELD_PENDING_NATIVE_DOMAIN_OUTPUTS` |

## `status`

Reports the lifecycle stages (`request … activated`) split into `REACHED` and
`HELD`, the placement status and authority, the delivery blocking operations and
the conformance summary. It never reports a stage as reached when an earlier stage
did not produce its artifact for the same request digest.

## `verify`

Compares native observations against the plan. Without observations the report is
`NOT_OBSERVED`; nothing is inferred. Verification cannot promote fixture placement
and cannot satisfy an external check.

## `apply`

`apply` requires both a `--approved-plan` digest and a recorded approval whose
`plan_digest` matches the plan the repository would produce. It then **still
refuses** with `EXECUTION_REFUSED_REPOSITORY_PLAN_ONLY`, because this repository
holds no target contact, credential or change authority. The refusal payload names
the external authority, the approval format and the outstanding owner operations.

Approval records are read, never written:

```yaml
approvals:
  - plan_digest: <sha256>
    approved_by: <reviewer>
    authority_ref: <external authority record>
    scope: plan
```

An approval that does not cite a digest, an approver and an authority reference is
refused with `AUTHORITY_REQUIRED`.

## Reference run

```
python -m provisioner.cli.main validate examples/requests/internal-production.yaml
python -m provisioner.cli.main resolve  examples/requests/internal-production.yaml
python -m provisioner.cli.main plan     examples/requests/internal-production.yaml
python -m provisioner.cli.main status   examples/requests/internal-production.yaml
```

All five reference requests currently plan as `PLANNED_DISABLED_NOT_AUTHORIZED`
with `native_contact: false` and one compiled file each; their digests are indexed
in [`examples/golden/digests.json`](../../examples/golden/digests.json).