# ExecPlan — Close contract coverage gaps at service-to-service authority boundaries

**Status:** Audit remediations committed, exact-head verification pending. As of 2026-10-11, the branch `codex/capability-runtime-assurance-audit-fixes` contains the implementation commits below, but an **exact-head green contract-integrity CI run has not been recorded**. Do not mark this plan verified until the acceptance matrix is satisfied.

This is a living document. Keep Progress, Surprises & Discoveries, Decision Log and Outcomes & Retrospective current after every checkpoint.

## Purpose / Big Picture

Every cross-service authority decision (delegated source reads, native input, current catalogue intent, approval, evidence, qualification) must be documented by an active, versioned OpenAPI release with the producer's real HTTP statuses. A missing `/v1/` or `/internal/` route must fail runtime route conformance, rather than silently passing because only documented→implemented routes are checked. Do not grant native-write authority, migrate a workload or elevate E2 fixture observations to E3/E4.

Baseline at plan intake: `scripts/contracts/check.py` reported **138 operations** (from the initiating review). The new authority releases add Catalogue (2), Inventory native/PlanningInputApp (6), Governance checks (2), Assurance qualifications (4), and retire one overlapping active Inventory 1.2 operation. The first review reached 151 operations; the audit follow-up retired one broken Inventory alias and registered 13 previously undocumented operations, suggesting **163 active operations** in 32 OpenAPI releases, subject to the actual validator output. Validation must establish the real count, not rely on the arithmetic.

## Progress

- [x] (2026-10-11) Reviewed current source contracts, consumers, Laravel routes, Python ASGI routers, Registry, CI and test canaries.
- [ ] **M0 — Verify real validators at exact head.** The remote CI has been queued on a series of changes, but the full real-validator command sequence has not been observed green. Do not substitute stubs.
- [x] **M1 — Implemented, unverified.** Added `catalogue-internal-v1`, `inventory-native-input-v1.3`, `governance-service-checks-v1`, `assurance-qualification-v1`; registered both release and consumers. Historical 1.2 native release remains a file but is no longer active. The unversioned Assurance qualification alias was removed from the router and controller, with a negative test.
- [ ] **M2 — Partially implemented.** Governance Inventory collection and native-approval checks now have separate active v1.1 status releases with an independent expected-status canary; their v1 files remain historical. New operations document owner error statuses; Inventory ASGI emits and schema-validates representative 400/401/403/409/413/422/503 and 200 responses under explicit fixtures. Full **per-status producer exercise for every Laravel and Python operation** is still outstanding. Do not claim equality/exhaustiveness until measured against the real app, including framework validation/authorization paths.
- [x] **M3 — Implemented, CI unverified.** Bidirectional deployed Laravel route conformance; Inventory discovery, five current PlanningInputApp paths and all four collection-worker internal endpoints are contract checked. Planning and Lifecycle bootstrap routes now fail closed for unknown scoped operations using complete explicit HTTP-operation manifests independently compared with active OpenAPI documents (including negative-injection canaries). Separate native-effect workers still retain their separate bounded contracts; full CI completion is pending.
- [x] **M4 — Implemented, CI unverified.** Strict canonical lowercase UUID patterns apply to current authority releases, with Inventory's verified version-4 URL pin and separately canonical legacy v4 payload maintained. The historical UUID allowlist compatibility implementation and SHA-object comparison defect were removed; the duplicated embedded migration-v4 response was collapsed to one reusable component, pinned against canonical producer and Planning installed schema.
- [x] **M5 — Implemented, unverified.** Added `contracts/schemas/common/error-v1.json`, shared error-body lint for new owner operations, and `docs/contracts/adr-service-authority-errors-idempotency-2026-10-11.md` explaining emitted Laravel and Python envelopes and per-command retry rules.
- [x] **M6 — Implemented, unverified.** Removed the unused installed `catalogue-current-v1.json` copy; documented that foundation-event.json files are installed aliases of versioned `catalogue-foundation-recorded-v1`, not independent publications. Kept published bundles immutable.
- [x] (2026-10-11) Updated `next_work.md` first, then appended the contract history in `contracts/README.md` and `docs/implementation/capability-runtime-assurance-ledger.md`.
- [x] (2026-10-11) **Post-audit implementation.** Declared real delegated authority headers and Governance approval 409, retired broken Inventory UUID/int legacy read, published four worker collection operations with producer probes, generated canonical success-schema projections, and de-duplicated Inventory v4 envelope. Fixed composed Planning readiness and placement dispatch and covered previously undeclared Planning/Lifecycle internal routes. Retired unused P00 compatibility workflow/fixtures/code. Runtime route allowlists prevent unregistered scoped operations. Full HTTP status branch proof and CI green remain outstanding.
- [ ] Record exact-head green CI run URLs and revise statuses to **Verified** only after all acceptance checks succeed.

