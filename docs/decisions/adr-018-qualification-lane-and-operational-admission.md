# ADR-018 — Qualification lane and operational admission

Owner role: Security/qualification leads. Related phases: P00, P06. Record date: 2026-10-04.

Origin: `DESIGN`. Disposition: `PROPOSED` as recorded in the [decision register](decision-register.md).

This record develops the existing baseline for review. No accountable-owner acceptance, experiment result or native qualification is claimed; the register disposition is unchanged.

## Context

The product must run authorized lab campaigns before qualification exists without allowing unqualified combinations into normal operation. A separate qualification lane is proposed to resolve that dependency. Lab authority must not be convertible into operational support merely by completing a workflow.

## Decision and scope

Separate authorized lab qualification lane; operational admission requires qualified exact-tuple evidence.

Initial checkpoint: PROVISIONAL: P00.04 defines authority boundary and campaign scope.

Refinement and validation: Final admission/fencing design before P06.01; deny tests G06; every native campaign separately authorized.

## Options and trade-offs

| Option | Assessment |
| --- | --- |
| Separate scoped qualification admission | Authorizes named campaigns and environments while keeping operational admission dependent on exact-tuple evidence. |
| Use ordinary admission with a broad bypass flag | Is convenient but risks turning a temporary testing exception into unrestricted operational authority. |
| Require qualification before any lab effect | Creates a circular dependency unless an external qualification mechanism supplies the required evidence. |

## Consequences

- Every campaign binds actor, environment, tuple, operation scope, expiry and reviewer authority.
- Evidence completion and operational acceptance are distinct; only reviewed eligible evidence can satisfy operational admission.

## Unresolved details and evidence needed

- Define campaign authority, worker identity separation, allowed resources and cleanup ownership.
- Specify tuple matching, evidence expiry, revocation and how failed or partial campaigns affect admission.

## Acceptance and validation

- Define authority boundaries and campaign scope in P00.04.
- Finalize admission and fencing before P06.01 and exercise negative tests at G06.
- Verify that lab-only evidence, expired approvals and mismatched tuples cannot authorize operational writes.

Record actual reviewer identity, decision date and evidence references when review occurs. Record delivery and gate outcomes in the delivery register; updating this ADR does not complete a work package.

## Revisit conditions

A campaign requires broader authority, a new environment changes the trust boundary, or evidence matching/expiry rules change.

## Related records

- [Decision register](decision-register.md) — authority for disposition, origin and blocking checkpoint.
- [Phased implementation plan](../implementation/phased-plan.md) — package and gate sequence.
- [ADR authoring template](../templates/adr.md) — required decision-record fields.
