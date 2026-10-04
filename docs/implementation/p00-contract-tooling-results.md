# P00 contract tooling results

Related work: P00.03 / R01; informs P01.03 and ADR-012. This is a measured candidate for isolated contract generation. It does not accept the enterprise contract dialect, implement a product API or close G00/G01. Existing service ownership, pragmatic Laravel conventions and framework-free Python domain rules are unchanged.

## Candidate and immutable inputs

The [experiment](../../spikes/compatibility/contracts/README.md) uses one pinned OpenAPI Generator distribution for three consumer languages. The generator embeds its Java executable artifact in the hash-locked Python wheel; generation needs no floating Maven download. TypeScript installation uses a separate exact npm lock. Generated Composer/npm/Python manifests are never used as unreviewed dependency installers.

| Component | Candidate / measured version | Purpose |
| --- | --- | --- |
| HTTP description | OpenAPI 3.0.4, small explicit object/enum/nullability subset | Synthetic read/create sample operation, request, response and problem model. |
| Event schema | JSON Schema draft 2020-12 | Synthetic versioned envelope with tenant, producer, aggregate version, event/time, correlation and causation fields. |
| OpenAPI Generator CLI | 7.25.0 | PHP `guzzle`, Python `httpx`, TypeScript `typescript-fetch` client generation. |
| OpenAPI validation | `openapi-spec-validator` 0.9.0 and `openapi-schema-validator` 0.9.0 | Validate the HTTP definition and its dialect-specific wire fixtures. |
| JSON Schema validation | `jsonschema` 4.26.0 with explicit format checking | Validate event fixtures, including real date-time and UUID formats. |
| Python generated-model runtime | Pydantic 2.13.5, HTTPX 0.28.1, Python 3.12.14 | Compile generated source and exercise its model serialization. |
| TypeScript compile/runtime | TypeScript 6.0.3, Node 24.19.0, npm 11.9.0 | Strict compile, decode/encode and mocked fetch transport. |
| Generator runtime | OpenJDK 17.0.20 locally | Execute the wheel's embedded JAR; CI records its own Java build. |
| PHP target | PHP 8.5.11 candidate | Generated-source lint and explicit model validity/serialization checks require remote execution. |

The local embedded JAR SHA256 is `41ce4f6b07f196676439d710759fa1ced7a08066d06ff1bf314681470289efae`. `pyproject.toml`, `uv.lock`, `package.json`, `package-lock.json`, both schemas, fixtures, all generator configurations and all probe sources are individually bound in each report. CI also records its GitHub revision/run/workflow binding. These are synthetic inputs, not a new authoritative product contract tree.

The OpenAPI 3.0.4 choice limits this experiment to a schema subset that the PHP generator advertises. It is not a claim that 3.0.4 is the newest standard. Full OpenAPI 3.1/3.2 semantics and PHP union/polymorphism behavior are not qualified here. ADR-012 must decide the actual product dialect before P01.03 adopts complex schemas. Independently validating the draft 2020-12 event does not imply that OpenAPI 3.0 schema objects are interchangeable with that dialect.

## Executed checks

[Local report](../../spikes/compatibility/results/contracts/local-20261004/report.json) and [complete generated-output hashes](../../spikes/compatibility/results/contracts/local-20261004/generated-sha256.json) retain the actual execution. Status is `LOCAL_PASS_PHP_NOT_RUN`: PHP is unavailable in the local environment. That limitation is explicit; PHP client runtime compatibility is not established by generating PHP text.

| Check | Actual local result | What it establishes |
| --- | --- | --- |
| OpenAPI definition | Both the independent validator and generator validator pass | The candidate description is structurally usable by both tools. |
| Wire fixtures | 18 verdicts: five accepted, 13 rejected | Required fields, unknown enum/version, wrong scalar type, decimal-string precision, empty labels, unknown command fields, status ranges and event scope/date/version constraints. |
| Invalid schemas | Two rejected with their expected schema exception classes | A missing operation response and an invalid event-schema type cannot silently pass. |
| Deterministic generation | 53 files compared byte-for-byte across two clean generations: PHP 20, Python 16, TypeScript 17 | Same pinned inputs produce the same complete output tree in this environment. No timestamp/path normalization hides differences. |
| Schema drift | A changed enum alters generated output | The regeneration comparison detects a concrete schema mutation. This is not a semantic breaking-change classifier. |
| Python | Generated source compiles; nullable/precision/additive-response fields round-trip; three invalid model values reject | The selected Pydantic model path works with the measured runtime. |
| TypeScript | Entire generated client strictly compiles; nullable/precision fields survive serialization; one mocked HTTP call uses the expected path and synthetic bearer header | The generated TypeScript client runs with the measured compiler and fetch runtime. |
| TypeScript negative compile | Unknown enum assignment produces the expected `TS2322` at the negative fixture | Static types catch this known caller error. |
| PHP | Not executed locally | CI must lint every generated PHP file and run the supplied model probe with `--require-php`. |

