# Source intent, native inventory and installed-version qualification — remediation ledger

**Scope:** Catalogue intent → Inventory current native observations → Assurance installed-version/E3/E4 evidence → Planning resolved workload readiness → Console preview and Lifecycle admission.

**Branch:** `codex/capability-runtime-assurance-audit-fixes` (draft PR #64). **State:** E2 implementation in progress; **not independently commissioned**. A signed receipt or a generated manifest alone must never confer E3/E4 equivalence or native write permission.

## Applied code changes (2026-10-09)

| Finding | Implementation | Verification |
| --- | --- | --- |
| Assurance flow field whitelist excluded per-VM interface cases | Permit optional strictly typed `workload_interface_cases` in the independently approved signed flow record. Reject duplicate workload IDs, invalid digests, stale probes and invalid E4 cases. Old route-only flow proof does **not** turn into workload proof. | Controller contract requires integration testing with real Assurance qualifications; Planning has per-VM positive/negative cases |
| Dataset accountable owner was used as workload identity | Membership joins through `workload.disks[].dataset_id`; owners remain independently accountable. Duplicate, unknown and overlapping disk coverage are held. | `test_workload_reconciliation.py` |
| Historical confirmation bound preceded deduplication | PostgreSQL `DISTINCT ON` selects the latest confirmation for each logical workload before applying the 101-row sentinel. | PostgreSQL integration with 101+ historical confirmations still required |
| Readiness expired after constituent evidence | Route and workload deadlines are constrained by API entitlement/version/qualification, E3/E4 route proof, interface case, Inventory field receipts, and signed collection envelope; expired or unbounded evidence holds. | `test_api_compatibility.py`, `test_migration_readiness.py`, `test_workload_reconciliation.py` |
| API version string counted as collection evidence | Inventory now requires an exact value in the profile's installed namespace/version inventory. Unsupported versions remain held. | `test_migration_collection_coverage.py`, `test_migration_collection_evidence.py` |
| Source-intent comparison omitted required semantics | Planning emits field dispositions and holds unknown required OS, image, architecture, hardening, disk boot/encryption/storage-class, required application requirements and failure-domain semantics; optional placement does not block. Inventory retains additional native raw facts without asserting semantic equivalence. | `test_source_intent_reconciliation.py`, source observation regression suite |

## Remaining implementation and qualification boundaries

1. **Collector ledger and complete installed namespace inventory (open).** A single signed mounted file is still the input, not a durable per-field, per-workload receipt ledger. Build the collector's persisted receipt/outbox protocol, with generation, operation, API family/version, value digest, evidence reference, owner custody, revocation and expiry. Expose scoped, paginated Inventory queries; negative discovery invalidates old receipts. Installed namespace coverage must be verified for every supported source/target API family, not inferred from version labels.
2. **Datasetless disk dispositions (open).** `dataset_id=null` is held rather than ignored. Provide a typed, owner-approved, scope-bound disposition (temporary/scratch, deliberately excluded with measured impact, or mapped to a replacement dataset), with independent risk and lifecycle approval where required. Do not invent a dataset or make null eligible by default.
3. **Semantic native normalization and independent equivalence (open).** Extend trusted collectors for actual OS/architecture, boot/controller roles, storage class, key/encryption, hardening, topology/failure-domain and workload requirements. Cross-platform conversions need distinct outcomes, owner approval, independent probe receipts, and an expiry-bounded acceptance; no string equality between native guest IDs and Catalogue OS values.
4. **Single workload-level operator projection (open).** Expose an authorized, Catalogue-backed application/revision/workload/device selector API and v2 readiness preview. The Console must display the exact resolved holds and deadlines Lifecycle uses. UI-only checks do not satisfy admission.
5. **Selected-version execution enforcement (open).** Planning already selects a qualified API operation/version; AHV's executor still uses fixed v4.3 routes and its native plan validates fixed versions. Bind the exact qualified namespace/operation manifest, evidence digest, installation/profile, and expiry to each immutable executable plan. Reject an actual HTTP path/version or operation not present in that manifest. Do not silently substitute a compatible-looking API release.
6. **True E3/E4 commissioning (open).** Exercise each approved VMware, AHV and OpenStack version/method with current independent observers, including effective security, network flows, data integrity, recovery, tenant isolation and rollback. Capture positive *and* negative evidence through Lifecycle admission and receipt replay/revocation. No E3/E4 qualification is implied by this ledger.

## Release gate

Do not mark PR #64 ready, merge, or enable native effects until relevant CI is green, the collector and Console APIs are integrated end to end, runtime version enforcement is exact, independent qualifications are valid, and the outstanding evidence ledger is reconciled. All failed or unobserved conditions remain `held`.
