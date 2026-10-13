# Active contract catalogue

This directory contains only current bounded-context wire and data contracts.
The authoritative inventory is `architecture/contract-consumers.json`.
Do not ship historical bundles, retired copies, contract aliases or compatibility
loaders. Source authorship fragments and test fixtures are not independent
published interfaces.

## Ownership and published interfaces

The owner defines each OpenAPI request and response, AsyncAPI event, JSON
Schema, capability and platform profile. Consumers validate the active
installed release before interpreting an authority or business decision.

- `contracts/openapi/`, `contracts/asyncapi/`, `contracts/schemas/`,
  `contracts/capabilities/` and `contracts/platforms/` contain current
  canonical artifacts.
- `contracts/source/` contains split authoring sources for generated
  canonical bundles. `contracts/fixtures/` contains test data only.
- The active registry identifies every producer, consumer, packaged copy,
  source manifest and release dependency.
- Existing published files remain byte-immutable against the Git review base.
  New versions replace genuinely changed interfaces. A version remains active
  only while it is actually consumed by a current producer or client.

## Installed runtime contracts

| Boundary | Active producer/schema | Consuming runtime |
| --- | --- | --- |
| Catalogue HTTP | `openapi/catalogue-v1.0.1.json` | Console |
| Inventory HTTP | `openapi/inventory-v1.9.json` | Console |
| Planning HTTP | `openapi/planning-v1.2.json` | Console |
| Planning migration | `openapi/planning-migration-v1.6.json` | Console |
| Lifecycle native jobs | `openapi/lifecycle-native-jobs-v1.1.json` | Console |
| Inventory planning input | `schemas/planning/inventory-input-v2.json` | Planning |
| Inventory migration input | `schemas/planning/migration-input-v4.json` | Planning |
| Governance delegated authorization | `openapi/governance-delegation-v2.json` | Lifecycle and Planning |
| Qualification | `schemas/planning/qualification-v2.1.json` | Planning |
| Migration support | `schemas/planning/migration-support-v2.json` | Planning |
| Migration readiness | `schemas/planning/migration-readiness-v2.2.json` | Planning and Lifecycle |

The v1 Inventory input schema remains active only because the current
Inventory native-input v1.3 API embeds that exact schema; the Planning
operation uses v2. Do not delete an actively embedded response merely to
reduce the version count. The common v1 error shape also has declared active
service consumers; it is not an archive copy.

The two installed `foundation-event.json` consumer filenames both derive
from `schemas/events/catalogue-foundation-recorded-v1.json`.
Console bundles the current migration feature policy for its Vue client.
All packaged consumers must have actual executable loaders and exact source
byte parity.

## Assurance and release qualification

`scripts/contracts/check.py` verifies canonical validity, schema and
source generation, actual consumer copies, owner operations and current
route/authority constraints. The Git review-base gate enforces unchanged
surviving canonical bytes. Real producer and consumer behavior, authenticated
authorization denials and cross-tenant isolation require separate executed
proof; a passing schema check is not sufficient.

Phase 2 adds source-pinned OCI image and Python wheel verification. The
artifact workflow examines built filesystems, compares complete shipped
runtime source, checks packaged contract bytes, and aggregates all nine
runtime images and five Python wheels into exact operation-to-image
bindings. Registry declarations without verified installed loaders are
clearly distinguished from packaged consumers.

Run the source and test checks from the repository root:

```sh
python scripts/contracts/build.py --check
python scripts/contracts/generate_readiness.py
python scripts/contracts/generate_authority_releases.py --check
python scripts/contracts/check.py
python scripts/contracts/dependency_graph.py
python scripts/contracts/runtime_binding_coverage.py
python -m unittest discover -s tests/contracts -p 'test_phase2_artifacts.py' -v
```

Built-artifact attestation is an actual high-cost GitHub Actions suite
(`qualification.yml`, `suite=contract-artifacts`). The consolidated pull-request
CI invokes it for affected contract changes, and it may also be dispatched
explicitly for release requalification. Its nine image/five wheel attestations
must aggregate successfully; an image matrix pass alone is not sufficient.
The separate strict `CI / Contract assurance` gate remains red until
every active operation earns independently measured behavioral evidence.

See [contract assurance](../docs/contracts/assurance.md),
[assurance phases](../docs/contracts/assurance-phases.md), and
[release quality](../docs/contracts/release-quality.md).