## Surprises & Discoveries

1. `scripts/contracts/check.py` initially verified declared operations without rejecting undocumented deployed paths; Assurance alone had a finite legacy exception list. All three Laravel owners now reject extra `/v1/` or `/internal/` routes.
2. Audit confirmed that Inventory's internal `planning-inputs` alias always attempted `int(endpoint_uuid)` and failed with 503 after authority checks. The dead runtime alias and its contract were retired; the supported five read routes remain, with a 404 negative check.
3. Native-effect commands deliberately omit `Idempotency-Key`. Their signed, bound native grant and operation journal — not generic transport retries — own exactly-once native admission.
4. Laravel route definitions use prefixes, closures, defaults and loops. Always use `php artisan route:list --json` rather than trying to parse `routes/api.php`.
5. The previous documentation specified an *aspirational* `application/problem+json` error envelope even though actual Python and Laravel services return `application/json` with `error` and/or framework `message` bodies.
6. `inventory-native-input-v1.2` did not exist on `main` at intake, yet v1.3 was still released separately. Keeping both simultaneously registered as *active* created duplicate owner routes; the v1.2 registry entry was removed, its published file retained.
7. Catalogue's Planning revision selector is a UUID; Inventory's migration source revision is a positive integer. A shared param-constructor initially obscured that distinction; v1 now specifies it correctly.

## Decision Log

- **Inventory input alias:** Remove the unqualified internal Planning-input path with an endpoint UUID passed to an integer native reader. No compatibility adapter or replacement alias is provided.
- **P00 compatibility:** Delete obsolete synthetic client/contract replay code and its no-longer-required workflow; keep cited historical evidence and immutable published artifacts.
- **Assurance alias:** Remove `POST /v1/tenants/{tenant}/planning-qualification` entirely, and remove its fallback controller output downgrade. Keep `planning-qualification-v2` only. This exception was explicitly requested and is the only deliberate endpoint behavior removal.
- **Immutable releases:** Never alter published versions. New 1.3 replaces active Inventory 1.2; historical bundles remain on disk. `planning-inputs-v1/v2` are not currently active owner-boundary releases.
- **Error envelope:** Preserve emitted `{"error":"snake_case_code"}` and Laravel framework `{"message":"..."}` variants. A universal problem+json migration would be a separate version. See ADR.
- **UUID:** Require lowercase hyphenated canonical UUIDs in current owner releases; Inventory retains its native version-4 URL pin. Historical releases are immutable but no legacy policy registry or SHA allowlist runs on modern authority contracts.
- **Idempotency:** No blanket `Idempotency-Key` rule. Record concrete behavior for delegation issuance, upload/finalize/review, continue-transfer and native-effect grants. See ADR.
- **Evidence:** Synthetic tests stay E2; no promotion to E3/E4 or native write is implied by these contracts.

## Context and Orientation

Root: `awalker0878/multi-tenant`, branch `codex/capability-runtime-assurance-audit-fixes`, base `main`. Keep PR #64 draft while checks are incomplete.

