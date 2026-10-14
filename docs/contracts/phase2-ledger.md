# Phase 2 implementation ledger

Branch: `codex/capability-runtime-assurance-audit-fixes`. Requested scope:
runtime contract conformance and security assurance. Main is not authorized.

## Determination — 2026-10-14

**Phase 2 FAIL / externally blocked at Phase 2.0.** Phase 1 is not complete.
The independently reproduced handoff blocker is the missing deployment-owned
Planning collection registry and its referenced manifest. The execution
instruction requires resolving Phase 1 before starting Phase 2 implementation.
No completion or production qualification is claimed.

Baseline checkout: `015feda8a0864bb87f6ca634160645eb16fb5955`.
Actual review base: `88f77d5b4dd5e4da8ae3e96be09ab8779b9c4843`.
No repository `AGENTS.md` was found. The checkout was initially clean.

## Independent handoff audit

- Ran the canonical builders, authority generation, contract validator,
  dependency/report freshness checks, installed loader registration checks,
  runtime build-binding coverage and Git-backed publication/retirement checks.
- Found 75 registered active releases, 166 HTTP operations, 47 canonical
  dependency edges, 83 consumer relationships and 35 installed copies.
  Nine deployable components are represented by the packaging matrix.
- Re-derived the release inventory: 74 releases have source-scope evidence;
  the collection manifest remains `active but requiring correction`.
- Read the actual protected-file loader and its production bootstrap wiring.
  `PlanningApp` installs `migration_collection_manifest.binding` into
  `MigrationSupport`; this is an actual runtime dependency, not a documentation
  reference. The loader selects an independently enrolled release, protected
  registry path, manifest path and manifest digest.
- `PLANNING_MIGRATION_COLLECTION_REGISTRY_FILE` is absent in this execution
  environment. A direct invocation of the actual loader returns `None`.
  Repository searches found its runtime loader and documentation, but no
  provisioned deployment registry or independent enrollment/provenance evidence.
- Did not fabricate a registry, enroll a fixture, delete the active dependency,
  replace the protected loader or weaken the qualification gate.

## Executed baseline verification

Python 3.12.14; pinned contract requirements; five component environments
prepared with `uv sync --locked --all-groups`. Contract PHP probes used the
available extracted PHP 8.3 CLI with `-n`. This does not establish supported
PHP 8.5.11 Laravel runtime qualification; that remains separate.

| Command / suite | Exit | Result |
| --- | --- | --- |
| `python scripts/contracts/build.py --check` | 0 | Six manifests / ten outputs |
| `python scripts/contracts/generate_authority_releases.py --check` | 0 | Five releases |
| `python scripts/contracts/check.py` | 0 | 30 schemas / 166 HTTP operations |
| `python scripts/contracts/dependency_graph.py --output architecture/contract-dependencies.json --check` | 0 | 47 edges / 83 relationships |
| `python scripts/contracts/runtime_binding_coverage.py` | 0 | Nine components / 166 bindings |
| `python scripts/contracts/installed_usage.py` | 0 | 35 usage records |
| `python scripts/contracts/release_inventory.py --output architecture/contract-release-inventory.json --check` | 0 | Report current; one unresolved release |
| `python scripts/p01/contracts/compatibility.py --base 88f77d5b4dd5e4da8ae3e96be09ab8779b9c4843` | 0 | No surviving published release rewritten |
| `python -m unittest discover -s tests/contracts -v` | 0 | 210 passed |
| `python -m unittest discover -s scripts/p01/contracts -p 'test_*.py' -v` | 0 | 16 passed |
| Inventory `uv run --locked --all-groups pytest -q -ra` | 0 | 214 passed / 47 skipped |
| Planning, same command | 0 | 586 passed / 20 skipped |
| Lifecycle, same command | 0 | 375 passed / 86 skipped |
| Inventory worker, same command | 0 | 146 passed / zero skipped |
| Lifecycle worker, same command | 0 | 725 passed / 27 skipped |
| `python scripts/contracts/route_conformance.py --app python-composed` | 0 | 35 router operations |
| P03/P04/P06/P09 current generators and capability generation `--check`; readiness generator default check | 0 | Generated outputs current |
| `python scripts/p09/check_contract.py` | 1 | Actual response/schema mismatch reproduced |

