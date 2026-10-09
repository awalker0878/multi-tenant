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

## 2026-10-09 follow-on implementation

- **P0 startup:** repaired missing `else`; P04 CI now compiles Inventory and the worker and imports all startup dependencies before running integration tests.
- **Unified native collection budget:** `profile_read_manifest.bounds` determines both worker authorization and completion; OpenStack destination has eight native GET permits.
- **Durable Inventory custody:** `008_migration_collection_ledger.sql` contains immutable signed receipt headers and per-field observation/applicability projections. A worker-scoped internal endpoint verifies installed trust, exact source/target profile SHA, tenant/site, generation, installation and current profile status before atomic append; Planning reads the latest database receipt, never a stale earlier file.
- **Pinned release field set:** Planning independently loads a protected allowlist from `PLANNING_MIGRATION_COLLECTION_REGISTRY_FILE` (manifest_file, SHA-256, and authorized release_sha256 list). Every coverage summary must match exact attribute IDs, source/target/owner scopes, manifest SHA-256 and receipt freshness.
- **Datasetless disks:** Inventoried native disk coverage is never discarded. Owner attestation plus signed per-disk E4 independent impact receipt is required when Catalogue disk.dataset_id is null. Mismatched owner hashes, a reused native disk, foreign profile or revoked/expired receipt still hold.
- **Native semantics and boot:** Planning emits `matched`, `drifted`, `unobserved`, `qualified_transformation`, `approved_omission` statuses. Independently bound E4 receipts (not owner text or guest metadata) are required for transformations and OpenStack Secure Boot claims.
- **Unified operator preview:** Planning exposes a read-only `migration-workload-readiness` endpoint which reads the current confirmed Inventory review and current Catalogue intent. Console obtains the review from Inventory and shows v2 workloads, field dispositions, evidence holds and expiry. Authoritative application/VM/disk/NIC selectors replace free-form UUID/digest entry.
- **AHV runtime versions:** Native HTTP rejects URLs diverging from pinned stage namespace versions. AHV destination plans are fixed to v4.3. Source capture execution requires an exact pinned v4.3 schema-v3 plan; Planning rejects independently qualified v4.2 when the actual executor cannot issue v4.2 requests. Fixed route allowlists still reject unknown native operations.

## Outstanding implementation/commissioning and evidence

1. **Independent worker field producer and full 278-attribute mapping (not complete).** The authenticated append-only ledger and per-field SQL projection exist; real native GET/operation-to-field publication, independent observer signature issuance, application owner-input collection, full installed API namespace probes, revocation notifications, coverage pagination and deployment wiring must be completed and validated for every platform before completeness can be asserted. An incomplete receipt remains held.
2. **Native effective source-policy collection (not complete).** VMware NSX and AHV enforced-policy membership/order/service resolution need current independent probes. OpenStack source Secure Boot can now be supplied by E4 independent evidence but no native producer has been commissioned. A source with unverified policies/boot remains held rather than having facts manufactured.
3. **Cross-provider semantic conversion (not commissioned).** Required OS, encryption, storage, hardening, topology and failure-domain fields still need qualified native observations, conversion plans and independently observed outcomes to permit positive equivalence.
4. **Exact API operation selection across the full platform matrix (partially implemented).** AHV HTTP stage versions and fixed route allowlists now fail closed. The selected operation-to-stage-plan binding and equivalent VMware/OpenStack per-operation enforcement must be independently qualified before production effects.
5. **CI and deployed E3/E4 (unverified).** Dedicated tests were added, but this PR requires real PostgreSQL, Laravel, TS/Playwright and live-read commissioning, positive and negative producer→Inventory→Planning→Console→Lifecycle gates, expiry/revocation and cross-tenant tests. Queued CI is not a passing gate.


## Release gate

Do not mark PR #64 ready, merge, or enable native effects until relevant CI is green, the collector and Console APIs are integrated end to end, runtime version enforcement is exact, independent qualifications are valid, and the outstanding evidence ledger is reconciled. All failed or unobserved conditions remain `held`.
