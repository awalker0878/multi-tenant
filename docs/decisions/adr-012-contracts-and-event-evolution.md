# ADR-012 — Contracts and event evolution

Owner role: Architecture lead. Related phases: P00, P01. Record date: 2026-10-04.

Origin: `DESIGN`. Disposition: `PROPOSED` as recorded in the [decision register](decision-register.md).

This record develops the existing baseline and records bounded contract-tool experiments for review. No accountable-owner acceptance or native qualification is claimed; the register disposition is unchanged.

## Context

Independent PHP and Python services need an explicit interoperability baseline. Schema-first OpenAPI/AsyncAPI definitions, transactional outbox/inbox behavior and expand/contract evolution are proposed to prevent unreviewed payload drift and coordinated breaking rollouts. Published examples must not become competing schema authorities.

## Decision and scope

OpenAPI/AsyncAPI schema-first contracts, outbox/inbox, at-least-once events and expand/contract evolution.

Initial checkpoint: NOW: P00.02/P00.03 before P01.03.

Refinement and validation: Compatibility/version/deprecation proof at G01 and rolling upgrades at G10.

## Options and trade-offs

| Option | Assessment |
| --- | --- |
| Schema-first contracts with compatibility checks | Makes the interface reviewable before implementation and supports generated references and cross-language conformance. |
| Code-first schemas generated after implementation | Can reduce duplicate authoring, but requires a reviewed process that catches behavioral and compatibility changes before release. |
| Shared internal classes or unversioned messages | Couples languages and deployments and leaves independent consumers without an enforceable compatibility boundary. |

## Consequences

- Canonical machine-readable definitions own wire fields; service documents own intent, authorization and business semantics.
- Consumers handle at-least-once delivery and unknown compatible fields; breaking changes require an explicit coexistence/deprecation plan.

## Unresolved details and evidence needed

- Review the measured OpenAPI 3.0.4 supported subset, JSON Schema 2020-12 event validation and exact generator tuple below; settle product error/idempotency/envelope semantics and AsyncAPI channels/bindings before P01.03.
- Define compatibility windows, consumer inventory, contract review ownership and removal criteria.

## Acceptance and validation

- Validate representative request, response, error and event fixtures in PHP and Python.
- Prove outbox/inbox recovery and backward-compatible deployment at G01.
- Exercise rolling upgrades and retirement of an old contract version at G10.

Record actual reviewer identity, decision date and evidence references when review occurs. Record delivery and gate outcomes in the delivery register; updating this ADR does not complete a work package.

## Revisit conditions

A new consumer or transport introduces unsupported schema semantics, or an interface change cannot fit the established evolution policy.

## Related records

- [Decision register](decision-register.md) — authority for disposition, origin and blocking checkpoint.
- [Phased implementation plan](../implementation/phased-plan.md) — package and gate sequence.
- [ADR authoring template](../templates/adr.md) — required decision-record fields.

## P00 tool candidate and adoption boundary

The [contract-tooling report](../implementation/p00-contract-tooling-results.md) records executed deterministic generation and cross-language checks for OpenAPI Generator 7.25.0, openapi-spec-validator 0.9.0 and jsonschema 4.26.0. The bundled generator JAR, Python/TypeScript locks, generator options, synthetic schemas and complete generated-file hash inventories are retained. PHP/Guzzle, Python/HTTPX/Pydantic and TypeScript/fetch are the proposed client families for the demonstrated OpenAPI 3.0.4 subset. A separate JSON Schema 2020-12 validates the synthetic event envelope; it is not an AsyncAPI implementation.

The passing CI experiment checks valid and invalid request/response/problem/event fixtures, malformed schemas, deterministic generation, schema-change detection, compilation and selected model/decoder behavior. TypeScript exercises mock HTTP serialization. PHP model checks do not exercise Guzzle transport; Python model checks do not exercise live HTTP. None proves service authorization, canonical digest vectors, idempotency, provider/consumer compatibility windows, broker delivery or outbox/inbox recovery.

Generated types are private transport adapters: PHP belongs under the consuming service's Infrastructure namespace, Python behind its Infrastructure adapters, and TypeScript at the console service-access boundary. Do not share them as domain models or import a foreign service's implementation. The observed decoders are permissive in specific ways, including PHP constructor scalar handling, ignored Python extra fields and TypeScript enum decoding. Validate the declared wire schema before translating into owned domain behavior; generated clients alone are not runtime validation.

The architecture and service owners may adopt this measured candidate with an update owner and explicit supported schema subset. P01.03 must implement product contracts and compatibility/deprecation checks, settle additive-field/enum policy by message kind, and demonstrate actual outbox/inbox recovery. It must also select and test AsyncAPI dialect, channels and broker bindings. The strict extra-field rejection in the synthetic request fixture does not prescribe closed schemas for every response/event. Tool execution supplies evidence to this review without deciding the outstanding domain semantics.
