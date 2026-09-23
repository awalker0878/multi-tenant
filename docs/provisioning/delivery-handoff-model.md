# Delivery handoff model

The portable package plans; it never executes. What it can do is compile the
reviewed plan into the exact graph the repository's **existing** persistent delivery
runner already accepts, so an operator holding recorded authority stages the typed
stage packets and resumes one delivery instead of re-deciding the sequence by hand.

The compiler is `provisioner/execution/handoff.py`. It is a pure function of the
reviewed plan plus one clean source commit: no platform is contacted, no credential
is read, no Terraform is invoked and no owner operation is performed. It imports no
repository tooling, so the transport cannot reach into the runner's module graph.

## The completed path

```
portable WSD request (YAML)
  -> provisioner (schema, profiles, policy, placement, desired state)
  -> tools/compile_wsd.py (the existing compiler)
  -> reviewed immutable plan (Plan.manifest_digest)
  -> hosting-delivery/1 (provisioner/execution/handoff.py)
  -> tools/delivery_run.py (the existing runner)
  -> owner operations (the typed stage packets)
  -> observation and reconciliation (provisioner/observation)
  -> conformance (provisioner/conformance)
  -> separate activation authority
```

`hosting apply` stops at the fourth line and refuses. The runner on the fifth line
is unchanged, is not reimplemented, and remains the only engine that executes a
change.

## The graph

`build(plan, source_commit)` emits the declared contract, exactly the keys
`tools/delivery_run.validate` requires:

| Key | Value |
| --- | --- |
| `format` | `hosting-delivery/1` |
| `source_commit` | the clean 40-hex commit under review |
| `operation_id` | `Plan.operation_id` (`{wsd_key}-g{generation}-{plan_digest[:12]}`) |
| `generation` | `Plan.generation`, a positive integer |
| `scope` | `Plan.identity.scope` — the five delivery scope keys |
| `steps` | the reviewed sequence below |

The graph carries **topology only**. It contains no parameter value, no private
path, no host fact and no predecessor receipt, because every one of those belongs to
the stage packet the owner of that step prepares and signs. A handoff that carried
them would be a second, unverified source of private state.

The reviewed sequence is the ordinary WSD delivery, topologically ordered:

| Step | Kind | Discharges |
| --- | --- | --- |
| `admission` | `acceptance` | the admission gate |
| `capacity-reservation` | `capacity` | `capacity-reservation` |
| `address-allocation` | `ipam` | `address-allocation` |
| `dns-registration` | `dns` | `dns-registration` |
| `dns-propagation` | `dns_propagation` | name propagation |
| `domain-plan` | `terraform_plan` | `state-backend` |
| `domain-apply` | `terraform_apply` | the domain scope |
| `domain-acceptance` | `acceptance` | native domain acceptance |
| `edge-policy` | `edge_policy` | `security-edge-route` |
| `workload-inputs` | `workload_inputs` | domain outputs into workloads |
| `workload-plan` | `terraform_plan` | the workload scope |
| `workload-apply` | `terraform_apply` | the workload scope |
| `bootstrap` | `platform_transition` | the narrow bootstrap |
| `bootstrap-acceptance` | `acceptance` | native bootstrap acceptance |
| `guest-plan` | `guest_plan` | `guest-configuration` |
| `guest-apply` | `guest_apply` | guest configuration |
| `backup-retention` | `restic` | `backup-retention` |
| `service-acceptance` | `acceptance` | `shared-service-handoff` |
| `pre-activation-campaign` | `target_campaign` | `native-qualification` |
| `activation` | `acceptance` | `production-authorization` |
| `post-activation-campaign` | `target_campaign` | post-activation qualification |

Three properties are load-bearing rather than cosmetic, and each is a recorded
assumption in the completion audit:

1. **The workload phase descends from the capacity reservation.** The existing
   `tools.capacity_demand.check_ancestors` walks transitive dependencies and demands
   a live reservation for every `capacity` ancestor of a workloads `terraform_apply`.
   Because `workload-apply` descends from `capacity-reservation`, the check still
   fires; a graph that placed the reservation elsewhere would silently skip it.
2. **The bootstrap and the workload build descend from the edge attachment.** No
   workload is created outside the isolated route, so containment precedes
   construction.
3. **Activation is separated by the two campaigns and one acceptance gate.**
   `edge_policy` has no phase distinction in the declared kind, so the activation and
   post-activation separation is carried by `pre-activation-campaign`,
   `activation` and `post-activation-campaign`. A post-activation campaign needs the
   separate edge owner's authorized withdrawal, exactly as
   [`docs/implementation/automation/delivery-runner.md`](../implementation/automation/delivery-runner.md)
   describes.

## Operation coverage

`Plan.delivery` names ten owner operations. `OPERATION_STEPS` maps every one of them
to the step that discharges it, and `uncovered(operations)` reports any operation
the table does not map. `build()` refuses with `COMPILATION_FAILED` when the mapping
is incomplete, so a new owner operation cannot appear in a handoff without a typed
step that owns it. Every step kind is a declared kind of
`tools.delivery_steps.KINDS`: the repository adds no new owner type and no parallel
generic runner.

## Source commit binding

A handoff binds exactly one clean 40-hex commit, and `tools.delivery_run.run`
re-verifies it against the checkout it is running from. `hosting apply` therefore
refuses before compiling rather than emitting a graph the runner must reject:

- with a clean checkout it takes the commit from the repository release verifier
  (`tools/check_release.verify`, reached only through `provisioner/repository.py`);
- with a dirty checkout it refuses with `ARTIFACT_INTEGRITY_FAILED`, naming the
  differing files, unless the caller names the commit under review with
  `--source-commit`, which must still be the commit the checkout reports;
- an exported release with no checkout accepts the explicit `--source-commit`.

## Refusals

| Condition | Code |
| --- | --- |
| no `--approved-plan` digest | `AUTHORITY_REQUIRED` |
| the claimed digest is not this plan | `ARTIFACT_INTEGRITY_FAILED` |
| no recorded approval for that digest | `AUTHORITY_REQUIRED` |
| the checkout is not the commit under review | `ARTIFACT_INTEGRITY_FAILED` |
| a reviewed operation has no typed step | `COMPILATION_FAILED` |
| a malformed graph | `SCHEMA_VALIDATION_FAILED` |

The first four refuse before anything is compiled. Nothing in this path can invoke
Terraform or an owner mutation, because the repository holds no credential, no
target contact and no execution authority.

## Determinism and resumption

The compiler is a pure function of the reviewed plan and the commit, so the same
reviewed plan always compiles to the same graph and a resumed delivery recognises
its own plan instead of creating a second one. The runner, not this repository, owns
the journal, the stage packets, the completed-step receipts and the
uncertain-mutation recovery model; a resumed execution reuses the receipts of the
steps that already completed. There is no second journal, no second Terraform runner
and no second recovery model.

## What this does not claim

This document does not assert that any delivery has started, that any stage packet
has been prepared, that any owner has acted, or that any site is qualified. The
repository compiles a reviewed topology and refuses; every plan stays
`PLANNED_DISABLED_NOT_AUTHORIZED` with `native_contact: false`, and activation
remains a separate external authority.