# Terraform execution boundary

The provisioner **never runs Terraform**. It resolves which reviewed stack a
decision belongs to, refuses any scope the reviewed catalog does not declare, and
hands the compiled inputs to the existing execution tooling. State and backends
belong to the stack owner.

Module: `provisioner/execution/terraform.py`
Catalog: [`terraform/catalog.json`](../../terraform/catalog.json)
Format: `hosting-terraform-catalog/1`

## Catalog

Each entry declares `id`, `platform`, `kind` (`component` or `composition`),
`module`, `root` and `owner_scope` (`wsd` or `security-edge`). The loader refuses a
malformed catalog, an incomplete entry, a duplicate id and an unknown owner scope.

The two phases are `domains` and `workloads`. `composition(platform, phase)`
expects the reviewed root `terraform/stacks/wsd/<platform>/<phase>` and refuses
anything else with `ENVIRONMENT_CONTRACT_INVALID`.

## Scope assertion

The compiler already returns plan scopes. `assert_scopes(scopes, platform)` checks
each compiled scope against the reviewed composition for its phase:

* a scope whose `root` is not the reviewed composition root is refused
* every accepted scope is annotated with `catalog_id`, `owner_scope`,
  `status: DRAFT_DISABLED_NOT_AUTHORIZED` and
  `backend: owner-provisioned; matched to state_key by its owner`

## Phase status

| Phase | Status | Requires |
| --- | --- | --- |
| `domains` | `COMPILED_DISABLED_NOT_AUTHORIZED` | reviewed inventory only |
| `workloads` | `HELD_PENDING_NATIVE_DOMAIN_OUTPUTS` | observed native domain members from the domains phase |

The workloads phase cannot be compiled from the request alone: the native domain
members do not exist yet, and this repository will not fabricate them.

## Native input ownership

The provisioner never restates a provider-specific field name. It asks the reviewed
module what it declares and overlays only the inputs it owns:

```python
native_variables(platform, phase)  # tools/compile_wsd.py: the module's own variables
PROVISIONER_OWNED_INPUTS           # boot_disk_gib, data_disk_gib, ipv4_address
```

`provisioner/compiler/environment.py` renders the environment document from the
portable desired state, then overlays an owned input only when the selected
module declares it. A restated OpenStack field list would have made the Nutanix
and VMware paths uncompilable; the compiler is the only owner of native shapes, so
there is nothing to drift.

## Cross-platform realization

The same portable request, differing only in `spec.platform.preference`, must
compile on Nutanix, VMware/NSX and OpenStack given compatible reviewed inventory.
The request carries no native field. Only the realization differs:

| Platform | Domains module | Workloads module | Realized address |
| --- | --- | --- | --- |
| `nutanix` | `nutanix-domain` | `nutanix-workload` | `ipv4_address` on the workload |
| `vmware` | `nsx-domain` | `vsphere-workload` | carried by the NSX domain segment |
| `openstack` | `openstack-domain` | `openstack-workload` | `ipv4_address` on the workload |

The vSphere workload module declares no address variable: the address is realized
by the NSX domain composition that owns the segment. The provisioner records that
boundary rather than dropping the fact silently. The plan carries one
`REALIZATION_INPUT_UNAVAILABLE` warning naming the input and the platform, in the
`compilation` layer, and the allocation itself still happens — every platform
allocates the same distinct addresses. `tests/provisioning/compiler/test_cross_platform.py`
holds the contract, reading the expected field shapes from the reviewed module
configurations rather than from the accessor the provisioner calls.
`examples/golden/cross-platform.digests.json` stores the resulting per-platform
digests and realization gaps, and
`tests/provisioning/end_to_end/test_golden.py` replays them.

## Ownership

| Concern | Owner |
| --- | --- |
| backend and state key | stack owner |
| Terraform execution | stack owner |
| credential injection | approved execution environment |
| security-edge routes and quarantine | security-edge owner |
| WSD domains and workloads | wsd owner |

## What is refused

`EXECUTION_REFUSED` is raised for any attempt to execute a plan: this repository
holds no execution authority. A scope that the catalog does not declare is refused
before it can be handed to Terraform, so a drifting compiler cannot silently create
a new root.