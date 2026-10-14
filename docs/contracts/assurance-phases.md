# Contract assurance — operation qualification and built-runtime binding

The active source registry is `architecture/contract-consumers.json`. No compatibility
aliases, retired API copies, or historical runtime shims participate in these
assurance flows.

## Phase 1: contract integrity, dependency closure and release rationalization

`check.py`, `discovery.py`, `build.py`, `generate_authority_releases.py`,
`runtime_inventory.py`, `installed_usage.py` and the Git review-base publication
check independently enforce current canonical ownership, complete locally
resolvable references, manifests, generated projections, installed copies and
safe repository retirement. `dependency_graph.py` and `release_inventory.py`
produce checked reports from those inputs. Built wheel/image source parity is
part of this integrity baseline; passing it does not qualify runtime behavior.
The [implementation ledger](phase1-ledger.md) records execution and the unresolved
external collection-manifest evidence. Phase 1 is not marked complete.

## Phase 2: runtime producer/consumer and security conformance

`scripts/contracts/assurance.py` enumerates every active canonical release
and every declared HTTP operation directly from the current OpenAPI documents.
It is independent of the owner-specific route test lists.

Five **separate** executable claims are needed for each protected HTTP
operation: route, producer, consumer, authorization denial, tenant isolation.
An anonymous operation requires route, producer, consumer. A non-HTTP release
requires executable producer and consumer evidence. Examples, registry entries,
and test filenames do not count as execution.

Evidence records are bound to the canonical file's SHA-256. Release-grade runs
also require the invoking GitHub Actions run ID, run attempt and exact commit SHA. Executed
claims may be emitted by `assurance_routes.py`, `python_denials.py`,
`measured_consumers.py` and `laravel_denials.php`. Tests verify stale and
duplicate evidence is rejected. The aggregate
`scripts/contracts/combine_assurance.py` writes a detailed per-operation and
per-release report with every missing claim.

**CI / Contract assurance** is a mandatory affected-change job. It consumes
fresh observations from the Python and Laravel owners and requires complete
qualified coverage, not just source validity. Missing tests keep the required
gate red until executable evidence exists for each current operation and
non-HTTP release. No manual bypass or compatibility exception qualifies it. Where a real producer or tenant isolation
probe does not exist, write the actual test; never substitute a route match,
static fixture or blanket allowlist.

## Phase 1 artifact integrity and Phase 2 measured runtime binding

`scripts/contracts/dependency_graph.py` derives typed HTTP, event, schema,
capability and platform consumption edges from the current registry. It
distinguishes producer-local shipped schemas from cross-service consumption
and does **not** repurpose a legacy deployment layering graph as actual
runtime dependencies. An edge without a verified installed loader remains
labelled `registry-declaration`.

`scripts/contracts/runtime_binding_coverage.py` requires every deployable
owner and registered installed-copy component to have an OCI image-build
attestation job.

`scripts/contracts/artifact_attestation.py` inspects **built** image
filesystems and wheel ZIPs; it verifies all registered packaged JSON bytes,
detects unregistered contract JSON and malicious wheel entries, compares
entire Python package bytes and shipped PHP runtime configuration, bootstrap,
public PHP entrypoints, the migrations actually shipped, and application resources
against the reviewed checkout. PHP images also attest the shipped Artisan entrypoint,
Composer manifests and their installed production dependency identities against the
reviewed lockfiles. Compiled Console Vite output is checked through its emitted
manifest and referenced asset files instead of being mistaken for checked-in source.
This does not independently attest third-party vendor source bytes. The verifier pins
the built artifact content ID
to the exact 40-character Git release SHA. It records owned operation IDs,
canonical file digests, and consumed release identities with an explicit
distinction between installed-copy proof and registry-only declarations.

`scripts/contracts/aggregate_artifacts.py` consumes the immutable outputs
of all nine image builds and five Python wheel builds, requiring exact match
against the current canonical registry. It emits one complete
`runtime-release-bindings.json` mapping **all active canonical releases** (HTTP,
event, schema, capability, and platform) and canonical HTTP operations to built
image digests. Each release-to-image relationship distinguishes an exact
installed-copy byte match from a registry-only declaration. A declaration is
never promoted to runtime usage evidence.
A contract-platform convention with no registered consumers is explicitly
listed as `source_only` without inventing a deployable runtime image. Shared foundation operations are labelled as shared declarations
on the participating service images, not independent HTTP execution results.

The **Contract artifact and runtime binding assurance** workflow must pass
before these images can be treated as packaged-contract verified. Do not
advertise this attestation as proof of tenant authorization or business response
behavior; those belong to Phase 2's separately measured probes.

## Commands

```sh
python scripts/contracts/check.py
python scripts/contracts/dependency_graph.py
python scripts/contracts/runtime_binding_coverage.py
python -m unittest discover -s tests/contracts -p 'test_assurance.py' -v
python -m unittest discover -s tests/contracts -p 'test_phase2_artifacts.py' -v
python scripts/contracts/assurance.py --output /tmp/contract-inventory.json
# CI produces /tmp/contract-assurance-report.json from measured evidence.
# Required CI / Contract assurance fails on an incomplete measurement set.
```

The active worktree keeps no historical contract copies, retirement rosters or
compatibility loaders. Git retains its normal commit provenance.

## Existing new-publication quality admission

`architecture/contract-quality-policy.json` and `scripts/contracts/quality.py`
enforce current security, error, idempotency, JSON Schema identity and event
delivery requirements on all newly published canonical versions. Semantic
change analysis rejects same-major changes to previously guaranteed response
schemas, consumer parameters, authorization, idempotency scope/retention,
public exposure, and channel/message bindings. See
`docs/contracts/release-quality.md`.

## Existing synthetic method/mode qualification

`scripts/contracts/qualify_capabilities.py` requires a passing native-worker
JUnit receipt for **every** defined method/mode, every implemented native
data-operation stage, cold capture, independent readback and revocation.
The Contract Integrity and P08 jobs fail if a result is missing, skipped,
failing or unqualified. This is strictly E2 synthetic behavior qualification;
installed versions require separate independently signed E3/E4 custody and
review and cannot be promoted from these results. See
`docs/contracts/capability-qualification.md`.
