# Portable provisioning

The portable provisioning package (`provisioner/`) turns one reviewed YAML request
into a deterministic, reviewable internal desired state. It is a **portable,
provider-neutral front end to the existing compiler** — it does not replace the
compiler, the Terraform roots, the Ansible roles or the delivery tooling.

Pipeline (each stage is a separate owner, in dependency order):

```
portable WSD request (YAML)
  -> schema validation          provisioner/schemas
  -> profile resolution         provisioner/profiles
  -> policy and semantics       provisioner/policy
  -> placement                  provisioner/placement
  -> desired state              provisioner/compiler/desired_state.py
  -> existing compile_wsd.py    tools/compile_wsd.py
  -> terraform / ansible        provisioner/execution, provisioner/adapters
  -> delivery and observation   provisioner/execution/delivery.py, provisioner/observation
```

WSD identity and generation are derived at the desired-state boundary and then bound
into the plan, the delivery plan, every owner operation, the observations, the
conformance report and the recorded evidence, so a plan and the operation it would
start cannot be confused with a later generation of the same WSD. The plan identity
itself is the digest of the complete reviewed-plan manifest, so an external approval
that cites it cites every reviewed decision. See
[WSD identity and generation model](generation-model.md) and
[Reviewed-plan manifest](plan-manifest-model.md).

## Active documents

| Document | Covers |
| --- | --- |
| [Provisioning architecture](architecture.md) | Stages, ownership, dependency direction, what CI does not do |
| [Portable WSD request contract](request-contract.md) | `apiVersion`, `kind`, `metadata`, `spec` field by field |
| [Profile model](profile-model.md) | Catalogs, implemented vs deferred status, resolution rules |
| [Placement model](placement-model.md) | Fail-closed site/cell selection from read-only inventory |
| [Internal desired-state model](desired-state-model.md) | The internal artifact handed to the compiler |
| [WSD identity and generation model](generation-model.md) | What is being changed, which change it is, and the claim rules |
| [Reviewed-plan manifest](plan-manifest-model.md) | The complete reviewed decision an approval cites, term by term |
| [Platform adapter contract](adapter-contract.md) | The read/plan/apply boundary and its refusals |
| [Terraform execution boundary](terraform-boundary.md) | Root selection, variable files, evidence |
| [Service-owner boundary](service-owner-boundary.md) | Service bindings and the owners that retain authority |
| [Plan workflow](plan-workflow.md) | `validate resolve plan status verify evidence apply` |
| [Supported service-profile matrix](service-profile-matrix.md) | What is implemented, what is deferred, why |
| [Refactor completion audit](../deepseek-refactor-completion-audit.md) | Ordered completion gates, required regressions, repository-side vs external exit criteria |
| [DeepSeek completion execution prompt](../deepseek-refactor-completion-execution-prompt.md) | Authoritative execution sequence for closing every repository-side audit gate with small commits |

## Command line

```
python -m provisioner.cli validate <request.yaml>
python -m provisioner.cli resolve  <request.yaml>
python -m provisioner.cli plan     <request.yaml>
python -m provisioner.cli status   <request.yaml>
python -m provisioner.cli verify   <request.yaml>
python -m provisioner.cli evidence <request.yaml>
python -m provisioner.cli apply    <request.yaml>
```

Exit codes: `0` success, `2` refused (a policy, semantic or authority decision),
`3` internal failure. `apply` always refuses: this repository holds no target
contact, credential or change authority.

## Reference corpus

[`examples/requests/`](../../examples/requests) holds the reviewed reference
requests; [`examples/resolved/`](../../examples/resolved) and
[`examples/golden/`](../../examples/golden) hold their stored deterministic
artifacts. See [`examples/README.md`](../../examples/README.md).

`provisioner/inventory/fixtures/` holds one reviewed fixture inventory per platform
(`openstack-reference`, `vmware-reference`, `nutanix-reference`). Every fixture is
`FIXTURE_NOT_AUTHORITATIVE`, and none of them is a placement authority. They exist
so the cross-platform contract can be exercised offline; replacing them with
authoritative site state is tracked as open work in
[`docs/NEXT_WORK.md`](../NEXT_WORK.md).

## Test layout

Regressions live under `tests/provisioning/`, split into the categories the refactor
names: `unit`, `schema`, `policy`, `placement`, `compiler`, `adapters`,
`reconciliation`, `conformance`, `documentation` and `end_to_end`. The shared
helpers stay in `tests/provisioning/support.py`.

The categories are nested inside `provisioning/` rather than placed at the top of
`tests/` because a test package must never shadow a top-level source package:
`policy/`, `profiles/` and `inventory/` already exist at the repository root, so
`tests/policy/` would resolve as the source package during discovery.

## What this does not claim

No document here asserts that a site, cell, provider or service has been
contacted, qualified or activated. Placement is fail-closed, every plan is
`PLANNED_DISABLED_NOT_AUTHORIZED`, and `native_contact` is always `false`.
