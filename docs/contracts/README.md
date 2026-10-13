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