The event fixture includes a tenant scope selector and causality fields to validate wire structure. It grants no identity, authority or permission. No real token, endpoint, tenant or platform resource is used. Request `actor_id` is an explicitly rejected unknown field, preserving the distinction between ordinary payload input and authenticated authority.

## Findings that affect implementation

Generated clients are useful wire adapters, but they do not consistently enforce the schema. The Python generated request model ignores unknown input fields even though the request schema rejects them. The TypeScript decoder accepts an unknown enum at runtime despite the static compiler rejecting that enum in typed code. The supplied PHP probe examines constructor permissiveness and explicit validity checks; PHP behavior requires its own recorded execution.

P01.03 must validate untrusted data against the correct contract dialect before generated deserialization, then map the resulting wire DTO to service-owned domain/application values. An Infrastructure adapter must set its approved origin, authenticated principal/delegation, timeouts, error mapping and coordinated retry budget. The generated bearer option only formats a header; it is not an authorization system. Business validation and resource authorization remain separate.

Response objects explicitly allow additional fields; command objects and the test event envelope explicitly reject them. Decimal revision strings preserve the value `9007199254740993` across JavaScript/Python model paths. Enum growth is not assumed backward compatible. No `oneOf`, polymorphic inheritance, arbitrary number precision, canonical command hashing or null/absent-field behavior beyond the tested cases is claimed.

Use the generated output as a private dependency pinned to the producing schema revision. PHP consumers keep it behind `app/Infrastructure/`; Python consumers keep it behind their service's `infrastructure` layer; the console uses its service-access boundary. Generated code must not become a cross-context Eloquent/domain model or a shared business-logic package. Generation does not require Laravel Boost or any domain scaffolding program.

## Adoption and remaining scope

Architecture and producer/consumer owner roles are proposed joint custodians of the generator/dialect decision. Each owning service reviews its schema changes. The build/platform role is proposed custodian of the hash-locked tool distribution and approved mirror; named accountable people and operating acceptance remain pending. Update the generator, templates, schema, compiler or runtime in a small reviewed change, resolve locks deliberately, regenerate in a clean environment and retain input/output hashes and positive/negative results. Never patch generated output manually to hide a drift.

The candidate is suitable for further review for simple HTTP clients. It does not settle the product's error/idempotency semantics, initial contract version policy, actual provider/consumer inventory or authentication delegation. AsyncAPI channel/binding/code generation, broker compatibility, outbox/inbox crash recovery, cross-language canonical digest vectors, compatibility-window checks and rolling-upgrade evidence remain P01.03/G01/G10 work. This experiment covers event schema validation only. Product contract ownership and examples remain in [contract conventions](../contracts/README.md), [examples](../contracts/examples.md) and [ADR-012](../decisions/adr-012-contracts-and-event-evolution.md).

## Primary references reviewed

- [OpenAPI 3.0.4 specification](https://spec.openapis.org/oas/v3.0.4.html) — the exact HTTP-description dialect used by this probe.
- [OpenAPI Generator installation](https://openapi-generator.tech/docs/installation/) and [PHP generator](https://openapi-generator.tech/docs/generators/php/) — generation options and the PHP capability limits; additional-property defaults are configured explicitly.
- [Python generator](https://openapi-generator.tech/docs/generators/python/) and [TypeScript fetch generator](https://openapi-generator.tech/docs/generators/typescript-fetch/) — client template selection. Actual compatibility is established by the locked runs above.
- [JSON Schema draft 2020-12](https://json-schema.org/draft/2020-12) and [jsonschema validation](https://python-jsonschema.readthedocs.io/en/stable/validate/) — event dialect and explicit format validation.
- [OpenAPI spec validator](https://openapi-spec-validator.readthedocs.io/en/latest/) — independent structural validation before generation.
