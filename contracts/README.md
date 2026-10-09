# Contract ownership and versioning

The contract root owns **wire contracts**, not provider eligibility or native execution authority.

- `contracts/source/` contains small, named, editable partitions for large source contracts.
- `contracts/openapi/`, `contracts/schemas/`, and `contracts/capabilities/` contain versioned, deployment-ready **bundles**. They remain self-contained because PHP, Python and generated clients load these artifacts directly.
- `scripts/contracts/build.py --check` reconstructs every split bundle and verifies its canonical and installed copies. Use `--write` only when intentionally assembling a reviewed unpublished version.
- Consumers must load exact versioned artifact names. Do not give a new version an old filename or schema `$id`.
- Previously published canonical versions are retained as historical references until a separately reviewed removal determines no external consumers or compatibility commitments remain. Unused *consumer copies* may be removed once all code generators, loaders and CI checks target the replacement.
- `migration-workload-readiness` is a **read-only eligibility assessment**. It never grants native writes or workload admission. Runtime still independently verifies signed custody, exact scope, freshness and E3/E4 evidence.

## Current active packages

| Capability | Canonical bundle | Installed consumer |
| --- | --- | --- |
| Planning migration | `openapi/planning-migration-v1.6.json` | `apps/console/resources/contracts/planning-migration-v1.6.json` |
| Inventory | `openapi/inventory-v1.9.json` | `apps/console/resources/contracts/inventory-v1.9.json` |
| Catalogue | `openapi/catalogue-v1.0.1.json` | `apps/console/resources/contracts/catalogue-v1.0.1.json` |
| Native migration input | `schemas/planning/migration-input-v4.json` | `services/planning/src/planning/infrastructure/inputs/migration-input-v4.json` |
| Migration support | `schemas/planning/migration-support-v2.json` | `services/planning/src/planning/infrastructure/inputs/migration-support-v2.json` |
| Resolved workload readiness | `schemas/planning/migration-readiness-v2.json` | `services/planning/src/planning/infrastructure/inputs/migration-readiness-v2.json` |

The source manifests are an editing representation, not independently hosted service contracts. Do not create separate, unverifiable drift between source fragments and the immutable deployed bundles.

## Duplicate cleanup

The byte-identical `contracts/fixtures/planning/synthetic-plan-v1.json` was removed. All fixture generation and live service test copies source `synthetic-plan-v1.1.json`. Fixture examples and partition source files are editable authoring inputs, not historically frozen published wire artifacts. Published API, event, schema and capability releases remain subject to the immutable-version gate.

The `planning/qualification-v2.1.json` validation profile tightens the externally delivered v2 qualification payload; its wire `version` remains `2` and Assurance keeps the existing v2 endpoint. This is a schema contract revision, **not** a native evidence upgrade.

## Archived duplicate schema identities

The published Inventory collection-page v1.1, v1.2 and v1.3 specifications historically declared the same `$id`. Their original bytes are preserved and pinned to Git blob identities; **do not register these three files together by `$id`**. The new `schemas/inventory/collection-page-v1.4.json` has its own identifier and represents the current schema definition. CI allows only those exact archived duplicates and rejects all new collisions or mutations to those historical artifacts.

## Collection-manifest source partitions

The Inventory collection manifest is authored in platform headers and ordered scope-specific arrays under `contracts/source/capabilities/migration-collection-manifest-v1/platforms/<provider>/`. Numeric prefixes preserve the published attribute sequence, including interleaved source/target/owner groups. Do not reorder these files or aggregate by scope: the resulting contract must continue matching the canonical bundle via `scripts/contracts/build.py --check`.

The archived Inventory and Planning API releases remain immutable. Unused Console copies of Inventory v1.7/v1.8 and Planning Migration v1.4 were pruned; the current consumers use Inventory v1.9 and Planning Migration v1.6. Older copies explicitly exercised by historical compatibility scripts remain in place.