Five Python suites: **2,046 passed / 180 skipped**. The skipped cases require
PostgreSQL qualification environments; they are not integration evidence.
Exact executed argv, JUnit counts and diagnostic log digests are retained in
[the preflight evidence](../../verification/contracts/phase2-preflight.json).
Contract commands use the five `src` directories on `PYTHONPATH` and the PHP
wrapper plus installed formatter on `PATH`.

Three initial command errors were resolved: the publication checker requires a
literal existing SHA rather than `origin/main`, and P09's actual generator is
`generate_contract.py`, not `generate_contracts.py`. The readiness generator
checks by default and does not accept `--check`. None of these initial errors
is reported as a passing check.

## Independently retrieved CI evidence

[CI run 38587471842](https://github.com/awalker0878/multi-tenant/actions/runs/38587471842)
belongs to the baseline branch head. Its actual tested PR merge revision is
`c8dfa97f7120c3fb8dd280651ae7c55f9003d391`; it is not a new-head result.

- CI / Contracts and all three live Laravel route jobs pass.
- All nine image/wheel builder jobs and their aggregation pass. Aggregation
  verifies nine images, five wheels, 35 installed release bindings and 155
  release/image relationships. These are built artifact checks, not deployed
  provider or externally mounted manifest qualification.
- Downloaded and inspected the actual assurance report artifact, independently
  compared its canonical and operation digests to the local baseline, and read
  its generating job logs. **0/166 HTTP operations** and **4/75 releases** are
  qualified by the existing CI model; 71 releases remain unqualified.
- The report has 358/909 required claims. HTTP claims include 161 route proofs,
  161 credential denials, 14 producer proofs and nine consumer proofs. No HTTP
  operation has authenticated tenant-isolation evidence in this report.
- All five AsyncAPI releases remain unqualified. One has a consumer claim;
  none has complete event producer/consumer qualification. No broker recovery
  or native E3/E4 qualification is newly established by this preflight.
- CI / Native contracts, service quality, E2 authority formatting, Contract
  assurance and CI / Required fail. These repository failures are recorded as
  additional unfinished work, not reclassified as external blockers.

## Findings and decisions

1. **External entry blocker:** deployment-owned Planning collection enrollment,
   manifest identity and provenance are unavailable. Preserve the boundary and
   stop Phase 2 implementation at the mandated Phase 1 prerequisite.
2. **Reproduced repository defect:** P09 validates actual `MigrationSupport.read`
   output against Planning migration v1.6 and rejects route fields
   `api_compatibility`, `expires_at`, and `readiness`. This defect remains open.
   Correct it after the handoff closes; do not weaken the closed schema or
   rewrite surviving published releases to hide accidental behavior.
3. Existing route, unit and package success does not qualify complete runtime
   security, individual consumers, event delivery or native effects.
4. No runtime security defect or contract mismatch was fixed in this execution.
   The changes are evidence/ledger documentation only.

## Exact missing dependency and resume condition

The deployment owner must provide the actual protected file named by
`PLANNING_MIGRATION_COLLECTION_REGISTRY_FILE`, its referenced `manifest_file`,
and independent release enrollment and provenance/commitment evidence. The
registry must contain `schema_version`, `manifest_file`, `manifest_sha256` and
`releases`. Both paths must be absolute, regular, non-symlinked protected files
accepted by the actual loader; manifest digest and enrolled release identities
must be independently reconciled to active canonical definitions. Fixture
success alone cannot establish deployment identity or authorized enrollment.

Once that evidence is available, repeat Phase 2.0, close the Phase 1 ledger,
then implement the remaining workstreams and execute real PostgreSQL, TLS
broker, Temporal, native provider/custody and supported Laravel/Console tests.
No required Phase 2 acceptance item is marked complete by this preflight.
The eight requested full-assurance deliverables remain incomplete; this ledger
and its machine-readable snapshot are the blocked baseline, not substitutes.

## Final re-audit and checkpoint

Rechecked the actual loader wiring, absent provisioned input, current canonical
digests, installed registry, executed test verdicts and downloaded CI evidence.
Phase 1 handoff remains FAIL, so Phase 2 remains FAIL. All observed repository
defects and absent qualification claims remain explicit. Only the preflight
evidence and this ledger are committed on the working branch.


## Current remediation — 2026-10-14

The current user instruction authorizes independent remediation while deployment
inputs remain unavailable. The earlier Phase 2.0 stop condition no longer governs
this work. Initial remote HEAD was `37312b3c48538fc48f04f6abf59665c2c34b5c15`;
first durable remediation checkpoint is `c90394c2df162a5f5cc38667636b2a20751e4ca0`.
Main remains unauthorized. Overall qualification remains **INCOMPLETE**.

### Confirmed defects and resolutions

| Finding | Severity | Root cause and current correction |
| --- | --- | --- |
| P09 producer/Console mismatch | High | The old response omitted route expiry, API compatibility and route readiness from a closed schema. Publish `planning-migration-v2` with explicit required fields and closed readiness/compatibility schemas. Migrate the sole registered Console consumer, generators, source manifest and installed copy. The major release satisfies the unchanged strict publication policy, including Error v2 and scoped idempotency. No surviving published canonical bytes change. |
| Malformed collection enrollment | High | The actual protected-file loader accepted boolean schema versions and silently filtered unknown scopes, missing owner fields, invalid IDs and extra platforms. Reject these inputs and require every source/target/owner attribute set. Fifteen real file-loader controls pass; original implementation fails six negative controls. Temporary enrollment is not deployed identity or provenance. |
| Authentication counted as authorization | High | Missing-token denials could satisfy the report's authorization category. Separate authentication from current effective authority. Authorization receipts require authenticated current-authority denial and absence of unauthorized disclosure/mutation. Original proof admission accepts a forged missing-token authorization receipt; the corrected gate rejects it. |
| Required source quality | Medium | Fixed import, formatting and strict typing defects across five Python and four Laravel components. Add pinned Lifecycle development stubs. No check or assertion is disabled. |
| Relevant integration omitted | High | The existing PostgreSQL/TLS broker integration suite was on demand and absent from PR admission. Reuse it for relevant contract/runtime changes and require its outcome. Separate reusable concurrency groups by suite so integration cannot cancel artifact verification. |
| Transient package download | External failure | First checkpoint's Assurance image failed on a GitHub archive HTTP/2 500. Extend the existing bounded network retry recognition to HTTP 50x; source failures remain non-retryable. No absent artifact earns a passing attestation. |

The first checkpoint's narrower support projection was rejected by the existing
API-compatibility acceptance test. The final correction preserves the richer
public behavior in a deliberately versioned release. The cross-service wire
regression reads the canonical test input in isolated Planning tests; independent
installed-copy and Console adapter tests cover the consuming resource.

### Query replay and release behavior

- Planning requires an Idempotency-Key after authenticating current workload and
  actor authority. Mutation commands use the existing immutable command ledger.
- Query receipts store only a request fingerprint and a read-only marker in that
  same Planning-owned ledger. They cannot replay returned data or grant authority.
  Every retry re-authenticates, re-authorizes and recomputes current readiness.
- Changed payload/operation reuse and expired keys fail closed. The new release's
  seven-day lifetime is applied explicitly to its migration commands; other
  active APIs retain their own idempotency contracts.
- Console sends query keys, requires mutation keys, validates the installed v2
  response and Error v2 wire, and rejects incompatible error envelopes.

### Current verification and limits

The current canonical tree contains 75 releases and 166 HTTP operations. The
replacement adds one real Error v2 dependency: 48 canonical edges, 83 registered
consumer relationships, 35 installed copies and nine deployable components.
The previous release/source/copy is removed after all registered call sites and
projections migrate. No additional release has a proven safe retirement.

Local Planning verification: 603 passed / 22 PostgreSQL-dependent cases skipped.
New query-key concurrency, scope, changed-payload and expiry tests require real
PostgreSQL and are included in required CI. Skips are not integration evidence.

PostgreSQL 16.15 acquisition and an actual local integration fixture were attempted;
the sandbox rejects `os.chown(..., 65534, 65534)` with `OSError: [Errno 22]`.
Do not rewrite the fixture or mock the database to report qualification. CI's
supported unprivileged PostgreSQL environment executes those requirements.
PHP formatting uses extracted PHP 8.3/Pint; supported PHP 8.5.11 runtime, real
broker/persistence and browser evidence must be independently retrieved from CI.

First checkpoint CI `38595120026` tested merge revision
`bfe7460d95f12f37faf2763baf3c8861869c470e`. Four Python components, all four Laravel
quality jobs, all three live Laravel route jobs, E2 authority transactions and
eight of nine built-image jobs pass. Planning and native failures identified the
response and isolated-test issues corrected above; the missing Assurance image
prevents artifact aggregation. Complete operation qualification remains red.
These results do not qualify the replacement release's final commit.

The missing deployment-owned collection registry and enrolled manifest provenance
remain a Phase 1 blocker. Installed native provider/custody E3/E4 evidence remains
unavailable. Complete authenticated per-operation/consumer and event recovery
qualification must still be established from applicable executed integration
results. Do not describe this ledger, a source build or E2 fixtures as completion.

### Required integration follow-up

Checkpoint `4058a28bb113bdfa53a05919823ac48c75bb6ac8`, CI run `38642332673`,
tested merge revision `0c9a7b2b772fc75c35a1b99b84c37066a5c17cea`.
All five Python quality jobs, three other Laravel quality jobs, live Laravel
route checks, E2 authority transactions, and the five real PostgreSQL/broker
integration jobs pass. Planning's new database tests execute without local skips.
These bounded results do not qualify every HTTP operation or native authority.

| Finding | Boundary | Reproduction and correction |
| --- | --- | --- |
| Invalid PostgreSQL migration command (high) | Governance production provisioning | All P03–P06 live journeys fail with `psql: invalid command \\`. Migration 014 contains two leading backslashes; correct it to the actual psql `\set`. Feature fixtures strip meta-commands and therefore did not expose the production defect. Required live journeys execute the actual migration files. |
| Retired producer-copy reference (medium) | P02 support qualification | All three P02 journeys fail opening the removed Governance OpenAPI copy. Remove the obsolete packaged-copy assertion; the preceding real PostgreSQL `SupportContractTest` already validates actual owner outputs against the canonical contract. No unused runtime copy is recreated. |
| Obsolete migration error specimen (medium) | Console installed consumer | `MigrationFleetTest` expects old `{error}` data to pass v2 validation. Use the exact Error v2 envelope for the positive denial and retain the old envelope as an explicit incompatible-wire rejection. The new Error v2 test passed on supported PHP. |
| Stale composition specimen (medium) | Native E2 compiler/resolver | Native qualification fails at command 32 because the synthetic owner configuration lacks Catalogue and the current workload-readiness receipt. Update the existing E2 check to exercise current readiness and independent Catalogue membership. All 30 combinations and 90 missing/stale/foreign controls pass locally. This is not E3/E4 evidence. |
| Transient pinned APK 404 | Catalogue image acquisition | CI reports 404 for pinned zlib. Independent retrieval returns 200, 56,195 bytes and SHA256 `b636306cbf8a0c15493b38de608ba11605fd8f11ade631f5ece6f7fdf5a1e09e`, exactly matching the lock. Extend the existing three-attempt network retry narrowly to official APK 404 responses; all signature, byte-count and digest checks remain mandatory. |

The integration and aggregate required gates remain failed until the corrected
branch is executed again. The complete qualification gate remains red for
missing authenticated authority and other operation-specific evidence. No test
fixture, successful build or missing receipt is promoted to runtime assurance.

The next run, `38644129101` at `e0fd55d35b1a6badb28267f062f6d4a2e64ddf02`,
passed the corrected SQL bootstrap and exposed two additional executable defects:
P03–P06 harnesses sent UUID issuance keys rejected by Governance v2's unchanged
lowercase-hex schema (422), and P02 migration replay found that migration 014's
table/index creation was not idempotent. Harness issuance now uses a fresh
cryptographic 64-character hex key; production delegation callers already send
valid hex keys. Migration 014 uses `IF NOT EXISTS`, retaining existing data and
reapplying current owner privileges. The actual replay journey is the regression
entry point, and the original implementation fails it. The source evidence
inventory also requires regeneration after modifying its bound P02 harness;
the strict stale-inventory rejection is preserved and the report is regenerated.

Run `38644920007` tested `43f4d94be999d7ff2afe9d87fd302bc66d84b3f8` as merge
revision `9203a7d427543162645aaf266c2d4050c3a1d066`. P02 passes in all three
browsers, including real owner relay/Console inbox, PostgreSQL TLS, bootstrap and
recovery, and actual migration replay. All nine images, five wheels and complete
release-binding aggregation pass; downloaded artifact `11932821183` binds exact
canonical digests, source revision, CI attempt and image identities. These are
disposable packaged artifacts, not operated deployments.

| Finding | Severity | Root cause and remediation |
| --- | --- | --- |
| Root version-discovery witness rejected | High | P04 stops at configuration page 7. Worker legitimately records `GET /`; Inventory's witness pattern requires another character after `/`. Permit that valid root path within the existing 404-character bound while retaining GET-only and CR/LF rejection. Add a real PostgreSQL regression proving root witness commit and no page mutation for malformed, non-GET or oversized witnesses. Required CI must execute it; local database absence remains a skip. |
| Nested API expiry can exceed effective authority | High | The exact installed Lifecycle readiness consumer accepts an expired nested API case after the whole receipt digest is recomputed, despite a future aggregate expiry. Require each eligible/accepted-omission case's integer expiry to be current and bound the aggregate lifetime. Deliberately restoring the original runtime makes four new controls fail; the corrected installed consumer passes all five. Canonical bytes are unchanged. |
| Stale P05/P06 policy fixture | Medium | The live E2 snapshot constructor raises `KeyError: network_flow_contexts`. Rebind current explicit network contexts and the existing reviewed recovery fixture to the simulated intent. This only repairs the bounded E2 campaign; fixture signatures or successes do not establish real provider, reviewer or receiving identity. |
| P09 route proof mistaken for workload admission | Medium | Required native command 20 assumes synthetic route evidence can pass `MigrationSupport.require` without collection/workload enrollment. Assert the actual uncommissioned denial and challenge route revocation/expiry separately. Preserve the real Lifecycle resolver's positive composition check using the existing explicit E2 readiness specimen, with current Catalogue membership. The directional campaign passes 270 scenarios, 3,348 stage boundaries and 1,800 rejection controls locally; no native authority is qualified. |

The existing `route_conformance.py` now records actual received HTTP traffic in
the P02–P06 live journeys, validates exact active response status/schema and valid
request parameters/body, and preserves operation/source/CI and canonical byte
digests. Installed source-copy equality does not assert installed image identity.
Returned data and credentials are not retained. Five admission-control regressions
reject unknown methods/statuses, invalid requests/payloads and copy drift; denied
traffic is never credited as positive conformance or complete security assurance.
The existing full assurance gate is not replaced or relaxed.
