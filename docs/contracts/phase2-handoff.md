# Conditional Phase 2 handoff

Phase 2 implementation has not started. Phase 1 remains **FAIL** until Planning's
externally provisioned collection-manifest registry and manifest identity are
independently verified. The generated release inventory marks that release as
requiring correction. Do not promote the branch as a completed Phase 1 baseline.

## Entry points and acceptance

| Work | Entry points | Acceptance |
| --- | --- | --- |
| Producer/consumer conformance | `check_http.py`, `route_conformance.py`, `assurance_routes.py`, `measured_consumers.py`, service `tests/` | Every actual status and body is validated against the consumer's exact active contract. No absent or skipped probe mints a receipt. |
| Exact installed versions | `runtime_inventory.py`, `installed_usage.py`, `artifact_attestation.py`, `aggregate_artifacts.py` | All 35 JSON copies plus generated projections match current canonicals in the five wheels and nine source-pinned images. Verify externally mounted manifests against independently enrolled release identity. |
| Authorization and isolation | `python_denials.py`, `laravel_denials.php`, owner authentication/delegation tests | Exercise missing/revoked/wrong-audience credentials, altered scopes, and cross-tenant requests through every protected operation. |
| Freshness and idempotency | Planning/Lifecycle owner adapters, Governance action transactions, command receipts | Expired/replayed/changed-digest requests fail without unauthorized effects; legitimate retries retain their exact result and scope. |
| Events and broker | Planning `infrastructure/facts/broker.py`, `infrastructure/messaging/`, Catalogue/Governance publishers, `deploy/dependencies/stateful/` | Validate producer identity, current payload version, real queue/binding permissions, poison delivery, deduplication and commit-before-ack. Cover Inventory and Planning fact publications as well as all active AsyncAPI channels. |
| Native authority and effects | Lifecycle `native_owners.py`, worker `owner_protocol.py`, `qualify_capabilities.py`, `scripts/p08/` | Externally owned custody/observer/provider boundaries and every installed method/mode require independent E3/E4 identity, custody and effect evidence. E2 fixtures grant no native support. |
| Release evidence | `combine_assurance.py`, `aggregate_artifacts.py`, `.github/workflows/ci.yml`, `qualification.yml` | Current commit/run/attempt/file digests, complete measured claims, exact image/wheel identity and required CI results all agree. Keep existing strict gates. |

## Known runtime findings to resolve in Phase 2

- Baseline CI run `38577108733` reports 204 missing measured boundaries,
  0/166 qualified HTTP operations and only 4/75 qualified canonical releases.
  This is runtime qualification, not evidence that canonical syntax failed.
- Executed `scripts/p09/check_contract.py` fails when validating actual
  `MigrationSupport.read` output against Planning migration v1.6: route records
  include `api_compatibility`, `expires_at` and `readiness`, which its closed
  response schema rejects. Publish and integrate an appropriate current release
  without rewriting surviving published bytes or introducing a compatibility
  loader. Do not weaken that test.
- `scripts/p08/check_any_to_any.py` passed its nine-direction outcome checks,
  144 partial-service rejection probes and 126 typed native method checks.
  These are synthetic source/runtime checks, not installed native qualification.
- Source-only validation schemas and producer-owned definitions must not require
  invented remote consumers merely to satisfy the measured assurance model.

## Infrastructure and dependencies

Use each component's locked uv environment and the pinned PHP/Composer/Node
versions in CI. Five Python suites passed 2,046 tests; 180 PostgreSQL/qualified
infrastructure tests were explicitly skipped because their required environments
were absent. Provision PostgreSQL, authenticated TLS RabbitMQ, Temporal and the
qualified provider/observer identities for their live tests.

The missing Phase 1 external input is
`PLANNING_MIGRATION_COLLECTION_REGISTRY_FILE`, whose protected registry names
`manifest_file`, `manifest_sha256` and `releases`. Obtain the deployment owner's
actual registry, referenced manifest, enrolled release identities and provenance.
Compare the manifest's canonical JSON digest to the active collection manifest,
verify protection/ownership and supported deployment commitments, then update
the release inventory from that independent evidence. A locally invented fixture
cannot establish deployed consumption or an external compatibility commitment.
