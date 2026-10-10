# Contract ownership and versioning

The contract root owns **wire contracts**, not provider eligibility or native execution authority.

- `contracts/source/` contains small, named, editable partitions for large source contracts.
- `contracts/openapi/`, `contracts/schemas/`, and `contracts/capabilities/` contain versioned, deployment-ready **bundles**. They remain self-contained because PHP, Python and generated clients load these artifacts directly.
- `scripts/contracts/build.py --check` reconstructs every split bundle and verifies its canonical and installed copies. Use `--write` only when intentionally assembling a reviewed unpublished version.
- Consumers must load exact versioned artifact names. Do not give a new version an old filename or schema `$id`.
- Previously published canonical versions are retained as historical references until a separately reviewed removal determines no external consumers or compatibility commitments remain. Unused *consumer copies* may be removed once all code generators, loaders and CI checks target the replacement.
- Wire readiness `v2` is immutable; the `v2.2` validation profile strengthens conditional eligibility and rejects unresolved required fields without changing the wire schema_version. Planning and Lifecycle both install the exact v2.2 profile. `scripts/contracts/generate_readiness.py` checks the embedded v2 OpenAPI projection.
- `migration-workload-readiness` is a **read-only eligibility assessment**. It never grants native writes or workload admission. Runtime still independently verifies signed custody, exact scope, freshness and E3/E4 evidence.

## Current active packages

| Capability | Canonical bundle | Installed consumer |
| --- | --- | --- |
| Planning migration | `openapi/planning-migration-v1.6.json` | `apps/console/resources/contracts/planning-migration-v1.6.json` |
| Inventory | `openapi/inventory-v1.9.json` | `apps/console/resources/contracts/inventory-v1.9.json` |
| Catalogue | `openapi/catalogue-v1.0.1.json` | `apps/console/resources/contracts/catalogue-v1.0.1.json` |
| Native migration input | `schemas/planning/migration-input-v4.json` | `services/planning/src/planning/infrastructure/inputs/migration-input-v4.json` |
| Migration support | `schemas/planning/migration-support-v2.json` | `services/planning/src/planning/infrastructure/inputs/migration-support-v2.json` |
| Workload-readiness validation (wire v2) | `schemas/planning/migration-readiness-v2.2.json` | Planning and Lifecycle exact packaged copies |

The source manifests are an editing representation, not independently hosted service contracts. Do not create separate, unverifiable drift between source fragments and the immutable deployed bundles.

## Duplicate cleanup

The byte-identical `contracts/fixtures/planning/synthetic-plan-v1.json` was removed. All fixture generation and live service test copies source `synthetic-plan-v1.1.json`. Fixture examples and partition source files are editable authoring inputs, not historically frozen published wire artifacts. Published API, event, schema and capability releases remain subject to the immutable-version gate.

The `planning/qualification-v2.1.json` validation profile tightens the externally delivered v2 qualification payload; its wire `version` remains `2` and Assurance keeps the existing v2 endpoint. This is a schema contract revision, **not** a native evidence upgrade.

## Archived duplicate schema identities

The published Inventory collection-page v1.1, v1.2 and v1.3 specifications historically declared the same `$id`. Their original bytes are preserved and pinned to Git blob identities; **do not register these three files together by `$id`**. The new `schemas/inventory/collection-page-v1.4.json` has its own identifier and represents the current schema definition. CI allows only those exact archived duplicates and rejects all new collisions or mutations to those historical artifacts.

## Collection-manifest source partitions

The Inventory collection manifest is authored in platform headers and ordered scope-specific arrays under `contracts/source/capabilities/migration-collection-manifest-v1/platforms/<provider>/`. Numeric prefixes preserve the published attribute sequence, including interleaved source/target/owner groups. Do not reorder these files or aggregate by scope: the resulting contract must continue matching the canonical bundle via `scripts/contracts/build.py --check`.

The archived Inventory and Planning API releases remain immutable. Unused Console copies of Inventory v1.7/v1.8 and Planning Migration v1.4 were pruned; the current consumers use Inventory v1.9 and Planning Migration v1.6. Older copies explicitly exercised by historical compatibility scripts remain in place.

## Active producer and consumer ownership

`architecture/contract-consumers.json` owns the **editable** active-release catalogue with per-contract producers, downstream consumers, installed artifact paths, source manifests, and explicit dependencies. `scripts/contracts/check.py` checks every declaration against real files and byte-identical installed copies. This is separate from immutable historical contract publications; replacing an active release updates the registry, never rewrites an older published API or schema.

All contracts with a declared implemented consumer are now represented by an active-release record. The registry validates source manifests, installed byte parity and the active OpenAPI specifications, including OpenAPI 3.0 foundation health. Asynchronous events are checked for channel/address uniqueness, valid operation bindings and referenced JSON Schema payloads; this is not a substitute for measured broker-event conformance.

## Migration admission owner commissioning

Lifecycle migration admission now requires an independently credentialed `catalogue` read owner in the protected native-owner configuration, alongside Planning, Governance, Inventory, Custody and Observer. The Catalogue owner must expose the current scoped `/internal/tenants/{tenant}/applications/{application}/environments/{environment}/current-planning-intent` read. At each admission/current-authority check Lifecycle compares the current Catalogue revision, immutable intent SHA and **complete unique workload-ID set** to Planning's reconciliation; a missing owner, stale revision, extra or missing VM holds the operation. Non-migration native workflows retain the existing owner set. Configure the dedicated scoped Catalogue credential and TLS trust before enabling migration, and include it in environment commissioning/rotation controls.