- `contracts/README.md`: published wire immutability, active packages and owner coverage documentation.
- `architecture/contract-consumers.json`: **both** `contracts` and `active_releases` must be updated for a new active release.
- `scripts/contracts/check.py`: OpenAPI/schema validation, hard-coded operations, active-registry integrity, shared errors and UUID policy.
- `scripts/contracts/route_conformance.py`: runtime Laravel route comparison, Inventory native source probe, Planning and Lifecycle probes.
- `tests/contracts/test_integrity.py` and `tests/contracts/test_route_conformance.py`: positive and negative checks.
- `.github/workflows/contracts-integrity.yml`: pinned validators, real source/router checks and Laravel route enumeration.
- `services/planning/src/planning/infrastructure/owner_contracts.py`: exact owner-operation to schema bindings.
- Owner routes: `services/governance/routes/api.php`, `services/catalogue/routes/api.php`, `services/assurance/routes/api.php`, `services/inventory/src/inventory/interfaces/planning.py`.

### Change checkpoints

| Commit | Result |
| --- | --- |
| `58a101bd` | Retired Assurance unversioned alias; positive v2 + negative legacy route test; next_work updated |
| `961d4c5c` | New owner OpenAPI releases, shared error schema and registry |
| `665706ce` | Reverse Laravel conformance, Inventory route probes, operation canaries |
| `0b716b75` | UUID rule and exact legacy blob ledger |
| `1acf83c0` | Error ADR/lint, docs, obsolete Planning v1 consumer removal |
| `35030351` | Additional Inventory emitted status probes, version-4 path UUID pattern |
| `608e69f8` | No overlapping active Inventory 1.2, Catalogue revision UUID |
| `151ede8e` | Versioned Governance collection/native approval status responses (v1.1) |
| *latest head* | Record `git rev-parse HEAD` and GitHub checks URL before changing status |

## Plan of Work / Remaining verification

1. Install pinned validators from `scripts/contracts/requirements.txt`: `jsonschema==4.26.0`, `openapi-spec-validator==0.7.2`, `PyYAML==6.0.3`. Use the repository checkout, not stubs.
2. Run all exact-head integrity, route, source and consumer checks below; fix any failures with additive source/contract versions. Do not alter a published bundle, except revising not-yet-published new contracts on this branch before merge.
3. For each newly documented non-2xx status, add real authorized/denied controller/ASGI fixture tests and assert `documented == observed` with independently generated requests. Include Python `Rejected(reason,status)`, Laravel default IdentityDenied(401), HTTP/validation exceptions, and dependency failures. Protect `native_write_authorized:false` throughout.
4. Complete source-independent reverse enumeration for all executable Planning/Lifecycle and Inventory internal worker routes, adding missing active releases as needed. Injection of any `/internal/` route with no active release must fail in CI. Do not rely only on positive known-path probes.
5. Run Laravel `route:list --json` for all three owners, compare, and add an actual temporary Governance `/internal/tenants/{tenant}/x` route as a negative test. Remove the temporary route and confirm passing.
6. Verify operation count exceeds 138, record exact-head CI run and output, then amend Progress and Outcomes. Keep PR #64 draft until broader capability assurance gates independently pass.

## Concrete Steps

From repository root:

```bash
python -m pip install -r scripts/contracts/requirements.txt
python scripts/contracts/generate_readiness.py
python scripts/contracts/build.py --check
python scripts/contracts/check.py
python -m unittest discover -s tests/contracts -p 'test_integrity.py' -v
python -m unittest discover -s tests/contracts -p 'test_route_conformance.py' -v

# Install actual app dependencies as in contracts-integrity.yml when needed.
PYTHONPATH=services/inventory/src:services/planning/src:services/lifecycle/src python scripts/contracts/route_conformance.py --app inventory
PYTHONPATH=services/inventory/src:services/planning/src:services/lifecycle/src python scripts/contracts/route_conformance.py --app planning-migration
PYTHONPATH=services/inventory/src:services/planning/src:services/lifecycle/src python scripts/contracts/route_conformance.py --app lifecycle-native
PYTHONPATH=services/inventory/src:services/planning/src:services/lifecycle/src python scripts/contracts/route_conformance.py --app planning-immutable
PYTHONPATH=services/inventory/src:services/planning/src:services/lifecycle/src python scripts/contracts/route_conformance.py --app planning-lifecycle

# Run for each owner after Composer dependencies are installed:
for service in governance catalogue assurance; do
  php "services/$service/artisan" route:list --json > "/tmp/$service-routes.json"
  python scripts/contracts/route_conformance.py --app "$service" --routes "/tmp/$service-routes.json"
done

git rev-parse HEAD
git diff --stat main...HEAD
```

