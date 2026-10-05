# P01 foundation HTTP contracts

P01.03/P01.04; R02/R35; architecture and owning service reviewers. The versioned
[OpenAPI artifact](../../contracts/openapi/foundation-health-v1.json) describes the
three implemented diagnostic routes in all seven applications. Each owning origin
remains independently deployed. The generated default origin is deliberately
unconfigured. A health bearer token cannot authorize business or native work.

The contract distinguishes process liveness, unavailable product readiness and
authenticated foundation dependency status. It includes the existing PHP/Python
reason variants, safe failure bodies, no-store headers and bounded retry advice.
No command or business API is created: diagnostic GETs have no mutation idempotency
key. Catalogue reference-event identity and retry semantics remain in the separate
[messaging record](p01-messaging.md).

The independent tooling under `scripts/p01/contracts/` replays the previously
measured exact tool selection from its own locks. It validates OpenAPI 3.0.4,
generates PHP/Python/TypeScript clients twice and compares every output hash,
compiles/lints generated code, and checks five valid and 23 invalid wire fixtures.
PHP Opis and Python OpenAPI validation must agree before accepted bodies enter
the generated models; both model round trips preserve accepted fields. Generated
models are not complete schema validators. Outputs remain temporary private
conformance adapters; no product imports the P00 spike or this support tooling.

`Foundation contracts` runs on branch pushes and pull requests, using the actual
push base or PR merge base. Existing JSON/YAML artifacts under `contracts/` are
immutable byte-for-byte; deletion or any modification fails, including apparently
additive enum/field changes. New versions use new artifacts and require an explicit
consumer migration/replay plan. This conservative rule does not claim general
schema-language inclusion, reviewed compatibility windows or protected admission.
The checker itself still needs the independent policy protection recorded in
[code controls](p01-code-control.md).

Local replay passed all 28 PHP/Python fixtures, model round trips, TypeScript
compilation and deterministic generation. Local snapshot testing cannot perform
the Git base comparison; the hosted report records that separate check. Actual
provider HTTP behavior belongs to the source-bound Compose/Kubernetes reports.
Business command/problem/digest protocols are implemented with their receiving
feature packages; this diagnostic contract does not silently settle those designs.
