# ADR-020 — Restricted-network and disconnection behavior

Owner role: SRE/security leads. Related phases: P00, P01, P06. Record date: 2026-10-04.

Origin: `DESIGN`. Disposition: `OPEN` as recorded in the [decision register](decision-register.md).

This record develops the existing baseline for review. No accountable-owner acceptance, experiment result or native qualification is claimed; the register disposition is unchanged.

## Context

Deployment may depend on restricted network access and remote workers that disconnect from central services. Installation artifacts, update metadata and authority renewal cannot silently assume public connectivity. Required deployment modes and permitted continuation behavior remain open.

## Decision and scope

Restricted-network artifacts/mirrors, site disconnection and permitted continuation.

Initial checkpoint: PROVISIONAL: P00.03/P00.05 selects required deployment modes before P01.02/P01.04.

Refinement and validation: Site authority expiry before P06.03; restricted install/restore qualification at G10.

## Options and trade-offs

| Option | Assessment |
| --- | --- |
| Controlled mirrors and explicitly bounded offline execution | Supports a restricted environment while making artifact provenance, freshness and authority expiry visible. |
| Fully connected installation and continuous central authorization | Simplifies artifact and policy distribution but only fits environments where those dependencies are accepted. |
| Unbounded local execution during disconnection | Maintains progress but can exceed revoked or expired authority and cannot be the implicit failure behavior. |

## Consequences

- Each dependency declares its installation and runtime network requirements and its approved source/mirror.
- Worker behavior distinguishes safe local observation, already-started effects and new effects requiring renewed authority.

## Unresolved details and evidence needed

- Select required deployment modes, artifact transfer controls, signing/trust verification and update freshness policy.
- Define disconnection detection, local durable state, authority expiry and reconnection reconciliation.

## Acceptance and validation

- Resolve deployment mode constraints before P01.02/P01.04.
- Test disconnection and authority expiry around external effects before P06.03.
- Rehearse restricted-network installation, update and recovery at G10 using approved artifacts.

Record actual reviewer identity, decision date and evidence references when review occurs. Record delivery and gate outcomes in the delivery register; updating this ADR does not complete a work package.

## Revisit conditions

An environment changes connectivity policy, artifact custody changes, or permitted continuation cannot meet revocation and recovery requirements.

## Related records

- [Decision register](decision-register.md) — authority for disposition, origin and blocking checkpoint.
- [Phased implementation plan](../implementation/phased-plan.md) — package and gate sequence.
- [ADR authoring template](../templates/adr.md) — required decision-record fields.
