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
| 3 | Profile resolution | `provisioner/profiles` | `Resolution` | unknown profile, deferred profile |
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
```

Nothing in `provisioner/` imports the CLI, and the CLI imports no other command.
`provisioner/repository.py` is the only module that reaches back into `tools/` and
`scripts/`; it resolves those modules by name so the existing compiler stays the
single source of native field shapes.

There is no circular ownership: the compiler never imports `provisioner/`, the
Terraform roots never import either, and the adapters re-export the compiler's
field sets rather than restating them.

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