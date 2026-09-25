# Reviewed-plan manifest

An approval is only worth recording if it can be proven to cite the exact decision a
reviewer saw. A digest over a partial projection cannot: two plans whose rendered
environment is byte-identical can still differ in a reservation target, a service
endpoint, a pinned placement cell, a reviewed profile revision or a later generation,
and an approval that cites only the projection would silently cover both.

`Plan.manifest` is the complete, canonical reviewed-plan manifest and
`Plan.digest` — also surfaced as `Plan.manifest_digest` — is the canonical digest of
that manifest. Format: `hosting-reviewed-plan-manifest/1`.
Module: `provisioner/execution/manifest.py`.

## Terms

The manifest is an enumeration of reviewed decision terms, in the order a reviewer
reads them. Each term is either a reviewed decision or a canonical digest of one.

| Term | Binds |
| --- | --- |
| `format` | `hosting-reviewed-plan-manifest/1` |
| `generation` | the claimed WSD generation this decision belongs to |
| `request` | the request source path, repository-relative, and the digest of the file that was read |
| `request_identity` | the normalized `apiVersion`/`kind`/`metadata`/`spec` identity |
| `resolution` | resolved profiles, profile versions, catalog versions, catalog digest |
| `policy` | the evaluated policy summary, including the exact `rules_digest` |
| `inventory` | the reviewed inventory document's own identity: its digest, the source it declares, its status and its authority. The read location is diagnostic provenance and is deliberately excluded, so the same document yields one identity on every operating system and in every checkout |
| `placement` | the placement decision digest, including every rejected candidate |
| `qualification` | the qualification reference the selection was gated on |
| `product_tuple` | the selected product/API/provider/hardware tuple |
| `realization` | the selected platform's realization contract: family, field shapes, readback identity, binding requirement, security edge, gaps and qualification status |
| `capacity` | every reservation, its demand and its committed-after position |
| `capacity_view` | the commissioned capacity snapshot the reservation intent is bound to |
| `addresses` | every reserved prefix, gateway host number and workload address |
| `allocation_view` | the addressing snapshot the allocation and registration intents are bound to |
| `service_bindings` | every service binding, its endpoints and its binding class |
| `desired_state` | the internal desired-state digest |
| `environment` | the rendered environment document digest |
| `compiled_inputs` | the digest of every input the existing compiler accepted |
| `terraform` | the reviewed scope, root, input, state key, catalog and owner bindings |
| `ansible` | the reviewed Ansible scope bindings |
| `delivery` | the identity of the reviewed delivery *topology intent*: the sequence, the kinds, the dependencies, the operation-to-step bindings and the parameters the reviewed decision fixes. The owner-operation summary is not bound, because the summary states *which owners* act while the topology states *what will be staged*, and only the latter is executed |
| `classification` | the approval-relevant disruptive/destructive/rebuild declaration |

## What the manifest deliberately excludes

- **Derived identity.** The delivery `plan_digest`, the `operation_id`, the plan
  `identity` and the generation echoed onto the delivery graph are all computed
  *from* the plan, so binding them would make the identity depend on itself. The
  manifest binds the reviewed topology *intent* by digest instead, and the intent is
  computed from the reviewed decision alone: it carries no commit, no generation, no
  scope and no operation identity.
- **A parallel delivery identity.** The owner-operation summary
  (`provisioner.execution.delivery`) is not bound as a second delivery term. It names
  the owners who must act; the topology intent names the sequence that would be
  staged, and the compiled `hosting-delivery/2` graph must project back onto exactly
  the bound topology or `handoff.build` refuses it. Binding both would give one
  decision two identities and let a change to the executed sequence pass unnoticed.
- **Owner-provisioned free text.** A Terraform scope's `backend` is the text an owner
  provisions against the reviewed state key, not a reviewed decision. The manifest
  binds `scope`, `root`, `input`, `state_key`, `catalog_id`, `owner_scope` and
  `status`, and excludes `backend`.
