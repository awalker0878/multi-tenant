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