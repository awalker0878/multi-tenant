# Active contract ownership

The deployed source of truth is [the active contract catalogue](../../contracts/README.md)
and `architecture/contract-consumers.json`. Only active canonical OpenAPI, AsyncAPI,
JSON Schema, capability and platform releases exist in the working tree.

## Runtime boundaries

- Each owning bounded context defines the request, response, event and eligibility decision.
- HTTP requests require authenticated authority, tenant-scoped identity, exact operation
  contracts, freshness and scoped idempotency when the behavior is implemented.
- Current producer output is validated against the installed consumer's exact release.
- Runtime installed copies are registered and checked against executable loaders, built
  images and packaged wheels. Unregistered copies and undeclared API routes fail closed.
- Simulated E2 success never implies native E3/E4 qualification or write permission.

## Active examples

- Catalogue: `contracts/openapi/catalogue-v1.0.1.json` and current Planning input reads.
- Inventory: `contracts/openapi/inventory-v1.9.json` and native-source input reads.
- Planning: `contracts/openapi/planning-v1.2.json`, migration and immutable plan reads.
- Lifecycle: `contracts/openapi/lifecycle-v1.json`, placement, native boundary and alert delivery.
- Governance/Assurance: authenticated authority, qualification and custody endpoints.
- Worker: `contracts/openapi/worker-simulation-v1.json` and native method/effect operations.

## Verification

`scripts/contracts/check.py` checks only live releases, bindings, installed files,
route/schema equivalence, and negative security cases. The Git review-base check
in `scripts/p01/contracts/compatibility.py` rejects modifications to surviving
published canonical releases, while allowing deletion of unconsumed releases
from this undeployed checkout. Current runtime copy registration is mandatory.

Contract assurance is deliberately evidence-gated, not a schema-only passing
assertion. See [assurance](assurance.md) and
[release quality](release-quality.md) for current requirements.

## Integrity baseline and independent discovery

Phase 1 is contract integrity, dependency closure and release rationalization.
Phase 2 is runtime producer/consumer and security conformance. See the
[implementation ledger](phase1-ledger.md) for executed checks and the
[conditional Phase 2 handoff](phase2-handoff.md) for entry points and open evidence.

`scripts/contracts/discovery.py` independently resolves JSON/YAML references,
URI schema identities, embedded projections, capability/profile schemas and
source-assembly relationships. The declared canonical graph must match that
discovery exactly and have no cross-release cycles. Recursive local schemas and
cyclic service communication are separate relationships and remain permitted.

The generated `architecture/contract-dependencies.json` and
`architecture/contract-release-inventory.json` are checked in CI. They are reports,
not authoritative input to discovery. `active_releases` owns release metadata;
the `contracts` index must agree exactly. Producer-local schema validation,
installed loaders, compiled projections, source-only definitions and external
mounted inputs have distinct evidence labels.

Retirement checks use the actual trusted Git review base, before the separate
new-publication quality cutover. Previous copy names, typed loader keys and
canonical identities expose surviving references even if registry rows are
deleted. Legitimate migration/removal is allowed when those references are gone.
No surviving published canonical bytes are rewritten and no retired bundles,
aliases or compatibility loaders are introduced.

Current capability labels and their active serialized method identifiers remain
distinct. Their existing mapping does not accept retired contract versions or
alternate obsolete identifiers; it is required by the current support/readiness
boundary.