- **External capacity facts.** The manifest binds the commissioned capacity snapshot
  as `capacity_view`, because that snapshot is reviewed inventory state. It excludes
  the reservation identity and the handoff compiled from it: the identity is derived
  from the plan digest and generation, and the envelope and the owner's answer are
  external facts the repository cannot review. See
  [Capacity reservation](capacity-reservation-model.md).
- **External addressing facts.** The manifest binds the addressing snapshot as
  `allocation_view`, for the same reason: it is reviewed inventory state that the
  allocation and registration intents are compiled against. It excludes the
  allocation identity, the allocation and registration intents and the owners'
  answers, because the authoritative prefix is the IPAM owner's value and the
  repository reviews the addressing *identity*, not a value an owner has yet to
  return. See [Address allocation](address-allocation-model.md).
- **Volatile and checkout state.** No timestamp, run identifier, host name or git
  checkout property is bound. The request source path is bound **repository-relative
  in POSIX form**, so the identity does not depend on whether an operator spelled the
  path relatively or absolutely, or on where the checkout lives. The manifest is
  reproducible from the reviewed inputs alone, which is what makes byte-identical
  replay possible. The immutable source identity is bound in the `hosting-delivery/2`
  handoff instead, where the delivery tooling already requires a 40-hex
  `source_commit`. The reviewed inventory document follows the same rule: the
  manifest binds the document's own `source`, `digest`, `status` and `authoritative`
  flag, and the location the file was read from is retained only as diagnostic
  provenance, normalized to POSIX separators, so that a Windows and a Linux checkout
  of the same document produce the same plan digest.

## Why an approval is provable

`hosting apply --approved-plan <digest>` requires the claimed digest to equal
`Plan.manifest_digest` and requires a recorded approval whose `plan_digest` matches
it. Because the manifest binds every term above, an approval that cites the manifest
digest cites the complete decision; a change to any one term — a reservation target,
a `committed_after` value, the commissioned capacity snapshot, the addressing
snapshot, a service endpoint, a binding class, a placement decision,
a qualification reference, a product tuple, a realization contract, a profile version,
a policy rule revision, the inventory snapshot, a compiled input, an environment value,
a Terraform state key or root, an Ansible scope, the reviewed delivery topology, the
generation or the change classification — produces a different digest and the stale
approval is refused.

A topology change is bound *and* re-proved at execution time. `handoff.build` derives
the same intent from the compiled `hosting-delivery/2` graph and compares its digest
with `manifest['delivery']['topology_digest']`; a step, a dependency, an operation
binding or a reviewed parameter that is not the approved one is refused with
`APPROVAL_TOPOLOGY_MISMATCH` before the graph leaves the repository. See
[Delivery handoff](delivery-handoff-model.md).

`apply` then **still refuses** with `EXECUTION_REFUSED_HANDOFF_READY`, and its
payload carries the manifest, the reviewer-facing `reviewed` projection, the manifest
digest and the compiled `hosting-delivery/2` graph it would have handed to an external
execution owner. The projection carries the same digest as the manifest, so an approval
may cite either. See [Delivery handoff](delivery-handoff-model.md).

## Determinism

Two requests that differ only in whitespace, key order or an unused field resolve to
the same manifest and the same digest: the request identity is a canonical digest of
the normalized document, and every other term is a canonical digest of reviewed
state. Two different reviewed decisions never collide. The reference digests are
indexed in [`examples/golden/digests.json`](../../examples/golden/digests.json).

## What this does not claim

The manifest is a reviewed *intent*, not an authorization or an observation. It binds
no native state, no target contact, no credential and no approval; every plan stays
`PLANNED_DISABLED_NOT_AUTHORIZED` with `native_contact: false`. The repository has no
replacement or destroy change-intent model yet, so `classification.destructive` and
`classification.rebuild` are declared `false` unconditionally and a future
change-intent model must set them from reviewed input. A qualification reference in
the manifest records the qualification the decision was gated on; it does not assert
that the platform is qualified.