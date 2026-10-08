# ADR-022 — Release support and requalification

Owner role: Product/service owners. Related phases: P00, P09, P10. Record date: 2026-10-04.

Origin: `DESIGN`. Disposition: `OPEN` as recorded in the [decision register](decision-register.md).

This record develops the existing baseline for review. No accountable-owner acceptance, experiment result or native qualification is claimed; the register disposition is unchanged.

## Context

A first release must distinguish intended platform breadth from combinations that have been qualified and can be operated. Expansion tranche, support owners, tuple expiry and requalification rules remain open. A working adapter or passing simulation cannot establish an unrestricted support claim.

## Decision and scope

First-release expansion tranche, support owners, tuple expiry and requalification rules.

Initial checkpoint: PROVISIONAL: P00.01 lists included/excluded routes and expiry-policy owner.

Refinement and validation: Final tranche before P09 qualification; release freeze P10.06; publish exact support G11.

## Options and trade-offs

| Option | Assessment |
| --- | --- |
| Release manifest with exact qualified support tuples | Binds each supported route and method to evidence, known limits and an accountable operating owner. |
| Broad support labels for whole platforms | Is simpler to advertise but conceals version, backend, guest and operation-specific limitations. |
| Experimental integrations alongside qualified scope | Can enable controlled learning only when admission, documentation and operator expectations clearly preserve their separate status. |

## Consequences

- Support records identify operation, direction, method, versions, guest and integration dependencies, evidence expiry and limitations.
- Changes to code, provider behavior or environment must trigger an impact review before carrying qualification into a new release.

## Unresolved details and evidence needed

- Select the first P09 expansion tranche and confirm service owners for every included combination.
- Define expiry/requalification triggers, emergency withdrawal, deprecation and the release freeze process.

## Acceptance and validation

- List included and excluded routes and an expiry-policy owner in P00.01.
- Review expansion scope before P09 qualification and freeze the proposed release at P10.06.
- At G11 publish only exact supported combinations with current evidence and accepted operating ownership.

Record actual reviewer identity, decision date and evidence references when review occurs. Record delivery and gate outcomes in the delivery register; updating this ADR does not complete a work package.

## Revisit conditions

A supported tuple changes, evidence expires or is invalidated, an incident exposes an unmet acceptance condition, or the release scope expands.

## Related records

- [Decision register](decision-register.md) — authority for disposition, origin and blocking checkpoint.
- [Phased implementation plan](../implementation/phased-plan.md) — package and gate sequence.
- [ADR authoring template](../templates/adr.md) — required decision-record fields.
