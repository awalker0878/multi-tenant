# ADR-021 — Retained data and import boundary

Owner role: Product/records owners. Related phases: P00, P10, P11. Record date: 2026-10-04.

Origin: `DESIGN`. Disposition: `OPEN` as recorded in the [decision register](decision-register.md).

This record develops the existing baseline for review. No accountable-owner acceptance, experiment result or native qualification is claimed; the register disposition is unchanged.

## Context

The greenfield reset establishes a fresh product implementation, but retention obligations and useful historical data require a separate decision. Clean product data is the default proposal. Any archive or import must preserve provenance without inheriting active workflow authority, stale approvals or historical completion claims.

## Decision and scope

Clean product data by default; identify any required archive/import without inheriting active workflow authority.

Initial checkpoint: PROVISIONAL: P00.01/P00.05 decides whether retained data exists.

Refinement and validation: If applicable, import/reconcile procedure before P10.05; final disposition before P11.05; reviewed non-applicability otherwise.

## Options and trade-offs

| Option | Assessment |
| --- | --- |
| Clean product data with explicitly retained external archives | Keeps the initial model clean while requiring an accountable records decision and usable retrieval path. |
| Reviewed selective import of required business records | Can preserve necessary history but requires mapping, validation, reconciliation and clear inactive authority semantics. |
| Bulk restoration of previous application state | Carries incompatible schemas and workflow authority risks and requires explicit justification rather than being treated as migration convenience. |

## Consequences

- Imported records retain source identifiers/provenance and must not automatically become current inventory, approved plans or qualified support evidence.
- Retention, deletion and archive accessibility belong to accountable product/records owners, not a developer cleanup choice.

## Unresolved details and evidence needed

- Determine whether retained records exist, who owns them and which obligations govern their retention.
- If needed, define field mappings, rejection handling, reconciliation and a controlled import cutover.

## Acceptance and validation

- Record the retention/import applicability decision in P00.01/P00.05.
- Rehearse any applicable import and reconciliation before P10.05.
- Resolve final disposition before P11.05, or document reviewed non-applicability without claiming an import test occurred.

Record actual reviewer identity, decision date and evidence references when review occurs. Record delivery and gate outcomes in the delivery register; updating this ADR does not complete a work package.

## Revisit conditions

An authoritative retention requirement emerges, required records are found, or source quality prevents the accepted import/reconciliation approach.

## Related records

- [Decision register](decision-register.md) — authority for disposition, origin and blocking checkpoint.
- [Phased implementation plan](../implementation/phased-plan.md) — package and gate sequence.
- [ADR authoring template](../templates/adr.md) — required decision-record fields.
