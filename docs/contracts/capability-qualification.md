# Phase 4 — Executable capability qualification

The current capability source is `contracts/capabilities/definitions-v1.json`.
It declares five methods and six modes (30 method/mode combinations). The
**versioned canonical contract remains immutable**; method labels in the
current wire schema are current wire identifiers, not compatibility routes.

## What qualifies in CI

`workers/lifecycle/tests/test_capability_qualification.py` enumerates the
entire matrix from the current registry. For **each** method/mode it checks the
current worker stage selection, bound prerequisites/results and active stage
registry. Every applicable native data operation is then exercised against
its actual typed contract, independent readback and deliberately foreign,
stale or mismatched inputs. The cold image capture and restoration protocols
are independently exercised in `test_openstack_source.py` and
`test_method_protocol.py`.

`scripts/contracts/qualify_capabilities.py` does not infer behavior from
handler filenames, aliases or declaration contents. It requires an **actual
passing worker JUnit result** for all registered combinations, plus all
applicable native-operation dispatch cases, cold capture, uncertain retry,
independent readback, commissioning revocation and authorization denials.
Missing, failing or skipped cases fail the qualification gate.

The gate runs in both `P08 native migration components` and the independent
`capability-qualification` job of `Contract source and consumer integrity`.
P08 retains the original full native worker checks; the focused CI gate
executes the real test modules, not mocked replacements or copied JUnit.

The qualification report records the exact Git revision, source-definition
digest and worker JUnit digest, and lists each method/mode result. It always
sets `evidence_level=E2`, `native_platforms_tested=[]`,
`installed_provider_qualified=false` and `native_write_authorized=false`.
It cannot authorize or commission migrations.

## Separate E3/E4 installed-version admission

E2 proves implementation against controlled native/TLS and dataset peers.
It **does not** prove a specific installed source or destination version, a
production tenant, qualified endpoint methods, commissioning, live writer
fencing, or receiving application acceptance.

Production E3/E4 qualification now also requires **30 explicitly enumerated,
independently observed method/mode outcomes**: each current wire method and
mode is either `passed` or `unsupported`. An unsupported combination is
not eligible for selection. Passing combinations must have an independent,
fresh, scope-bound native case receipt. Missing results, contradictory states,
stale observations and partial matrices fail closed in the worker signer,
Inventory reader and Assurance reviewer.

Independently signed native conformance also binds the nested Inventory installation and scope to the probed installed tuple; a conflicting Inventory projection is suspended before publication.

Passing installed rollback and recovery method/mode outcomes additionally require a nonempty, successful independent restoration/readback measurement; empty recovery evidence cannot silently qualify a method. Unsupported combinations remain explicit holds.

Signed records and runtime observations are compared canonically: JSON
object property ordering is not authority. E3/E4 approval remains tied to
the exact installed tuple, reviewed inventory and provider evidence; no
synthetic test or metadata declaration can promote an unsupported combination.

Production E3/E4 Inventory and Assurance verifiers reject revoked or revocation-state-unknown enrolled keys and require signed core adapter/installed-identity/runtime-artifact claims before admitting an installed observation. A cryptographically valid signature is not sufficient after revocation.

Production E3/E4 qualification requires real, independently enrolled
observer evidence through the existing
`workers/lifecycle/.../capability_conformance.py`,
`services/inventory/.../capability_observations.py` and
`services/assurance/.../NativeQualification.php`. Those components verify
signed observed installed tuples, fresh dimensions, independent observers,
review decisions, custody and optional receiving acceptance. Installed
provider support must remain held until those current, independently
authenticated records exist; neither this matrix nor generated definitions
grant runtime authority.

Assurance derives the enrolled public-key fingerprint after cryptographic verification and rejects verifier-reserved identity fields within signed observer, reviewer, or receiving-owner claims. Mounted E3/E4 dossiers accept only the current V2 registry shape; removed V1 registry records cannot be read or silently downgraded to `unknown`.

There are no version aliases, dual-running fallback handlers or migration
compatibility shims in this implementation. The old `LEGACY_METHODS`
generated symbol was replaced with `WIRE_METHODS` to describe the **active**
wire method set.

## Commands

```sh
cd workers/lifecycle
uv sync --locked --group build
uv run --frozen pytest -q \
  tests/test_capability_qualification.py \
  tests/test_method_protocol.py \
  tests/test_openstack_source.py \
  tests/test_migration_bootstrap.py \
  --junitxml=/tmp/worker-capabilities.xml
cd ../..
python scripts/contracts/qualify_capabilities.py \
  --worker-junit /tmp/worker-capabilities.xml \
  --output /tmp/capability-qualification.json
python -m unittest discover -s tests/contracts -p test_capability_qualification.py -v
```

A failed test **blocks** an E2 qualification. Passing E2 never overrides a
held, stale, unqualified, or unavailable installed-version E3/E4 record.
