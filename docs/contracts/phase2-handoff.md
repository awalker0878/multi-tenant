# Current contract remediation handoff

Runtime remediation is underway under the current instruction to continue
independent work despite external blockers. Phase 1's deployment-owned collection
manifest enrollment remains **BLOCKED**; it does not prevent repository fixes.
The current result is **INCOMPLETE**, not a qualified release. Follow
[the current ledger](phase2-ledger.md) and freshly executed CI evidence.

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

## Current runtime correction

Planning migration v2 preserves the route expiry, API compatibility and readiness
fields that caused the P09 mismatch. Its strict closed schemas, Error v2 responses,
query-key binding and migrated private Console copy replace the prior release.
Surviving canonical bytes remain immutable. The producer and consumer regression
checks must pass against the final commit before the mismatch is closed.

Authentication-only receipts no longer count as effective authorization. The
required aggregation stays red until current-authority and cross-tenant boundaries
have real evidence. Source schemas have their actual definition/validator roles;
no remote consumer is invented to fill a reporting gap.

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
