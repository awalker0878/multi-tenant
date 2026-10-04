# ADR-012 — Contracts and event evolution

Owner role: Architecture lead. Related phases: P00, P01. Record date: 2026-10-04.

Origin: `DESIGN`. Disposition: `PROPOSED` as recorded in the [decision register](decision-register.md).

This record develops the existing baseline for review. No accountable-owner acceptance, experiment result or native qualification is claimed; the register disposition is unchanged.

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

- Choose schema dialect/tooling, error model, idempotency scope and event envelope fields.
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
