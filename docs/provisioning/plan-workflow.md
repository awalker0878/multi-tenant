# Plan workflow

The command line is a transport. Every command calls the same core library the
pipeline uses; no command decides policy, placement, allocation or authority for
itself, and no command imports another command. The operations the commands share —
loading the request, its reviewed inventory and its catalogs, and building the plan
— live in `provisioner/execution/service.py`, below the transport. `apply` exists so
the refusal is explicit and machine-readable, not so a change can be made.

Entry point: `python -m provisioner.cli <command> <request.yaml>`
Module: `provisioner/cli/`
Shared service: `provisioner/execution/service.py`
Result format: `hosting-cli-result/1`

## Commands

| Command | Does | Exit `0` | Exit `2` |
| --- | --- | --- | --- |
| `validate` | syntax, schema, semantics, standards | `VALID` | `REFUSED` with every diagnostic |
| `resolve` | normalize, resolve profiles, validate, policy | `RESOLVED` | `REFUSED` |
| `plan` | the whole pipeline through compilation | `PLANNED_DISABLED_NOT_AUTHORIZED` | `REFUSED` |
| `mobility-plan` | compare source/target realizations, bind portable policy/artifact/data/cutover intent, and compile a disabled migration topology | migration plan | `REFUSED` |
| `mobility-apply` | require an exact reviewed mobility digest, prove readiness/approval, compile delivery v2 for the target, then refuse local execution | — | `EXECUTION_REFUSED_HANDOFF_READY` or a fail-closed hold |
| `status` | where the plan stands in the lifecycle | plan status plus reached/held stages | `REFUSED` |
| `verify` | compare observations against the plan | report status | `REFUSED` |
| `evidence` | record the review evidence for a plan | `RECORDED` | `REFUSED` |
| `apply` | compiles the reviewed plan into the existing delivery handoff, then refuses | — | `EXECUTION_REFUSED_HANDOFF_READY` |

Exit `3` is an internal failure (an unreadable file, an unknown platform name).

## Options

| Option | Applies to | Meaning |
| --- | --- | --- |
| `--inventory PATH` | all | reviewed source inventory; defaults to the non-authoritative fixture |
| `--target-inventory PATH` | `mobility-plan`, `mobility-apply` | reviewed target inventory; defaults to the selected target platform fixture |
| `--mobility-intent PATH` | `mobility-plan`, `mobility-apply` | reviewed `WorkloadMobility` document carrying migration-specific artifact, dataset, rebind and cutover intent |
| `--artifact-registry PATH` | `mobility-plan`, `mobility-apply` | reviewed logical-artifact-to-native-realization registry; repository registry is the default |
| `--profiles-root PATH` | all | alternate catalog root; the repository catalogs are the default |
| `--no-compile` | `plan` | resolve the environment document without invoking the compiler |
| `--generation N` | all | the WSD generation the caller claims; defaults to `1`, and only a positive integer is accepted |
| `--approved-plan DIGEST` | `apply`, `mobility-apply` | the digest the caller claims was approved |
| `--source-commit COMMIT` | `apply`, `mobility-apply` | the clean 40-hex commit the delivery handoff binds, when the checkout is not itself clean |
| `--approvals PATH` | `apply`, `mobility-apply` | recorded external approvals bound to a plan digest |
| `--observations PATH` | `verify` | native observations document |
| `--reservation-index PATH` | `apply`, `status`, `verify`, `evidence` | exported reservation record index; defaults to the repository export, and is read to reconcile capacity |
| `--capacity-facts PATH` | `apply`, `status`, `verify`, `evidence` | recorded capacity owner facts used to compile the reservation request |
| `--ipam-index PATH` | `apply`, `status`, `verify`, `evidence` | exported IPAM allocation record index; defaults to the repository export, and is read to reconcile addressing |
| `--dns-index PATH` | `apply`, `status`, `verify`, `evidence` | exported DNS registration record index; defaults to the repository export, and is read to reconcile registration |

## `plan`

Produces a `hosting-provisioning-plan/1` document containing the normalized
request, the resolution, the policy summary, the placement decision (with every
rejected candidate), the resolved desired state, the environment document, the
compiled file list, the compile plan scopes, the Terraform and Ansible scopes, the
compiler phases, the delivery plan, the reviewed-plan manifest and the conformance
report.

`Plan.digest` — also reported as `Plan.manifest_digest` — is the canonical SHA-256 of
the complete reviewed-plan manifest, not of a summary: the claimed generation, the
request source digest and normalized identity, the resolved profile and catalog
revisions, the policy rule-set digest and result, the reviewed inventory snapshot,
the placement decision, the qualification reference and product tuple, the capacity
and address intent, the service bindings, the desired state, the rendered environment,
every compiled input, the Terraform and Ansible scope bindings, the reviewed delivery
topology and the change classification. A change to any one of those terms produces a
new digest, so an approval that cites it cites the whole decision; two requests that
differ only in whitespace, key order or an unused field still share a digest, while
two different reviewed decisions never collide. See
[Reviewed-plan manifest](plan-manifest-model.md).

The plan also carries its WSD `identity` and its derived `operation_id`
(`{wsd_key}-g{generation}-{plan_digest[:12]}`), so a plan is never confused with a
later generation of the same WSD. See
[WSD identity and generation model](generation-model.md).

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

