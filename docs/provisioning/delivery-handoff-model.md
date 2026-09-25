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
  -> hosting-delivery/2 (provisioner/execution/handoff.py)
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
| `format` | `hosting-delivery/2` |
| `source_commit` | the clean 40-hex commit under review |
| `operation_id` | `Plan.operation_id` (`{wsd_key}-g{generation}-{plan_digest[:12]}`) |
| `generation` | `Plan.generation`, a positive integer |
| `scope` | `Plan.identity.scope` — the five delivery scope keys |
| `steps` | the reviewed sequence below |
| `operation_bindings` | owner operation → delivery step mapping |
| `reviewed_parameters` | approval-bound parameter subset per step |
| `compiled_catalog_ids` | compiled phase → reviewed catalog ID mapping |

The graph carries the approval-bound topology plus the subset of parameter values
already fixed by review. It deliberately does **not** carry private runtime paths,
credentials, executable locations/digests or predecessor receipts; those remain in the
stage packet the owner prepares. The runner compares every reviewed parameter in the
plan with the corresponding packet value before an owner is dispatched.

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

## The approved topology identity

The manifest binds the digest of the **reviewed topology intent**
(`hosting-delivery-topology-intent/1`), and this module owns that intent. It carries
the four things that decide what would be staged:

| Key | Value |
| --- | --- |
| `steps` | the ordered sequence, each step's `id`, `kind` and `needs` |
| `operationBindings` | every owner operation mapped to the step that discharges it |
| `reviewedParameters` | the parameter values the reviewed decision already fixes, per step |
| `compiledCatalogIds` | the catalog entry of every compiled phase, once the environment compiled |

It carries no commit, no generation, no scope and no operation identity: those are
execution-time bindings, not decisions a reviewer approved. Because the manifest
binds this digest, a change to a step, a dependency, a step kind, an operation
binding or a reviewed parameter changes the plan identity and the stale approval is
refused.

`build()` then re-proves the binding against what it actually emits.
`approval_projection(plan, graph)` reads the *compiled graph* — not the declaration —
and reduces it to the same intent shape, and `build()` compares
`digest(approval_projection(plan, graph))` with
`manifest['delivery']['topology_digest']`. A mismatch is refused with
`APPROVAL_TOPOLOGY_MISMATCH` before the graph is validated or returned, so the
approval an operator holds provably covers the sequence that would execute. Reading
the graph rather than re-reading `STEPS` on both sides is the point: a comparison
that restated the declaration would prove nothing about what would run.

## The capacity step's owner handoff

`capacity-reservation` is the one step whose reviewed intent is a compiled owner
document rather than a parameter value. `hosting apply` carries it in the payload as
`capacity_owner_handoff` (`hosting-capacity-owner-handoff/1`), together with the
reconciled `capacity` reading and `capacity_review`. The step's own parameter contract
is unchanged: the owner still prepares the stage packet. See
[Capacity reservation](capacity-reservation-model.md).

## The addressing steps' owner handoff

`address-allocation` and `dns-registration` are the other two steps whose reviewed
intent is a compiled owner document rather than a parameter value. `hosting apply`
carries the whole reviewed chain in the payload as `address_owner_handoff`
(`hosting-address-owner-handoff/1`) — the compiled capacity request, the compiled
reservation intent, one allocation intent and one registration intent per reviewed
zone, the staged sibling references and the per-document digests — together with the
reconciled `addresses` reading and `address_review`. Both step kinds are declared
kinds of `tools.delivery_steps.KINDS`, and the two steps still prepare their own
stage packets. See [Address allocation](address-allocation-model.md).

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
| an owner has not answered on addressing | `IPAM_ALLOCATION_UNRESOLVED` |
| a reviewed operation has no typed step | `COMPILATION_FAILED` |
| the compiled topology is not the approved topology | `APPROVAL_TOPOLOGY_MISMATCH` |
| a stage packet changes an approval-bound parameter | runner refusal before owner dispatch |
| a malformed graph | `SCHEMA_VALIDATION_FAILED` |

The first four refuse before anything is compiled. Nothing in this path can invoke
Terraform or an owner mutation, because the repository holds no credential, no
target contact and no execution authority.

## Determinism and resumption

The compiler is a pure function of the reviewed plan and the commit, so the same
reviewed plan always compiles to the same graph and a resumed delivery recognises
its own plan instead of creating a second one. The graph a resumed delivery
recognises is also the graph the manifest binds: the approved topology identity is
re-derived from the compiled graph on every call, so a resumed delivery cannot pick
up a sequence that differs from the approved one. The runner, not this repository,
owns the journal, the stage packets, the completed-step receipts and the
uncertain-mutation recovery model; a resumed execution reuses the receipts of the
steps that already completed. There is no second journal, no second Terraform runner
and no second recovery model.

## What this does not claim

This document does not assert that any delivery has started, that any stage packet
has been prepared, that any owner has acted, or that any site is qualified. The
repository compiles a reviewed topology and refuses; every plan stays
`PLANNED_DISABLED_NOT_AUTHORIZED` with `native_contact: false`, and activation
remains a separate external authority.