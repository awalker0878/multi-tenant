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
- **Durable Inventory custody:** `008_migration_collection_ledger.sql` contains immutable signed receipt headers and per-field observation/applicability projections. The independent worker helper `migration_collection_writer` generates GET-only value digests and a domain-separated Ed25519 signing request, then publishes to Inventory through the authenticated worker port. The private key remains outside Inventory and the worker, under a separate signer callback. A worker-scoped internal endpoint verifies installed trust, exact source/target profile SHA, tenant/site, generation, installation and current profile status before atomic append; Planning reads the latest database receipt, never a stale earlier file.
- **Pinned release field set:** Planning independently loads a protected allowlist from `PLANNING_MIGRATION_COLLECTION_REGISTRY_FILE` (manifest_file, SHA-256, and authorized release_sha256 list). Every coverage summary must match exact attribute IDs, source/target/owner scopes, manifest SHA-256 and receipt freshness.
- **Datasetless disks:** Inventoried native disk coverage is never discarded. Owner attestation plus signed per-disk E4 independent impact receipt is required when Catalogue disk.dataset_id is null. Mismatched owner hashes, a reused native disk, foreign profile or revoked/expired receipt still hold.
- **Native semantics and boot:** Planning emits `matched`, `drifted`, `unobserved`, `qualified_transformation`, `approved_omission` statuses. Independently bound E4 receipts (not owner text or guest metadata) are required for transformations and OpenStack Secure Boot claims.
- **Unified operator preview:** Planning exposes a read-only `migration-workload-readiness` endpoint which reads the current confirmed Inventory review and current Catalogue intent. Console obtains the review from Inventory and shows v2 workloads, field dispositions, evidence holds and expiry. Authoritative application/VM/disk/NIC selectors replace free-form UUID/digest entry.
- **AHV runtime versions:** Native HTTP rejects URLs diverging from pinned stage namespace versions. AHV destination plans are fixed to v4.3. Source capture execution requires an exact pinned v4.3 schema-v3 plan; Planning rejects independently qualified v4.2 when the actual executor cannot issue v4.2 requests. Fixed route allowlists still reject unknown native operations.

## Outstanding implementation/commissioning and evidence

1. **Independent worker field producer and full 278-attribute mapping (not complete).** The authenticated append-only ledger, per-field SQL projection, GET-only generic worker witness mapper and externally signed-envelope publisher exist. Platform collectors still must emit every actual native GET field witness, and the separate Ed25519 signing service, independent observer, application owner-input collection, full installed API namespace probes, revocation notifications, coverage pagination and deployment wiring require integration/qualification before completeness can be asserted. An incomplete receipt remains held.
2. **Native effective source-policy collection (not complete).** VMware NSX and AHV enforced-policy membership/order/service resolution need current independent probes. OpenStack source Secure Boot can now be supplied by E4 independent evidence but no native producer has been commissioned. A source with unverified policies/boot remains held rather than having facts manufactured.
3. **Cross-provider semantic conversion (not commissioned).** Required OS, encryption, storage, hardening, topology and failure-domain fields still need qualified native observations, conversion plans and independently observed outcomes to permit positive equivalence.
4. **Exact API operation selection across the full platform matrix (partially implemented).** AHV HTTP stage versions and fixed route allowlists now fail closed. The selected operation-to-stage-plan binding and equivalent VMware/OpenStack per-operation enforcement must be independently qualified before production effects.
5. **CI and deployed E3/E4 (unverified).** Dedicated tests were added, but this PR requires real PostgreSQL, Laravel, TS/Playwright and live-read commissioning, positive and negative producer→Inventory→Planning→Console→Lifecycle gates, expiry/revocation and cross-tenant tests. Queued CI is not a passing gate.


## 2026-10-09 contract-integration corrective audit (latest)

**Code changes applied**

1. Inventory's strict migration input schema is now packaged byte-for-byte
   from the canonical `migration-input-v3.json` including per-scope
   `expires_at` and optional typed source observation timestamps. Run
   `python scripts/p05/sync_migration_inputs.py --check`; P05 CI also runs
   `test_migration_owner_contract.py` on actual Inventory coverage evaluation
   and the `WorkloadProfiles.planning` response against the *installed* schema.
2. Console's PlanningClient recognizes `migration-workload-readiness` with
   `plan.read` delegation and typed response. Readiness requires a current
   Catalogue logical workload selection. The server resolves matching
   confirmed Inventory native review by application/environment/workload
   instead of using the unrelated site-latest review, and holds if a bounded
   lookup is incomplete or ambiguous. Planning preview and native admission
   both query the same independent E4 verification path.
3. Required native semantic comparisons expose desired value, observed value,
   source/independent-E4 provenance, evidence age, disposition and next action.
   Unknown OS, hardening, image or storage encryption/key semantics cannot
   be promoted from guest labels: an exact independent E4
   `verified_observation` carrying a signed source-profile and field
   digest is required to assert equivalence.
4. AHV qualified version selection intersects installed, entitled, E3/E4
   accepted and **actually executable** releases before choosing a version.
   The immutable Planning migration content includes a pinned
   `api_selection` (capability, side, family, version, qualification evidence
   digest, expiry, source/target profile and release); both validation and
   execution re-resolve and compare the tuple. AHV transport still permits
   only fixed qualified v4.3 routes. Non-v4.3 is held rather than substituted.
   OpenStack native-discovered min/max compute and volume microversion ranges
   are retained and matched numerically without implying missing services.
5. Workers now capture successful TLS native GET-response digests inside the
   lease and atomically publish `native_read_receipts` with Inventory pages.
   Inventory validates the bounded GET outbox and requires each later signed
   native field receipt to reference its same-generation operation, response
   SHA and observed time. Signed receipts have monotonic generation sequences;
   delayed older generations, duplicate sequence conflicts and timestamp
   regression are held. Failed/partial discovery appends source/target
   generation invalidations so old receipts do not survive negative evidence.
6. Resolved workload expiry is bounded by both declared E4 expiration and
   the *exclusive* observed_at + 30 seconds freshness deadline. Coverage
   completeness matches each release-bound manifest's exact attribute set,
   not the count of summary records.

**Not yet proven/commissioned**

- The independent Ed25519 signer, all platform-native field extraction
  adapters and complete manifest coverage, especially VMware NSX/AHV policy,
  guest attestation and encryption/key ownership, still require connected
  producer and external E3/E4 runtime proof.
- An effective security policy or syntactically valid signed receipt does not
  itself constitute equivalence. Missing/invalid measurements remain held.
- Full PostgreSQL and browser/Console→Planning→Lifecycle integration and
  native observer commissioning are release gates. CI success is not implied
  by these commits; see PR #64 checks.

## Release gate

Do not mark PR #64 ready, merge, or enable native effects until relevant CI is green, the collector and Console APIs are integrated end to end, runtime version enforcement is exact, independent qualifications are valid, and the outstanding evidence ledger is reconciled. All failed or unobserved conditions remain `held`.