To reproduce the negative Laravel gate without changing runtime behavior permanently, in a throwaway checkout temporarily add a `GET /internal/tenants/{tenant}/x` route to Governance, generate the route list, run conformance (it **must fail naming the undocumented route**), revert the dummy route, and run conformance again (must pass).

## Validation and Acceptance

- All concrete commands exit 0 with real pinned dependencies, not stubs.
- `check.py` reports **more than 138 operations**.
- Every active owner endpoint is present in the concrete runtime; no uncovered `/v1/` or `/internal/` endpoints exist, including Python routers and Inventory worker-only handlers.
- A dummy undocumented Governance route fails route conformance, without adding an exception.
- No historical published OpenAPI/schema bytes change. Superseded versions are retained in the repository, not duplicated as active releases.
- Every documented non-2xx status is independently exercised against its actual producer; every emitted status appears in the active release.
- Source operation fixtures validate against exact installed Planning, Inventory and Lifecycle consumer contracts. Negative assertions reject native write authority and unauthorized evidence promotion.
- Exact-head passing CI run URL and `git rev-parse HEAD` are saved in the ledger before promotion from **Implemented, unverified** to **Verified**.

## Idempotence and Recovery

All contract additions are additive; only the explicitly approved unversioned Assurance alias and unused consumer copy were removed. New release assembly is performed by `build.py --write` only for a version that has not been published. Rollback the new release entries and files together; do not alter legacy published version bytes. No schema migrations, data migrations, native grants or native effects are introduced by this work.

## Interfaces and Dependencies

Python 3.12, PHP 8.5 and the service Composer lockfiles as specified in `.github/workflows/contracts-integrity.yml`. Python contract validator versions are pinned in `scripts/contracts/requirements.txt`. The APIs still rely on their existing credentials, subject/current-delegation authority and source-native input checks. The new `common/error-v1` schema is a wire description, not a shared runtime exception handler.

## Outcomes & Retrospective

The engineering branch now has the missing owner release documents, an explicit retirement of the unversioned Assurance alias, active-release uniqueness protection, stricter two-direction Laravel coverage, Inventory route/status probes, shared error conventions, a historical UUID pin, and concrete retry semantics. The important remaining gaps are **exact-head test evidence, exhaustive real-producer response-status coverage, and full Python reverse route enumeration**, including worker-only internal routes. No native execution authority, E3 evidence or E4 acceptance has been created.

### CI discovery: embedded Catalogue schema reference (2026-10-11)

The earlier head `1acf83c0` had all three Laravel reverse-route jobs pass, but `scripts/contracts/check.py` failed before tests at `Invalid catalogue-internal-v1.json local $ref: #/$defs/Intent`. The producer's standalone `catalogue-current-v2` schema was embedded in OpenAPI with an absolute-to-schema-root reference. The new bundle now relocates that reference to `#/components/schemas/CurrentPlanningIntent/$defs/Intent`, and `check_implemented_api_contracts` asserts exact projection equality after relocation. The historical canonical schema remains unchanged. **The latest amended head still needs a fresh green run.**

### Negative regression canary for embedded local references

The contract-integrity suite now includes a negative fixture which changes the sole Catalogue current-intent projection reference back to the invalid `#/$defs/Intent` root and asserts `local_refs` rejects it. Keep this test alongside the exact canonical projection equality check. No previously published producer schema was edited.
