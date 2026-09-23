# Platform adapter contract

An adapter owns *how a portable decision is realized on one platform*. It declares
the native field shapes, the reviewed module identities, the cross-phase binding the
platform requires, the edge realization and the inputs the platform cannot carry. It
never provisions, never contacts a platform and never decides placement.

Modules: `provisioner/adapters/base.py`, `provisioner/adapters/{nutanix,vmware,openstack}/`
Format: `hosting-platform-adapter/2`
Contract format: `hosting-adapter-realization-contract/1`
Gap format: `hosting-adapter-realization-gap/1`

## The six surfaces

`Adapter.realization_contract()` returns the whole declaration. It is the six
surfaces below plus `format`, `platform`, `family`, `gap_codes`, `limits` and
`native_contact: false`. Every surface document carries its own `format`, its own
`surface` name, the `authority` it was read from and `native_contact: false`.

| Surface | Method | Binds |
| --- | --- | --- |
| capability | `capability_contract(required=(), assurance_profile=None)` | the product tuple, whether it is qualified, and every reason it is not |
| placement | `placement_contract()` | the native identity reviewed inventory must supply for placement |
| phases | `phase_contract(phase)` | one reviewed module, its declared inputs, the computed inputs it accepts, the ones it cannot, and its binding requirement |
| readback | `readback_contract()` | the native identity the domains phase must read back, and whether the module or the binding produces it |
| security edge | `security_edge_contract()` | the reviewed edge component, its components and its owner scope |
| gaps | `realization_gaps()` | each computed fact the platform cannot carry, as a gap document |

`capability_contract()` with no arguments reports the bare registry state. Passing
`required={'distributed_firewall'}` adds
`capability:distributed_firewall:NOT_NATIVE_QUALIFIED` to `blockers`; passing
`assurance_profile='protected-b-medium'` adds `assurance_profile:protected-b-medium`.
A blocker is a reason, not a refusal: the plan still compiles and the refusal happens
where the requirement is enforced.

## The metadata surface

```python
adapter = adapters.get('openstack')

adapter.platform          # 'openstack'
adapter.family            # platform family
adapter.domains_module    # reviewed domains module identity
adapter.workloads_module  # reviewed workloads module identity
adapter.placement_fields  # native identity the inventory must supply for placement
adapter.network_fields    # native identity produced by native readback
adapter.security_edge     # the reviewed edge realization for this platform
adapter.edge_components   # every reviewed component that realizes the edge
adapter.binding_requirement  # the observed field -> binding field pairs the phase needs
adapter.realization_note  # how the platform realizes a fact its module cannot accept
adapter.product_tuple     # reviewed product tuple, or 'UNSELECTED' (property)
adapter.qualified         # True only when a product tuple is qualified (property)
adapter.limits            # the declared limits of this declaration
adapter.to_dict()         # JSON form, always with native_contact: False
```

`module(phase)`, `declared_inputs(phase)` and `computed_facts(phase)` answer
per-phase questions. `module_contract(component)` returns the reviewed Terraform
module's own `variables` and `outputs` sets, read from the reviewed configuration,
which is what the readback surface is checked against.

`placement_shape()` and `network_shape()` state which side supplies each field:
placement fields come from inventory cluster native identity, network fields come
from native readback after the domains phase.

## No drift

The native field sets are **read from the existing compiler**
(`tools/compile_wsd.PLACEMENT` / `tools/compile_wsd.NETWORK`) and the module
identities come from `scripts/build_wsd_compositions.COMPONENTS`. The adapter and the
compiler therefore cannot disagree: there is one declaration, in the compiler, and the
adapter is a typed projection of it. `provisioner/compiler/environment.py` reaches the
compiler through `provisioner/repository.py`, which is the only module allowed to
import `tools/` and `scripts/`.

