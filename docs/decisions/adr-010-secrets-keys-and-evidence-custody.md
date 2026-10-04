# ADR-010 — Secrets, keys and evidence custody

Owner role: Security/SRE leads. Related phases: P00, P01, P06. Record date: 2026-10-04.

Origin: `DESIGN`. Disposition: `OPEN` as recorded in the [decision register](decision-register.md).

This record develops the existing baseline for review. No accountable-owner acceptance, experiment result or native qualification is claimed; the register disposition is unchanged.

## Context

Workers require controlled native credentials and assurance requires protected evidence objects. A single storage API does not define key custody, immutable retention, trust bootstrap or disaster recovery. The initial secret/key services, PKI and S3-compatible evidence store remain open choices.

## Decision and scope

Secret/key services, PKI/trust bootstrap and protected S3-compatible evidence store.

Initial checkpoint: NOW: P00.03 initial services/custody before P01.05/P01.06.

Refinement and validation: Immutable evidence/retention/finalization before P06.04; key-loss/restore at G10.

## Options and trade-offs

| Option | Assessment |
| --- | --- |
| Operated enterprise secret/key and object services | May align ownership with existing capabilities; validate interfaces, access policy and recovery rather than assuming availability. |
| Dedicated services operated with the product | Provides explicit product control but adds security, availability, patching and key-recovery responsibilities. |
| Configuration-embedded credentials and ordinary writable object storage | Does not satisfy the proposed custody and protected-evidence model; cannot be used as an implicit fallback. |

## Consequences

- Repository and operation records store secret references and approved evidence references, not credentials or raw sensitive evidence.
- Evidence finalization must bind object identity, digest, authorization and retention policy; object presence alone is not verified evidence.

## Unresolved details and evidence needed

- Choose services, custody owners, trust bootstrap, rotation/revocation and break-glass recovery.
- Define retention/deletion authority, integrity verification, time sources and behavior during secret or evidence service outages.

## Acceptance and validation

- Demonstrate scoped secret retrieval and denied cross-tenant or cross-site access.
- Verify finalized evidence cannot be silently replaced and incomplete uploads cannot appear accepted.
- Rehearse key-loss, rotation, object restore and integrity reconciliation at G10.

Record actual reviewer identity, decision date and evidence references when review occurs. Record delivery and gate outcomes in the delivery register; updating this ADR does not complete a work package.

## Revisit conditions

Custody ownership, required retention controls, encryption policy or recovery guarantees change.

## Related records

- [Decision register](decision-register.md) — authority for disposition, origin and blocking checkpoint.
- [Phased implementation plan](../implementation/phased-plan.md) — package and gate sequence.
- [ADR authoring template](../templates/adr.md) — required decision-record fields.
