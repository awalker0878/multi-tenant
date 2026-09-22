# Platform adapter contract

An adapter declares *only* the native field shapes and module identities a platform
realization needs. It never provisions, never contacts a platform and never decides
placement.

Modules: `provisioner/adapters/base.py`, `provisioner/adapters/{nutanix,vmware,openstack}/`
Format: `hosting-platform-adapter/1`

## Contract

```python
adapter = adapters.get('openstack')

adapter.platform          # 'openstack'
adapter.family            # platform family
adapter.domains_module    # reviewed domains module identity
adapter.workloads_module  # reviewed workloads module identity
adapter.placement_fields  # native identity the inventory must supply for placement
adapter.network_fields    # native identity produced by native readback
adapter.security_edge     # the reviewed edge realization for this platform
adapter.product_tuple     # reviewed product tuple, or 'UNSELECTED'
adapter.qualified         # True only when a product tuple is qualified
adapter.to_dict()         # JSON form, always with native_contact: False
```

`placement_shape()` and `network_shape()` state which side supplies each field:
placement fields come from inventory cluster native identity, network fields come
from native readback after the domains phase.

## No drift

The native field sets are **re-exported from the existing compiler**
(`tools/compile_wsd.PLACEMENT` / `tools/compile_wsd.NETWORK`) and the module
identities come from `scripts/build_wsd_compositions.COMPONENTS`. The adapter and
the compiler therefore cannot disagree: there is one declaration, in the compiler.

The same rule governs realization: the environment renderer overlays only the
inputs the reviewed module declares, and a platform that cannot carry a computed
fact records `REALIZATION_INPUT_UNAVAILABLE` instead of dropping it. See
[Terraform execution boundary](terraform-boundary.md#native-input-ownership).

## Qualification

`qualified` is derived from `eligibility.product_tuple(platform)`. No tuple is
currently qualified in the registry, so every adapter reports
`status: NATIVE_QUALIFICATION_ABSENT`. An adapter that is not qualified can still
describe its shapes and produce a plan, but it cannot be selected as an eligible
placement target and it cannot authorize execution.

## Refusals

| Situation | Result |
| --- | --- |
| unknown platform name | `ValueError` from `get()`; the CLI reports it as an internal failure |
| platform absent from the reviewed composition table | `KeyError` from the compiler table, surfaced as an internal failure |
| adapter used to claim a change | impossible: no adapter has a mutating entry point |

Adding an adapter means adding a compiler table entry, a composition entry, a
catalog entry, and a regression in `tests/provisioning/test_adapters.py`.