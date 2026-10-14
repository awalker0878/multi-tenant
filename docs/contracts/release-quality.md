# Contract release quality — Phase 3

**Applies to newly published canonical versions.** Existing published canonical
versions are immutable and cannot be silently patched to satisfy this profile.
No deprecated endpoint aliases, fallback parsers, compatibility shims or
dual-version installed copies are introduced.

## Admission gates

Every proposed canonical file must have a versioned filename. The policy and
machine-enforced admission rules are in
`architecture/contract-quality-policy.json` and
`scripts/contracts/quality.py`. The Contract Integrity workflow calculates
the trusted Git review base, enumerates files independently of the editable
active-release registry, validates the new files and publishes the semantic
change report. CI / Contracts runs the quality admission on every affected
change. During first adoption, when the trusted mainline base predates the
quality policy, the initial policy-introduction commit forms the baseline
for subsequent releases; this is derived from Git provenance, not a retained
legacy contract, runtime shim or editable exemption list. Once the policy
exists on main, every newly published canonical is checked against the
trusted pull-request base. P01 continues to prohibit in-place mutation
and unreviewed canonical deletion.

### HTTP/OpenAPI

Every new operation must have a unique stable `operationId`. URL template
variables require matching, non-duplicated, mandatory string-typed path
parameters (including bounded integer revision identifiers). Only explicit numeric HTTP statuses are admitted: a `default`
response cannot conceal unmodelled failures or bypass the Error v2 policy.


New HTTP interfaces use OpenAPI 3.1 with exact `info.version` parity. Each
operation must declare a resolvable, non-anonymous security requirement.
Public unauthenticated endpoints must be explicitly marked and limited to
approved diagnostic paths. Typed 200/201 JSON responses and explicit 401, 403 and 503
failure responses must be present; any request body, including non-JSON
media, requires an explicit schema and a 422 response; mutations require 409. Any explicitly documented 4xx/5xx JSON error body, including statuses beyond the required minimum, uses the exact new canonical
`contracts/schemas/common/error-v2.json` envelope: stable machine code,
safe message, correlation UUID, retryability and optional bounded field
details. No generic default response substitutes for these cases. Additional bodyless statuses may be documented when the producer makes no response-envelope guarantee; these must not be represented as verified Error v2 payloads.

Mutating operations must require one bounded `Idempotency-Key` header, record
an exact scope of tenant, actor, operation and request digest, set a finite
retention window, and explicitly define 409 conflict semantics. Wire schemas
cannot accept uncontrolled extra top-level input properties.

### JSON Schemas

New schemas must declare JSON Schema 2020-12 and a unique HTTPS `$id` tied
to the canonical filename/version. New top-level object schemas reject
additional undeclared properties. Existing published schemas lacking IDs are
not rewritten in place.

### Events

New AsyncAPI contracts use version 3.0 and canonical event payloads with an
explicit, typed tenant/identity/correlation envelope (UUID identities and
date-time occurrence). Each channel must have a unique nonempty broker address and bind every declared message. Messages must explicitly use JSON Schema draft-2020-12 format. Each channel must define
at-least-once delivery, tenant ordering, event-ID deduplication, bounded
retry attempts, exponential jitter backoff, after-commit acknowledgment,
a dead-letter address, a retention window and a bounded deduplication
window. Publishing and receiving operations must bind declared channels.

### Capability and platform declarations

New capability catalogues and platform profiles must validate their contents
against their active, versioned canonical JSON Schema. A JSON object that only
passes a structural parse is not an admissible capability declaration; missing
schema files, unrecognized properties and invalid statuses fail closed.

### Semantic change admission

The admission script resolves the latest previously published version in
the Git review base. It evaluates removed methods and routes, security
changes, operation IDs, request constraints and required fields across **every declared request media type**,
response statuses/media/guarantees across **every response media type**,
media encoding, nested arrays, event routing/delivery, and capability/platform declaration changes. Existing method semantics, ordered migration stages, qualified statuses and field inventories cannot be removed or changed in a minor release. New schema
identifiers are collision-checked against all current canonical schemas.
A breaking change cannot reuse the same major version. A breaking major
version must be explicit and is listed in the generated change report for
consumer migration planning. This is a release-contract gate, *not* a claim
that any untested running service accepts or produces a wire contract.

## Phase 2 runtime binding

`scripts/contracts/dependency_graph.py` derives typed provider/consumer
relations from active releases rather than a hand-maintained dependency DAG.
`scripts/contracts/artifact_attestation.py` verifies built images and Python
wheels, installed contract bytes and bounded runtime source identity.
The Console image is also required to ship its compiled Vite manifest and
all referenced browser assets. The runtime coverage validator confirms the
artifact qualification workflow is invoked from pull-request CI and is a
dependency of the required result; merely defining a manual builder is insufficient. `aggregate_artifacts.py` requires the
complete release-bound image/wheel matrix; the artifact workflow is invoked
on pull requests and main-branch pushes.

An artifact identity statement is distinct from operation-level behavioral
qualification. `scripts/contracts/assurance.py` still demands measured
producer, consumer and security-negative evidence before declaring an API
operation qualified. No static code search or source-bound image can provide
that behavioral proof alone.

## Checks

```sh
python scripts/contracts/quality.py --base "$(git merge-base origin/main HEAD)"
python -m unittest discover -s tests/contracts -p 'test_quality.py' -v
python scripts/contracts/check.py
python scripts/contracts/runtime_binding_coverage.py
python -m unittest discover -s tests/contracts -p 'test_phase2_artifacts.py' -v
```

For an intentionally breaking change, publish a new **major version**,
update all actual consumers and generated clients, and demonstrate readiness
before changing the active runtime binding. Do not add compatibility
controllers or aliases to mask incomplete migrations.