The payload also carries the reconciled owner readings: `capacity` (with
`capacity_review`) and `addresses` (with `address_review`), read from the exported
reservation, IPAM allocation and DNS registration records. Reading an owner's export
never changes the plan, the plan digest or a stage.

## `verify`

Compares native observations against the plan. Without observations the report is
`NOT_OBSERVED`; nothing is inferred. Every observation is classified against the
plan's generation: an observation that names no generation is `UNBOUND` and one that
belongs to another generation is `STALE`, and neither can satisfy current
conformance. Verification cannot promote fixture placement and cannot satisfy an
external check.

`verify` evaluates the same reconciled owner readings, so `capacity-confirmation`,
`address-confirmation` and `dns-registration` report `PASS` only against a
confirmed authoritative answer and `PENDING_EXTERNAL_EVIDENCE` while the owner has
not answered. A reading that does not name this plan's operation identity, generation
or view digest is not this plan's evidence: the check it would have settled stays
`PENDING_EXTERNAL_EVIDENCE` and reports the mismatched keys, so a wrong-generation or
wrong-plan record never becomes a pass. `evidence` records the review evidence for the
same readings, including the `capacity`, `allocation` and `registration` records, so a
later reviewer can see which owner states an approval was taken against.

The conformance summary separates what the repository proposes from what an owner has
answered. `capacity-proposal`, `address-intent` and `service-binding` are repository-side
and report planning intent; each names the `confirmation_check` that settles it in its
evidence, and the report carries a `proposal` block stating the same authority
(`REPOSITORY_PROPOSAL_NOT_OWNER_STATE`), which owner check settles each proposal, and
which proposals are still `unconfirmed`. A repository-side row never uses the owner's
vocabulary: the report refuses to be built with `CONFORMANCE_CLAIM_UNPROVEN` if a
proposal claims an outcome only an owner can give without that owner's evidence.

## `apply`

`apply` requires both a `--approved-plan` digest and a recorded approval whose
`plan_digest` matches the plan the repository would produce. It then compiles that
plan into the established `hosting-delivery/2` handoff and **still refuses** with
`EXECUTION_REFUSED_HANDOFF_READY`, because this repository holds no target contact,
credential or change authority. The compiled graph is executed by the existing
delivery runner, which owns the journal, the stage packets, the Terraform
preparation and the uncertain-mutation recovery model; the repository adds no second
runner, no second journal and no second recovery model. See
[Delivery handoff](delivery-handoff-model.md).

`apply` also re-proves that the graph it would hand over is the topology the approved
manifest binds. Delivery v2 carries the reviewed parameter subset directly, and the
runner requires every incoming stage packet to match those values before dispatch. `handoff.build` reduces the compiled graph to the reviewed topology
intent and compares its digest with `manifest['delivery']['topology_digest']`; a
step, a dependency, an operation binding or a reviewed parameter that is not the
approved one is refused with `APPROVAL_TOPOLOGY_MISMATCH` before the graph is
returned, so an approval never covers a sequence that differs from what would run.

Before compiling, `apply` binds one exact clean source commit. When the checkout is
clean it takes the commit from the repository release verifier; when it is not, it
refuses with `ARTIFACT_INTEGRITY_FAILED` unless the caller names the commit under
review with `--source-commit`, which must still be the commit the checkout reports.
A handoff therefore never cites a commit the delivery runner would reject.

The refusal payload names the external authority, the approval format, the
outstanding owner operations and the generation, identity and operation identity it
would have handed off — one generation per handoff, and the authoritative record
decides which generation is current. The refusal and the handoff payload also carry
the complete reviewed-plan manifest, its digest, the reviewer-facing `reviewed`
projection and the compiled `delivery` graph with its `delivery_review`, so the
approval provably cites the exact plan that would be executed. See
[Reviewed-plan manifest](plan-manifest-model.md).

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

The payload also carries the capacity reading: the compiled
`capacity_owner_handoff` intent, the reconciled `capacity` state and
`capacity_review`, read from the repository's exported reservation records and, when
the caller supplies `--capacity-facts`, from the recorded owner facts. A reservation
whose authoritative outcome is a definite refusal or is still unresolved stops the
handoff. See [Capacity reservation](capacity-reservation-model.md).

The same payload carries the addressing reading: the compiled
`address_owner_handoff` chain, the reconciled `addresses` state and `address_review`,
read from the repository's exported IPAM allocation and DNS registration records
(`--ipam-index`, `--dns-index`). An unresolved or unconfirmed allocation, or an
unresolved registration, stops the handoff before it is compiled. See
[Address allocation](address-allocation-model.md).

## Reference run

```
python -m provisioner.cli validate examples/requests/internal-production.yaml
python -m provisioner.cli resolve  examples/requests/internal-production.yaml
python -m provisioner.cli plan     examples/requests/internal-production.yaml
python -m provisioner.cli status   examples/requests/internal-production.yaml
```

All five reference requests currently plan as `PLANNED_DISABLED_NOT_AUTHORIZED`
with `native_contact: false` and one compiled file each; their digests are indexed
in [`examples/golden/digests.json`](../../examples/golden/digests.json).