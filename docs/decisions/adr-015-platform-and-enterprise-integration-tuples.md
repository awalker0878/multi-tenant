# ADR-015 — Platform and enterprise integration tuples

Owner role: Platform/service owners. Related phases: P00, P04, P07, P09. Record date: 2026-10-04.

Origin: `DESIGN`. Disposition: `OPEN` as recorded in the [decision register](decision-register.md).

This record develops the existing baseline for review. No accountable-owner acceptance, experiment result or native qualification is claimed; the register disposition is unchanged.

## Context

Provider names are insufficient to establish compatibility. Each capability depends on installed platform and API versions, storage/network backends, guest profiles and enterprise service interfaces. Candidate tuples and input owners must be confirmed before read integrations and native effects are developed.

## Decision and scope

Exact platform/API/backend/network/guest and IPAM/DNS/identity/backup/monitoring interfaces.

Initial checkpoint: PROVISIONAL: P00.04 candidate tuple and confirmed input owners.

Refinement and validation: Read contracts/installed tuples before P04.02; each real integration before P07.03; expansion per P09 tranche.

## Options and trade-offs

| Option | Assessment |
| --- | --- |
| Explicit versioned integration tuples | Makes capability claims precise and allows qualification and expiry to bind to the actual installed combination. |
| Broad platform-level support claims | Simplifies communication but cannot identify backend, version or guest limitations and must not substitute for qualification. |
| Unconstrained plugin interfaces with user-provided adapters | May support extension later, but still requires interface ownership, permission review and evidence before native admission. |

## Consequences

- Profiles describe capabilities and limits; support is determined by exact qualified combinations and permitted operations.
- IPAM, DNS, identity, backup and monitoring integrations each need owners, contracts and failure/reconciliation behavior.

## Unresolved details and evidence needed

- Confirm actual installed versions, interface owners, credentials scope and approved test environments.
- Record tuple identifiers, API/backend dependencies, discovery freshness and integration-specific constraints.

## Acceptance and validation

- Validate read contracts and installed tuples before P04.02.
- Verify each real enterprise integration independently before P07.03 uses it.
- Create separate qualification scope for each P09 expansion tranche or changed tuple.

Record actual reviewer identity, decision date and evidence references when review occurs. Record delivery and gate outcomes in the delivery register; updating this ADR does not complete a work package.

## Revisit conditions

An installed component, interface version, permission model or backend changes, or new evidence invalidates a previously qualified capability.

## Related records

- [Decision register](decision-register.md) — authority for disposition, origin and blocking checkpoint.
- [Phased implementation plan](../implementation/phased-plan.md) — package and gate sequence.
- [ADR authoring template](../templates/adr.md) — required decision-record fields.
