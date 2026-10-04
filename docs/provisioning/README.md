# Portable provisioning

The portable provisioning package (`provisioner/`) turns one reviewed YAML request
into a deterministic, reviewable internal desired state. It is a **portable,
provider-neutral front end with a package-owned native compiler**. The original
compiler implementation is preserved at `provisioner/compiler/wsd.py`; Terraform
roots, Ansible roles and the remaining delivery tooling keep their owners.

Pipeline (each stage is a separate owner, in dependency order):

```
portable WSD request (YAML)
  -> schema validation          provisioner/schemas
  -> profile resolution         provisioner/profiles
  -> policy and semantics       provisioner/policy
  -> placement                  provisioner/placement
  -> desired state              provisioner/compiler/desired_state.py
  -> realization contract       provisioner/adapters
  -> package-owned compiler     provisioner/compiler/wsd.py
  -> terraform / ansible        provisioner/execution, provisioner/adapters
  -> hosting-delivery/2         provisioner/execution/handoff.py
  -> existing delivery runner   provisioner/execution/delivery_run.py (the only engine)
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
| [Current enterprise execution plan](../product/enterprise-workload-mobility-execution-plan.md) | B01–B50 delivery sequence, remaining implementation and separate qualification gates |
| [Provisioning architecture](architecture.md) | Stages, ownership, dependency direction, what CI does not do |
| [Portable WSD request contract](request-contract.md) | `apiVersion`, `kind`, `metadata`, `spec` field by field |
| [Profile model](profile-model.md) | Catalogs, implemented vs deferred status, resolution rules |
| [Placement model](placement-model.md) | Fail-closed site/cell selection from read-only inventory |
| [Internal desired-state model](desired-state-model.md) | The internal artifact handed to the compiler |
| [WSD identity and generation model](generation-model.md) | What is being changed, which change it is, and the claim rules |
| [Reviewed-plan manifest](plan-manifest-model.md) | The complete reviewed decision an approval cites, term by term |
| [Delivery handoff model](delivery-handoff-model.md) | The compiled `hosting-delivery/2` graph and the existing runner that owns it |
| [Capacity reservation model](capacity-reservation-model.md) | The reservation intent handed to the authoritative capacity owner, and the states it can answer |
| [Address allocation model](address-allocation-model.md) | The allocation and DNS registration intents handed to the authoritative owners, and the states they can answer |
| [Platform adapter contract](adapter-contract.md) | The six realization surfaces, the gap vocabulary and the platform-name-free compiler |
| [Terraform execution boundary](terraform-boundary.md) | Root selection, variable files, evidence |
| [Service-owner boundary](service-owner-boundary.md) | Service bindings and the owners that retain authority |
| [Plan workflow](plan-workflow.md) | `validate resolve plan mobility-plan mobility-apply status verify evidence apply` |
| [Supported service-profile matrix](service-profile-matrix.md) | What is implemented, what is deferred, why |
| [Installed runtime identity](installed-runtime-identity.md) | Exact protected interpreter, source, wheel and installed receipt before each writer use |
| [Current command authority](../operations/current-command-authority.md) | Scoped planning, each guarded Linux SSH command and certificate-only Windows command custody |
| [Fleet discovery and on-call owners](../engineering/discovery-fleet-and-oncall-owners.md) | Global database read budgets, installed collector custody and independently assigned human alert ownership |
| [Enterprise wave pools](enterprise-wave-pools.md) | One aggregate physical budget and tenant turn over existing B09 wave members and retained uncertain charges |
| [Enrolled resource and service recovery](../engineering/enrolled-resource-service-recovery.md) | Current approved service intents, independently observed outcomes and separate old-credential exclusion |
| [Authenticated retained-state handover](../operations/retained-state-authenticated-handover.md) | Original retained import, independent proof verification, native reconciliation and owner-epoch interlock |
| [Controlled HA and restore drills](../operations/control-application/3-controlled-ha-and-restore-drills.md) | Actual commissioned failover and observation-only restoration under current command authority |
| [Final-code evidence intake](../operations/control-application/4-original-final-code-evidence-intake.md) | Independent raw campaign and pilot originals required by final release preparation |
| [Final-code commissioning dossier](../operations/control-application/5-final-code-commissioning-dossier.md) | Exact direction, method, profile and tuple acquisition instructions from the sealed installed command |

## Retained refactor history

The [refactor completion audit](../deepseek-refactor-completion-audit.md) and
[DeepSeek completion execution prompt](../deepseek-refactor-completion-execution-prompt.md)
are retained specifications for an earlier refactor scope, not current execution
authorities or evidence that the complete mobility programme is implemented.
The B01–B50 execution plan above owns the current sequence and outstanding gates.

## Command line

```
python -m provisioner.cli validate <request.yaml>
python -m provisioner.cli resolve  <request.yaml>
python -m provisioner.cli plan     <request.yaml>
python -m provisioner.cli mobility-plan <request.yaml> --mobility-intent <mobility.yaml>
python -m provisioner.cli mobility-apply <request.yaml> --mobility-intent <mobility.yaml> --approved-plan <digest>
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
