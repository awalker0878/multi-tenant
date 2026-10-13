# Contract assurance — evidence-gated qualification (Phase 1)

This phase inventories **every** active canonical contract and every HTTP operation
directly from `architecture/contract-consumers.json`; it does not copy a second
API registry into source control. `scripts/contracts/assurance.py` generates the
versioned, SHA-256-bound result. The inventory includes OpenAPI, AsyncAPI, JSON
Schema, capability and platform contracts.

## Separate structural integrity from qualification

A syntactically valid contract, byte-identical installed schema, generated type,
existing route or named test is **not qualified producer/consumer behavior**.

Every HTTP operation must have five independently measurable categories, with
authorization and tenant-isolation cases required when the operation declares
security:

- `route`: a real service router/route:list check matched its exact method/path
- `producer`: the actual application returned an accepted payload validated
  against the active operation response schema
- `consumer`: the actual installed consumer accepted the producer-shaped
  payload and rejected invalid or stale input
- `authorization`: an executable boundary rejected a missing/invalid caller
- `tenant_isolation`: an authenticated cross-tenant request was independently
  denied, not merely rejected for missing headers; receipts require different
  credential and requested tenant scopes, authentication, and a real 403/404/423

Non-HTTP releases require independently executed producer and consumer proof.
These include actual broker event publishers/consumers, validated schema
boundaries and installed capability/platform consumers. Their canonical
structural schema checks alone do not constitute runtime qualification.

Evidence is accepted only for an active operation or release, with the exact
SHA-256 fingerprint, evidence kind, executable test identity and PASS result.
Release-grade qualification also requires matching `GITHUB_RUN_ID` and
`GITHUB_SHA` from the current workflow. Empty, mismatched, duplicated or
stale evidence fails closed; no wildcard/alias or historical compatibility
exception grants coverage.

## Currently measured evidence

- `scripts/contracts/assurance_routes.py` invokes the existing owner-owned
  Laravel route comparison and Python router probes before emitting route
  proof. Explicit successful ASGI request/response schema validation allows
  positive producer proof for the native Lifecycle and selected Planning reads.
- `scripts/contracts/laravel_denials.php` sends missing-token requests to
  the **real** locked Laravel applications. Only 401/403 count as auth-denial
  evidence; 503/404/5xx do not count. It requires locked PHP dependencies.
- `scripts/contracts/assurance_routes.py` additionally measures 401 denial from
  the independent native-job and worker-effect ASGI route verifiers. These
  receipts never claim tenant isolation or a successful business response.
- `scripts/contracts/python_denials.py` probes the actual composed Inventory,
  Planning and Lifecycle ASGI services. It omits separately deployed native
  control and worker processes rather than faking coverage.
- `scripts/contracts/measured_consumers.py` executes exact Inventory,
  Planning, Lifecycle and Governance consumer paths, including the actual
  Lifecycle ASGI placement receipt through Planning's installed validator.
- `scripts/contracts/combine_assurance.py` combines ephemeral observations
  from the same workflow run. The required CI / Contract assurance job retains an operation-level
  report and invokes **`--require-qualified`**, which fails the workflow
  until *every* current release and operation has earned all required proof.

This qualification gate is **expected to remain red** while remaining service
owners add actual positive producer/consumer, broker, and authenticated
cross-tenant tests. This is an honest boundary, not a waiver. The report exposes
missing claims by exact contract and HTTP method/path. A green structural job
without that proof must not be described as assurance completion.

## How to extend coverage

1. Use the current canonical operation path, verb and release SHA; never refer
   to a retired contract or add a compatibility shim.
2. Build a service-owned test using the real HTTP/event boundary with
   deliberately controlled owner dependencies; compare actual returned JSON
   with the exact current contract and challenge authorization separately.
3. Execute the installed consumer's actual validation path, including a
   malformed/stale payload negative test. Retain tenant isolation as its own
   credentialed test.
4. Emit a receipt from the **test runner after successful execution**, not from
   a manually edited ledger. Bind it to `GITHUB_RUN_ID`, `GITHUB_SHA`, release
   `sha256`, `operation_key`, evidence `claim`, `source`, `test`, and `PASS`.
5. Run the full Contract Integrity workflow; inspect the uploaded
   `contract-assurance-report` for remaining unqualified interfaces.

Local structural inventory:

```sh
python scripts/contracts/assurance.py --output /tmp/contracts-assurance.json
python -m unittest discover -s tests/contracts -p 'test_assurance.py' -v
```

Release qualification (requires executed evidence from this CI run):

```sh
python scripts/contracts/combine_assurance.py \
  --input-directory "$RUNNER_TEMP/measured" \
  --output "$RUNNER_TEMP/contract-assurance-report.json" \
  --require-qualified
```

No new canonical compatibility layer, alias, runtime shim or legacy test is
introduced by this phase. Removed versions are not retained as additional worktree artifacts. Git commit
history remains the source of prior source revisions.
