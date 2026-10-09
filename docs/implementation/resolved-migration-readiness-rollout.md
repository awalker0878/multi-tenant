# Resolved migration readiness — bounded-context contract and commissioning ledger

**Branch:** `codex/capability-runtime-assurance-audit-fixes` · **PR:** #64 · **status:** engineering changes, source CI and native commissioning pending.

## Authority boundaries

| Owner | Only authoritative for | New composition |
| --- | --- | --- |
| Catalogue | Immutable desired application/workload/dataset/dependency intent and revision digest | Source-intent reconciliation **reads**, never rewrites, this intent |
| Inventory | Observed native identities, installed versions, per-field collection, disk/NIC facts, confirmed migration reviews | OpenStack per-SG read accounting; AHV namespace-specific native reads; `migration_collection_coverage.evaluate` |
| Assurance | Independent E3 operation/route evidence, revocation and E4 receiving acceptance/optional omissions | Planning reads current per-route and per-operation evidence |
| Planning | Exact route eligibility, transformation/omission decisions, owner joins and immutable plans | `migration_readiness.resolve`; `source_intent_reconciliation.reconcile`; protected execution-plan re-read |
| Console | Authenticated display/operator selection only | Displays Planning's **same** readiness SHA, expiry and holds; cannot emit proof or native write grants |
| Lifecycle | Final native admission, custody epochs, direct current owner recheck and effect fencing | Rejects missing/stale/tampered readiness from Planning; re-fetches on every current check |

### Contract

`contracts/schemas/planning/migration-readiness-v1.json` defines the closed, read-only **route-level** projection. The `readiness_sha256` covers all contract fields except itself. The current route projection requires exact source/target installation/profile/version, E3, E4 and operation-qualified API observations. No browser or route declaration establishes these conditions. `workload_admission_authorized=false` and `native_write_authorized=false` are unconditional in this contract; Lifecycle retains the independent authority to admit or deny an actual native effect.

**Important:** A route being `eligible` does not prove a **particular VM** matches Catalogue intent, that every field in the 278-row manifest was gathered, or that a receiving platform passed its actual migration rehearsal. These are separate, mandatory native commissioning requirements. Do not call the overall migration readiness feature production-complete on the strength of a route-only E2 test.

### Source-intent reconciliation

`planning.domain.source_intent_reconciliation.reconcile` is the Planning-owned *pure comparison* of immutable Catalogue logical workloads and Inventory-owned current source profiles, under explicit owner-confirmed one-to-one native identity links. It holds unmatched native identities/generations, CPU/memory/firmware/Secure Boot drift, incomplete disk or NIC sets, stale source profiles, missing dataset mapping and absent independent dependency evidence. A VM name or matching UUID label does **not** establish a binding. It supplies **no native grant**.

**Not yet integrated**: live Catalogue + Inventory owner ports for an immutable logical-to-native association, per-VM UI discrepancy display and the native-operation admission input. The current module must not be described as an activated reconciliation service.

### Per-field collection

`inventory.domain.migration_collection_coverage.evaluate` consumes the declared manifest, an exact installed tuple/generation and scoped per-field native or independent-owner receipts. It denies missing/expired/duplicate/cross-installation facts, distinguishes absent applicability from unobserved applicability and never converts `native_field_candidate` to actual E3/E4 qualification. The raw, append-only collection evidence and all applicable manifest rows must be persisted and re-evaluated at source/review/effect boundaries before workload migration can be independently admitted.

**Not yet integrated**: the worker's every native API operation to the manifest-derived read ledger, durable field receipt persistence, an Inventory service-only coverage endpoint and the Planning/Console/Lifecycle consumption of its live result. A crosswalk declaration or matching capability flag does not close this gap.

### Installed API operations

- AHV native source workload paths now select the independently configured v4 namespace versions, rather than stamping v4.3 for every namespace; server-only v4.2 discovery does not imply all namespaces support v4.2.
- OpenStack source workload completion now accounts for five baseline operations, every Cinder volume GET and every Neutron security-group GET. The existing scoped request authorization and hard budget still apply. SG-heavy VMs can remain held when the budget is exceeded; the collection plan must be made manifest-driven rather than bypassing safety limits.
- Planning fails closed for operational routes with missing `api_usage`/independent operation evidence and prefers the lowest *qualified* version when multiple are available. Static/v1 route declarations do not yet establish exhaustive code-derived API-use coverage.

**Not yet integrated**: operation-by-operation probe-to-runtime comparison for every supported platform+method/version, drift invalidation across all worker call sites and actual E3/E4 native release readback. Never substitute a configured namespace version or installed product number for a native capability probe.

## Completion gates — do not silently close

1. **Source ownership:** Catalogue revision and Inventory generation/VM incarnation are joined through an independently confirmed one-to-one logical workload link; zero unmapped/extra native devices, all dependencies and datasets explicitly dispositioned.
2. **Collection:** All *applicable* manifest rows have current scoped receipts, unknown applicability is held, required external proofs are independent, and no critical security/policy/guest attribute is inferred or silently omitted.
3. **Installed release:** Every native method uses an exact live-discovered installed namespace/version, entitlement and adapter-operation qualification; the runtime request sequence is checked against qualified read/write manifests.
4. **Single admission:** Planning's service-only protected response binds the workload reconciliation, field coverage and E3/E4 receipts to the same exact plan, and Lifecycle revalidates these immediately before *every* native effect. The current route contract alone does not satisfy this gate.
5. **Operator view:** Console presents each per-VM hold, source observation discrepancy, optional omission/impact, selected native version and expiry; stale/unavailable reads cannot claim eligibility.
6. **CI:** Required checks pass at the exact head, including Inventory/Planning/Lifecycle, static/mypy, schema, runtime owner forgery, cross-tenant, replay, expiry and revocation tests; no merely queued/skipped jobs count.
7. **Native commissioning:** Authorized positive/negative E3 rehearsals, separate receiving-side E4 acceptance, independent observer records, approved operational runbooks/rollback and real version/network/guest/disk/data checks exist for the intended installation/route.

**Promotion rule:** Leave PR #64 draft and native writes disabled until gates 1–7 have evidence and all required CI is green. Only real operating owners can supply E3/E4, entitlement and receiving acceptance; neither a code generator nor synthetic test evidence can do so.