The same rule governs realization. The environment renderer overlays only the inputs
the reviewed module declares — `PROVISIONER_OWNED_INPUTS` is derived from
`adapters.COMPUTED_FACTS`, so even the list of facts the provisioner computes is owned
by the adapter. A computed fact the selected module cannot accept is declared as a gap
by the adapter and recorded as one `REALIZATION_INPUT_UNAVAILABLE` warning naming the
input, the platform and how the platform realizes it instead. The warning comes from
the adapter's gap document; the compiler never decides it. See
[Terraform execution boundary](terraform-boundary.md#cross-platform-realization).

## What the adapter owns that generic code used to

The compiler used to carry a provider-specific branch:

```python
if platform == 'vmware':        # removed
    ...build the NSX segment mapping...
```

That decision now lives in two declarative places and nowhere else:

* `tools/compile_wsd.WORKLOAD_NETWORK_BINDING` — a table keyed by platform holding
  `observed_field`, `native_field`, `binding_field`, `binding_identity` and the
  message a reviewer reads. The compiler looks the selected platform up; it never
  compares a platform name.
* `Adapter.binding_requirement` — the same declaration, surfaced as data on the
  adapter and bound into the plan manifest.

`compile_environment(document, phase, outputs, phase_bindings)` is named for the phase
it binds rather than for the platform, so the argument cannot silently become
provider-specific again. `tests/provisioning/adapters/test_adapter_contract.py` walks
the AST of `tools/compile_wsd.py` and of every `provisioner/**.py` source and fails on
any comparison against a platform-name literal.

## Qualification

`qualified` is derived from `eligibility.product_tuple(platform)`. No tuple is
currently qualified in the registry, so every adapter reports
`status: NATIVE_QUALIFICATION_ABSENT` and `blockers: ['product_tuple:UNSELECTED']`.
An adapter that is not qualified can still describe its shapes and produce a plan, but
it cannot be selected as an eligible placement target and it cannot authorize
execution.

## The realization manifest term

`Plan.manifest['realization']` binds the selected platform's declaration: the
platform, the family, the edge component and its components, the owner scope, the
sorted gap codes and the inputs they cover, the sorted placement fields, the sorted
readback identity, the binding requirement, the qualification status and
`native_contact: false`. `manifest.review()` surfaces the edge component as
`realization` and the gap codes as `realization_gaps`.

Because the term participates in the manifest, an approval citing a plan digest cites
the realization contract it was reviewed against: changing a declared input set, a
binding requirement or a gap produces a different digest. See
[Reviewed-plan manifest](plan-manifest-model.md#terms).

## Refusals

| Situation | Result |
| --- | --- |
| unknown platform name | `ValueError` from `get()`; the CLI reports it as an internal failure |
| plan realizes another platform | `REALIZATION_CONTRACT_UNSATISFIED` in the `compilation` layer, `path: $.spec.platform` |
| plan represents no required zone | `REALIZATION_CONTRACT_UNSATISFIED`, naming the absent zone |
| a zone supplies no native placement identity | `REALIZATION_CONTRACT_UNSATISFIED`, naming the missing fields |
| a workload declares native inputs the module does not accept | `REALIZATION_CONTRACT_UNSATISFIED`, naming the inputs |
| adapter used to claim a change | impossible: no adapter has a mutating entry point |

`Adapter.validate(plan)` returns the problem list; `create_plan` raises
`REALIZATION_CONTRACT_UNSATISFIED` with `details = {'platform', 'problems'}` when the
list is non-empty. The check runs after compilation, so a plan whose environment
document the compiler already refused reports the compiler's refusal first.

The three repository conformance checks `adapter-contract`, `adapter-readback` and
`security-edge` run this contract against every plan. They are repository-side static
checks: they read reviewed configuration, they report `native_contact: false` and they
never satisfy an external requirement.

## Adding an adapter

Adding an adapter means adding a compiler table entry (`PLACEMENT`, `NETWORK` and,
where the platform binds phases, `WORKLOAD_NETWORK_BINDING`), a composition entry, a
catalog entry, an `_adapter()` call in the platform package, and a regression in
`tests/provisioning/adapters/`. The platform name appears in exactly those declarative
tables; no generic module learns it.