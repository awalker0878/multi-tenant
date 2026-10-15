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

The [existing machine-readable snapshot](../../verification/contracts/phase2-preflight.json)
now records the independently reconstructed initial Git baseline and current
inventory, all 166 HTTP/security rows, 83 consumer relationships, five event
releases, 30 native method/mode entries, installed-copy/source bindings, actual
retrieved CI/artifact identities, findings and current acceptance gaps. Canonical
schema pointers avoid duplicating contract definitions. It is an ongoing evidence
snapshot, not a qualification receipt or a completion claim.

Run `38647622315` reaches real recovered federated sign-in. The new live probe
rejects `/identity/session` because the surviving bootstrap-only schema does not
permit the legitimate `FederatedIdentity` returned by Governance. This is a
confirmed producer/contract mismatch, not a validator defect. Preserve federated
functionality; publish an intentional new release and enforce its exact installed
Console decoder. P05/P06 also reach concurrent assessment and expose a remaining
synthetic-fixture eligibility mismatch. Both findings remain open. No repository
defect is relabelled as an external blocker.


### Resumed remediation — 2026-10-15

Recovered the unfinished working tree at remote `609c161102418b9f3492f1124fbf28fa51307d0f`.
The latest independently retrieved CI run is `38647622315`, attempt 1; its tested
merge revision is `d95e85b565b5a93e9485ff464758aa3265162d7f`.

- Publish Governance local identity v2 intentionally, preserving both actual
  bootstrap and federated identity variants with exact permissions, session
  expiry, closed request bodies, Error v2 and command idempotency. Retire v1
  after the sole Console consumer migrates; add an actual packaged Console
  decoder. Supported PHP runtime and live database evidence remain CI gates.
- Credential issuance records only keyed request/command digests and never
  replays raw credentials. Owner locks serialize commands; failed-password
  counters still commit independently of idempotency conflicts. Logout retains
  its idempotent revocation behavior. Preserve Retry-After on throttling.
- Console rejects incompatible success/error envelopes, invalid identity or
  permissions and expired returned credentials. Retain session expiry in the
  server-held session, and preserve the browser session on an incompatible
  upstream error. Identity recovery now validates the current active schema
  in addition to exact reconciled actor equality.
- Independently reproduced Assurance rejecting the Planning recovery fixture
  with `native_recovery_readback_invalid`. The specimen used a generic strategy
  string where the actual signed decoder requires a canonical method identity,
  mode, scope and readback digest. Bind the existing explicit synthetic cold
  export specimen to `VM_COLD_EXPORT` and these required fields. The regression
  invokes the real PHP decoder and rejects re-signed missing-field and generic
  method controls. No runtime validator or native evidence requirement changes.
- P08 wheel staging polluted the source tree before P09's architecture gate.
  Direct wheel build intermediates into the qualification output directory;
  retain the unchanged architecture boundary checks. An isolated wheel build
  succeeds and the actual architecture validator passes on the source tree.

Current independently derived inventory: 75 releases, 166 HTTP operations,
49 canonical dependency edges, 83 consumer relationships, 36 installed copies,
five AsyncAPI releases and nine deployable components. The two additional
edges since the initial baseline are intentional Error v2 dependencies.

Local Planning: **603 passed / 22 PostgreSQL cases skipped**. Strict publication
quality passes for eight releases introduced since the Git-derived policy
adoption commit `bb0adb3c08609f2ed674ae0c44efe5ef5ef28e1c`, as CI requires.
The earlier unadapted full-main invocation correctly rejected a release that
predates that policy; it is not reported as a passing check. PHP syntax/Pint
checks use the extracted 8.3 toolchain and do not qualify supported PHP 8.5.11.

Full assurance remains **FAIL / INCOMPLETE**. The last actual minimum report
contains 358/1,073 claims, 0/166 qualified HTTP operations and 4/75 qualified
releases. Repository changes still need a new CI run. External protected
Planning enrollment and real provider/custody/receiving E3/E4 remain unavailable.
No merge to main, native qualification or production admission is claimed.