## E4 qualified-transformation provenance

The newly published `schemas/planning/independent-e4-field-provenance-v1.json` defines an independently attestable E4 field proof: Catalogue revision/digest, workload and field, exact source profile and desired/observed field hashes, proof/plan/acceptance digests, level, decision, revocation and validity interval. **It is a prerequisite for a future versioned migration-readiness wire release, not a currently commissioned execution grant.** The active wire v2/v2.2 admission validator intentionally **holds required qualified transformations**, because v2 field dispositions do not carry an independently verifiable E4 reference. Do not relax that invariant by accepting `evidence_source=independent_e4` alone; activate these transformations only after an authenticated Assurance proof lookup and a complete versioned producer/consumer rollout with negative tests.

## Executable consumer inventory and conformance

The editable active-release registry is checked against a **separate observation
of deployed code** in `scripts/contracts/runtime_inventory.py`. Executable
PHP/Python/TypeScript/Vue references to packaged JSON inside each bounded
product must resolve to exactly one registered byte-identical canonical
release. A retired copy may remain in a package only while it is not referenced
by deployed code. The checker also requires every shipped AsyncAPI release and
its event payload schemas to appear in the active inventory; removing records
from both editable registry maps is not sufficient to bypass this check.

`scripts/contracts/check.py` validates broker-address uniqueness across event
documents, all operation/channel/message bindings, complete event-type routing,
and channel-specific event discriminators. Existing immutable v1 event payloads
are **not** overwritten: channel-specific discriminator schemas are validation
profiles. Catalogue intentionally multiplexes its four intent fact types over
the single `catalogue.intent.changed.v1` exchange binding. Event delivery
consumers must still verify publisher identity, routing key, event ID and the
current authorization boundary independently.

The dedicated CI job compares `php artisan route:list --json` for Governance
and Catalogue with **every active OpenAPI operation owned by that service**,
including verbs and full paths. This proves published operations have concrete
runtime routes; it does not establish that all endpoints are documented or that
response bodies match. Producer fixture/live HTTP tests and installed-consumer
validation remain additional requirements, particularly for Planning, Inventory,
Console and Lifecycle.

All split-source file names and deployment destinations are confined to approved
repository subtrees, with resolved-path traversal checks. CI calls the source
assembler in `--check` mode, not `--write`. A changed published contract
requires a new release; no previous wire version is silently rewritten.

Do not equate these source-bound and synthetic conformance checks with live
provider qualification, independent E3/E4 evidence or authority for native
execution. Those gates remain separate and fail closed.

## 2026-10-09 owner-operation contract remediation

The Planning owner client no longer selects JSON Schema by a caller-defined
filename allowlist. `planning.infrastructure.owner_contracts` binds each
authenticated upstream owner, HTTP method and exact route pattern to one
installed response contract; unknown/mismatched operations fail closed before
the network call. `scripts/contracts/check.py` independently verifies that
**all six owner-response schema types** are registered and byte-identical to
their installed copies, even though `importlib.resources` constructs the
schema file path dynamically.

Inventory migration-input requests use **v4**, including reconciliation and
collection-coverage evidence. Assurance migration qualification requests use
**v2**, including API and application-flow E4 evidence. Historical v3 and v1
canonical schemas are retained, but are not accepted at these active owner
operations. The Inventory producer fixture is additionally passed through the
real Planning HTTPS owner-client validator, with an obsolete-version canary.

`schemas/planning/catalogue-current-v2.json` is a new immutable internal
Catalogue-current response contract. Its complete `$defs.Intent` is projected
from `schemas/planning/catalogue-input-v1.json`, and CI prevents divergence.
Planning consumes the installed v2 copy instead of the earlier shallow v1
envelope. The existing v1 internal copy remains for historical reference.

Planning's installed Catalogue foundation-event payload and Python package
copies are included in consumer parity checks. Live route conformance also
probes Inventory's separate authenticated Planning-input ASGI router.
These checks do not by themselves establish successful live deployments,
independent provider E4 qualification, or authorization for native execution.

## 2026-10-09 registered API and producer-conformance closeout

Inventory's native-read API is now published at
`openapi/inventory-native-input-v1.2.json`, embedding the exact canonical
`schemas/planning/migration-input-v4.json` success response. CI checks that
published response, canonical v4 schema and Planning's installed v4 schema
are identical. Inventory's real producer response is exercised through its
authenticated ASGI route and compared with both the API and Planning consumer.
The published native-input v1.1 schema is retained unchanged as historical.

Assurance evidence v1, Lifecycle migration boundary v2 and Planning's immutable
plan v1.1 are registered as active implemented OpenAPI releases. The required
owner/operation set is hard-coded independently of editable registry entries:
removing a contract from both registry maps does not disable validation.

Assurance evidence-review requests must contain exactly a JSON `decision`
with no additional fields; extra fields and non-JSON requests fail before
custody access. Route CI includes Assurance and fails on newly implemented
`/v1/` or `/internal/` operations unless covered by an active API contract
or explicitly listed as a pre-existing qualification-operation exception.
The exceptions are intentionally finite and must be reduced through
separately versioned specifications, never expanded automatically.

Synthetic, successfully authenticated ASGI contract probes are included for
Lifecycle's native-grant boundary and Planning's immutable plan. These are
in addition to Inventory's concrete producer fixture and negative authority
tests. They validate **transport and wire compatibility**, not independent
production commissioning or a live provider migration.
