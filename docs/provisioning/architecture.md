# Provisioning architecture

## Purpose

`provisioner/` converts one reviewed portable request into a deterministic internal
desired state that the **existing** compiler already understands. It is an additive
front end: the compiler, the Terraform roots, the Ansible roles and the delivery
tooling keep their current owners.

## Stages and owners

| # | Stage | Owner module | Artifact | Refuses |
| --- | --- | --- | --- | --- |
| 1 | Parse and normalize | `provisioner/domain/request.py`, `provisioner/compiler/normalize.py` | `Request` | unreadable source, duplicate keys, unknown `apiVersion`/`kind` |
| 2 | Schema validation | `provisioner/schemas` | violation list | unknown field, wrong type, bad pattern |
| 3 | Profile resolution | `provisioner/profiles` | `Resolution` | unknown profile, deferred profile, unknown service, unversioned catalog |
| 4 | Policy and semantics | `provisioner/policy` | policy summary | standards rule, cross-field inconsistency |
| 5 | Placement | `provisioner/placement` | `PlacementDecision` | no eligible platform, capacity, capability, service, prefix |
| 6 | Allocation | `provisioner/allocations` | reservations | pool exhaustion, address conflict |
| 7 | Desired state | `provisioner/compiler/desired_state.py` | `DesiredState` | uncompilable intent |
| 8 | Environment document | `provisioner/compiler/environment.py` | environment document | contract violation, private output path |
| 9 | Compilation | `tools/compile_wsd.py` (existing) | compiled inputs + plan scopes | compiler refusal |
| 10 | Execution boundary | `provisioner/execution` | Terraform/Ansible/delivery scopes | undeclared catalog scope |
| 11 | Conformance | `provisioner/conformance` | conformance report | missing mandatory check |
| 12 | Observation and reconciliation | `provisioner/observation`, `provisioner/reconciliation` | drift classification | unclassifiable drift |
| 13 | CLI transport | `provisioner/cli` | JSON result document | every refusal above |

## Dependency direction

```
domain  <-  schemas, profiles, inventory
profiles <- policy, placement, compiler
placement <- compiler, execution
compiler  <- execution, conformance
service   <- cli
```

Nothing in `provisioner/` imports the CLI, and the CLI imports no other command.
Every command is a thin transport over `provisioner/execution/service.py`, which
holds the operations they share: `build_context()` loads the request, the reviewed
inventory and the catalogs, and `plan_for()` runs the pipeline over that context.
`provisioner/repository.py` is the only module that reaches back into `tools/` and
`scripts/`; it resolves those modules by name so the existing compiler stays the
single source of native field shapes.

## Reviewed policy inputs

Stages 1 and 3 read two reviewed inputs and nothing else:

- the reviewed inventory under `sources/capabilities/`, which says what the
  platforms are allowed to hold;
- the catalogs under `profiles/<family>/catalog.json`, which say what a portable
  request may ask for, which defaults a request may omit, and which revision of
  each answer was reviewed.

Each catalog declares its own `version`, each profile entry declares its own
`version`, and the loader refuses a catalog or profile without one. The loader
publishes a canonical `digest` over the whole reviewed set, so the revision of
every answer is part of the plan identity rather than a property of the checkout.
No default lives in code: `provisioner/compiler/normalize.py` applies the defaults
the catalogs declare, so changing a default is a catalog review rather than a
source edit. See [Profile model](profile-model.md#revisions).

`tests/provisioning/unit/test_architecture.py` enforces every statement in this
section, plus the rule that no `provisioner/` source carries a UTF-8 byte-order mark.
A reversed import edge fails that test rather than only contradicting this page. The
command rule reads the import graph rather than a naming convention, so both
`from provisioner.cli import plan` and `from provisioner.cli.plan import plan_for`
are reported, and a controlled fixture proves the rule rejects that edge.

There is no circular ownership: the compiler never imports `provisioner/`, the
Terraform roots never import either, and the adapters re-export the compiler's
field sets rather than restating them. The renderer asks the reviewed module which
native inputs it declares instead of restating a provider-specific list, which is
what keeps one portable request compilable on all three platforms — see
[Terraform execution boundary](terraform-boundary.md#cross-platform-realization).

## Refusal model

Every refusal is a `ProvisioningError` with a stable code, the layer that refused
it and a remediation. The layers are `syntax`, `structural`, `standards`,
`capability`, `inventory`, `capacity`, `allocation`, `compilation`, `execution`
and `authority` (`provisioner/domain/errors.py`). `Diagnostics` accumulates every
actionable refusal so one run reports all of them, not just the first.

## Lifecycle

```
request normalized validated resolved placed allocated compiled planned
   -> approved executed observed verified activated
```

This repository may reach `planned` on its own. `approved`, `executed`,
`observed`, `verified` and `activated` require evidence produced outside the
repository (`provisioner/domain/lifecycle.py`).

## What CI does

CI runs the request, placement, policy, compiler-contract, adapter, conformance,
observation and CLI regressions plus the golden corpus replay. CI **does not**
contact a platform, retrieve credentials, run Terraform or Ansible, apply a plan,
activate a service or promote fixture placement to an authorization.