Final local source regressions: **217 passed**, plus **16 publication/retirement controls passed**. The original missing-field/generic-method specimen fails the new real signed-decoder controls. These checks do not replace supported runtime integration.

### Qualification wire and evidence admission follow-up

The supported run for `a3b5e8ee` is `38738058752`, tested merge revision
`015a7fdccb2a39438ddbc77446d0086a7f877e3a`. Its native-contract E2 job now passes,
including P08/P09 source isolation. All nine image builds and their release
binding aggregation pass for that exact earlier tree. They do not qualify the
subsequent replacement contracts or a deployed installation.

The live P05/P06 assessment exposed another confirmed wire defect: the actual
Assurance resolver returns its signed `method_modes`, while the closed installed
qualification schema omits it. Dropping the field would invalidate the reviewed
record digest. Publish `qualification-v3` and Assurance qualification API v2;
require the exact method/mode matrix for qualified records while preserving
explicit unknown results. Migrate the sole Planning consumer and remove the two
superseded canonical files and old installed copy. Request scopes derive from
the same new schema; malformed IDs, tuple objects, artifacts and actions cannot
be echoed into an invalid successful response. Publication epochs remain JSON
integers. No native verification predicate is relaxed.

The new API preserves strict new-release requirements: Error v2 and scoped
Idempotency-Key receipts. Assurance stores digests only, recomputes current
qualification on every query, and rechecks delegated actor authority before
retaining query identity. Existing publication command/epoch deduplication still
owns the mutation result. Add the owner-only migration and real PostgreSQL
conflict/isolation/privilege regression. Planning generates a fresh key for each
current read, validates success through its installed v3 schema, and validates
denials through an actual installed Error v2 decoder before accepting status
semantics. Unsafe or incompatible errors become unavailable authority.

Independently reproduced and fixed two false-pass paths in the assurance model:

- Authenticated cross-tenant status alone admitted evidence reporting disclosure
  and mutation. Require explicit absence of both effects and a nonempty foreign
  target.
- An unnamed consumer proof could qualify all declared callers. Attribute every
  executed consumer by component, require every registered caller independently,
  and report missing consumer boundaries. Source-only definitions require an
  explicitly identified owner-local validator; no remote consumer is invented.
  Existing executable probes now name only the consumers they actually execute.

Supported PHP also identified two test-specimen defects. Governance admission
asserted the retired Error v1 shape; require Error v2's exact key count, code,
retryability and UUID correlation instead. Console's repeated HTTP fake callbacks
kept returning the initial success, so isolate each malformed identity in its
own test. The decoder assertions remain strict. A broker startup failed with a
cookie-permission diagnostic; a targeted retry of that job passed. No production
permission or broker health requirement was weakened.

Current source inventory: **75 releases, 166 HTTP operations, 49 dependency edges,
83 consumer relationships and 37 installed copies**. Assurance's Error v1
relationship disappears after its API replacement; Error v2 now has a real
installed Planning consumer. The protected external Planning enrollment and real
provider/custody/receiving evidence remain unavailable. Full assurance is still
**FAIL / INCOMPLETE**, including unresolved per-operation and event evidence.

Checkpoint verification: **221 local contract tests passed**, **603 Planning tests passed / 22 infrastructure skips**, and strict types passed for 109 source files. All ten releases introduced since policy adoption pass strict quality. Replacements preserve surviving canonical bytes. Current supported PHP, PostgreSQL/broker/browser and new artifact identities must be verified in the next CI run.

Run `38742662220` (`6c26a54b`, tested merge `a340851aeeb3d8a829c55990105c8434fea4b2ca`)
reproduced a least-privilege defect in the new query receipt: PostgreSQL requires
UPDATE privilege for SELECT FOR UPDATE. Remove that unnecessary read lock. The
unique INSERT ON CONFLICT already serializes simultaneous claims, current receipt
bytes cannot be updated, and retention deletes only sufficiently old expired
rows. Keep the actual runtime UPDATE-denial regression and existing grants.
The P05 signature check also ran in unconfigured system Python; invoke it through
the already locked Planning environment rather than skipping schema validation.
These corrections still require current PostgreSQL/live verification.

The same run passes all four supported Laravel quality suites. P02 reaches 106
live checks, then its helper incorrectly applies local identity's new Error v2
to an unchanged OIDC operation that still publishes Error v1. Preserve both
active APIs: the existing mandatory HTTP conformance observer validates errors
against each exact active operation/status; retain the extra explicit success
and custom-identity checks. No OIDC canonical or runtime error is rewritten.

Targeted follow-up checks pass: four signed qualification/scope controls in the
actual locked Planning environment, 17 route/wire controls (including distinct
active OIDC/local error contracts), and PHP formatting/syntax. The original
SELECT FOR UPDATE implementation fails the current PostgreSQL authority test;
its corrected transaction must be rerun with unchanged restricted grants.

### Verified CI checkpoint and remaining live defects

Run [38744215057](https://github.com/awalker0878/multi-tenant/actions/runs/38744215057),
attempt 1, tests branch head `10b6aea9a8af7ebf18870c0da14ea5830cc940c7`
through merge revision `f6c84e70f9a88ffe7121451b24dc2663b2f90261`.

- The restricted PostgreSQL authority transaction and epoch tests pass with the
  existing grants. P05 plan/reservation and P06 journal/independent simulation
  PostgreSQL jobs also pass.
- All four supported Laravel quality suites, five Python service/worker quality
  jobs, architecture, security, contracts and three live Laravel route checks
  pass. All nine image-binding builds and the exact-source aggregation pass.
- P02, P03 and P04 live journeys pass on Chromium, Firefox and WebKit. P05 passes
  Firefox and WebKit; Chromium fails
  `two-authorized-destinations-explain-positive-and-blocked`. This intermittent
  assessment failure remains a repository-owned gap; its finding payload must
  be inspected before choosing a correction.
- P06 Chromium and WebKit reach a later `KeyError: 'scope'`. Source inspection
  confirms `scripts/p06/live_execution.py` copies a signed registry bundle and
  accesses `q['scope']`, although the current bundle holds the record under
  `q['record']`. Repairing this requires issuing and enrolling a new signed,
  scope-bound fixture for each campaign and updating its current runtime proof;
  a nested-key substitution alone would not repair the old unsigned fixture
  protocol. P06 Firefox stops at the earlier intermittent P05 assessment check.
  No full P06 live journey passes for this tree.
- The native-contract job was still running when this checkpoint was inspected;
  its result is not inferred from earlier trees.
- The current minimum assurance gate fails closed: **352/1,073 verified claims,
  0/166 qualified HTTP operations, 4/75 qualified canonical releases**, and
  **204 missing boundaries**. These E2 measurements do not establish native,
  deployment, security or release qualification.

The local execution service subsequently reports `environment_offline:
Environment is not connected`. GitHub source/log reads remain available, but
local editing, artifact extraction and executable regression checks cannot run.
The above source diagnosis is recorded without claiming a tested repair.
Repository-owned P05/P06 defects and assurance coverage remain open, separately
from the unavailable protected Planning enrollment and real provider/custody/
receiving evidence. No merge to main or production admission is authorized by
these results.


### 2026-10-15 resumed executable repairs

The workspace is executable again. The latest completed baseline run is
[38745811357](https://github.com/awalker0878/multi-tenant/actions/runs/38745811357)
on head `f57f4bf5c5012750ce5813c8928bf7a51d9dec32`. Native contracts, service
quality, active contracts, Laravel router/denial probes and PostgreSQL authority
transactions pass. Live P05/P06 fail; one Governance image download fails on a
pinned upstream Alpine APK 404, and P02 WebKit stops at broker readiness. Those
failures have not been relabelled as successful checks.

Current corrections:

- Planning retries an Inventory read once when independently verified Assurance
  identifies a different current runtime proof. The native/installed identity
  must remain equal and exact snapshot/proof equality is still mandatory.
- Known observation freshness fields no longer change immutable plan input
  semantics. Every current freshness check still executes, while scope, policy,
  sequence, readback, native identity and actual recovery event times stay bound.
- Synthetic E2 runtime renewal now covers nested network selections, return
  paths and isolation controls. Concurrent runtime publications are serialized.
- Each P06 campaign generates a new signed, scope-bound dossier and enrolls its
  own observer/reviewer keys and current runtime proof before publishing it.
  Editing signed scope bytes in an existing dossier is no longer attempted.
- P05 retains initial assessment findings before asserting eligibility and waits
  for the current-authority revocation explanation during the browser poll.

Local verification: **222 contract tests pass**; **608 Planning tests pass**,
**22 database tests require CI**; Ruff and strict mypy pass. The signed renewal
regression executes the actual PHP verifier and Planning assessment; negative
regressions preserve holds for expired, continuously mismatched or foreign
proofs and detect semantic recovery/readback changes. Live acceptance awaits
CI on the resulting source revision. Full contract/security/release coverage
and real protected enrollment, native E3 and independent E4 remain open.


### Follow-up diagnosis and producer-evidence ingestion

Run [38780170967](https://github.com/awalker0878/multi-tenant/actions/runs/38780170967)
executes head `2754b992eb96951f59e56203f0451bba0440169b`. Its retained initial
assessment proves the intermittent P05 failure is
`native_fault_hierarchy_unverified`: random ID rebinding changes placement
sorting while the fixture previously assigned hosts by input order. Synthetic
pool/hierarchy construction now uses the same explicit workload ordering, with
a reversed-order regression. No production isolation check is removed.

All three P06 browsers progress beyond the former signed-registry access fault
and hold at `campaign_safety_inputs_missing`. Replaying retained live inputs
through the real PHP verifier identifies a stale newly signed campaign specimen:
its recovery samples still use P05 startup time, exceeding the unchanged
30-second dossier observation bound. New enrollment now creates observations
and signatures at one current enrollment time. The regression rejects a
five-minute-old specimen and accepts freshly scope-bound measurements. The
retained live inputs re-evaluate as eligible locally with current signatures.
P06 persists each campaign's actual plan holds for further CI diagnosis.

The contract CI failure on this head is the generated release evidence
inventory's now-stale source hashes. Regenerate it from current source and
retain the unchanged inventory check. This is not runtime assurance.

The assurance aggregator previously ignored P05/P06 wire artifacts. It now
waits for runtime integration and admits only producer proof from successful
journeys on the same source/run/attempt, with exact validator and artifact
hashes, canonical operation/release identity, request/response conformance and
contracted success status. Failed journeys confer no proof. Repeated browser
observations cannot fabricate consumer, authorization, tenant-isolation or
image provenance. Negative tests reject stale, tampered or invalid receipts.
The strict qualification gate remains mandatory; missing claims stay missing.


Follow-up local validation: **226 contract tests pass**, **609 Planning tests
pass**, **22 PostgreSQL cases remain CI-only**; Ruff, strict mypy, generated
bundle/authority parity, active registry/integrity and nine-component runtime
binding checks pass. The regenerated inventory contains **75 active releases,
49 dependency edges and 37 installed copies**, with the existing external
collection enrollment limitation retained. Replaying the completed P05 WebKit
artifact through the new ingestion code yields **20 distinct producer proofs**
and **zero qualified operations** from those proofs alone, as expected.

The same CI run independently reproduces Governance's pinned upstream
`zlib-1.3.2-r0.apk` HTTP 404 across all three build attempts. Exact artifact
hashes/signature requirements remain mandatory; an unavailable reviewed input
is not replaced with unreviewed bytes. P02 broker readiness still fails in one
browser job; retain redacted container state/logs before cleanup to diagnose
that separate failure. Current-source live campaign and release assurance
acceptance remain unverified until the next CI run finishes.


### Typed worker identity and actual effect transport

Run [38782109274](https://github.com/awalker0878/multi-tenant/actions/runs/38782109274)
on head `dbbcb1196f3dd32efb82fdae4685c3edd041f8b8` passes all three P05
browser campaigns and all nine source-bound image builds/aggregation. The
pinned Alpine package was independently retrieved as HTTP 200 with the exact
reviewed size and SHA-256; earlier 404s were intermittent, not a justified
replacement of pinned bytes. P02 succeeds in all three browsers on this run.

All P06 browsers progress through campaign admission, crash-before-acceptance,
sealing and retry, then stop at `p06-migrate-reserve: outcome_unknown`. Actual
source comparison identifies the hard-coded `sim-worker` producer identity,
which the worker's UUID contract correctly rejects. The separate Temporal
poller and process witness now require `LIFECYCLE_SIMULATION_WORKER_ID`, and
campaigns enroll that exact UUID. The execution owner rejects invalid worker
identities before durable acquisition or redemption. Unit fixtures now use a
canonical UUID instead of bypassing the real transport's identity requirements.
The crash witness removes its local `completed` flag before persisting/sending
the actual typed effect grant, so late-arrival tests exercise real fencing
rather than an unrelated extra-property denial.

Lifecycle units pass **384 tests** with **86 database cases skipped**; Ruff and
strict mypy pass. A new PostgreSQL-backed test sends a real acquired grant through
the actual worker ASGI endpoint and validates the canonical SimulationGrant.
Local database execution cannot start because the isolated execution UID mapping
rejects chown to the fixture's nonroot owner with EINVAL; these tests remain
CI-required, not locally verified or silently skipped as assurance.

The updated aggregator executes successfully and remains red with **372/1,073
verified claims, 0/166 qualified HTTP operations and 4/75 qualified canonical
releases**. Missing claims: producer 170, consumer 196, authorization 164,
tenant isolation 163, authentication 3 and route 5. This is explicit unfinished
repository-owned assurance work, separately from deployment enrollment and real
native/receiving qualification. No broader completion is claimed.


### Redemption callback closes the producer/consumer chain

Run [38783949271](https://github.com/awalker0878/multi-tenant/actions/runs/38783949271)
on head `648daafa3e9bbe09785c8b18e888dfe7363b9b9b` passes the P06 core
PostgreSQL suite, including the new grant-to-worker HTTP case. Live migration
reserve still reports outcome unknown. The real worker callback reaches
`ExecutionApp`, which independently retained the second hard-coded worker
name in its redemption call. The authenticated simulator handler now passes
`identity(body['worker_id'])`; the execution owner still enforces exact journal
worker, grant, campaign, current authority, expiry, custody and single-use state.
The database regression is strengthened to route redemption back through the
actual Lifecycle ASGI handler instead of a direct domain callback. Local route
checks require a canonical UUID and prove invalid workers never reach redemption.
This corrects a missed executable boundary; no schema or security check is relaxed.

Callback correction local verification: **226 contract tests pass**, **386
Lifecycle units pass**, **86 database cases require CI**; Ruff, strict mypy,
source-bound release inventory and documentation checks pass. The protected
worker and redemption schemas are unchanged. Live and database callback-chain
acceptance remains pending current-source CI.


### Fencing probe transport validity

Direct live worker negative probes now supply the exact body/path-bound replay
key, matching the unchanged worker transport contract. The sealed-absence
late-arrival probe also requires the grant to remain unexpired; otherwise a
403 cannot prove that the seal fenced the request. The post-restore old-grant
probe is labelled only as continued denial, with an explicit limitation that
it may also be expired. A fresh-grant, epoch-only live control remains open
and must not be inferred from that combined denial. No schema, expiry or
custody enforcement is relaxed to obtain passing fixture results.

All P06 browser jobs on run 38785554175 pass (Chromium, Firefox and
WebKit), including crash/recovery, custody, history replay and restore controls.
The stricter fencing transport correction passes **227 contract tests** locally;
the added replay-key regression reaches the real worker endpoint and rejects
a key bound to a different attempt. Final-source live CI is still required.


### Independent current-source checkpoint and remaining security evidence

Head `e7cde0aa25471d7f83064c2583d8f9e85d254cc8` completed
[run 38786986460](https://github.com/awalker0878/multi-tenant/actions/runs/38786986460)
at tested PR merge revision `fdb5d0e1a731fdec69273c8e1cbf8980c58b2c9e`.
All service, SQL, P02–P06 browser and nine built-binding jobs passed. Contract
assurance remains **FAIL**, with **379/1,073 claims**, **18/271 consumer
boundaries**, **0/166 qualified HTTP operations**, and **4/75 releases**.
The missing internal evidence is not described as an external blocker.

The next live campaign isolates each independently mounted custody epoch
while an actual durable grant remains unexpired. The exact same grant must
subsequently be accepted once and recognized as a duplicate; mere denial
cannot earn the control. The PostgreSQL/ASGI regression exercises the worker,
Lifecycle redemption handler and journal together under both epoch faults.
Separate live authenticated wrong-scope/cross-tenant probes cover admission,
job reads and commands, compare the full execution and independent-effect
state before/after denial, and reject protected resource disclosure. Their
qualification receipts require exact source, run attempt and artifact digests,
valid request/response schemas and successful positive controls. New controls
remain unverified until the corrected source completes real CI. The older
post-restore grant still proves continued denial only; isolated pre-restore
controls do not authorize restored-journal re-enablement or native writes.

Local verification for these controls: **235 contract tests pass**; canonical
integrity, publication/retirement, quality-policy cutover, source-bound release
inventory and documentation validation pass. Database/live controls require CI.


### Console request binding and live consumer qualification

The Console's simulation client previously checked schema and tenant/scope,
without comparing a read's job ID, an admission's plan/approval binding or a
command's job/key/action. These are now explicit fail-closed checks. Seven
Laravel cases and a live TLS consumer witness challenge nine substitutions
in actual owner responses. The witness executes the shipped JobsClient,
current Governance delegation and Lifecycle service, with no HTTP fake or
substituted producer for positive evidence. Consumer receipts are admitted
only from successful current-source campaigns with source/loader/installed
release and artifact bindings plus all request-specific negative controls.
Local contract regressions: **237 passed**. PHP syntax and Laravel Pint pass.
Four Lifecycle delegation-status tests, Ruff and strict mypy pass.

Run 38821391028 on head `33c451881329c217004b318f521c71c1763e3633` is
not accepted: wrong-scope authority is denied, but upstream Governance's 401
was propagated after workload authentication. The actor boundary now exposes
that refusal as 403; dependency failures remain 503 and denial is preserved.
That run also exposes upstream 404 for the locked zlib APK in the Assurance
image builder. Independent direct downloads reproduce 404; cached bytes
match the unchanged lock. No package-lock relaxation, native qualification,
completed runtime assurance or release completion is inferred.


### P02 RabbitMQ cookie ownership diagnosis

The retained P02 Firefox/WebKit artifacts from run 38821391028 identify
`/var/lib/rabbitmq/.erlang.cookie: eacces`. P02's root health diagnostic raced
server startup and could create the cookie before the RabbitMQ user owned it.
Both P02 fixtures now run diagnostics as the RabbitMQ account, matching the
existing P03/P04 fixture behavior; readiness, TLS and time bounds stay strict.
This requires a current-source live rerun, not a relabelled external blocker.
The new epoch PostgreSQL/ASGI case passes on `33c45188`. Locally **390
Lifecycle tests pass / 86 PostgreSQL cases skip**, with full Ruff/format/mypy
passing. Independent Planning registry lookup is absent/None; official Alpine
mirror probes also reproduce locked-zlib 404. Internal evidence gaps remain.
