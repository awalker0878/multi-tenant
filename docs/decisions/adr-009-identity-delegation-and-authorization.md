# ADR-009 — Identity, delegation and authorization

Owner role: IAM/security leads. Related phases: P00, P01, P02, P06. Record date: 2026-10-04.

Origin: `DESIGN`. Disposition: `OPEN` as recorded in the [decision register](decision-register.md).

This record develops the existing baseline for review. No accountable-owner acceptance, experiment result or native qualification is claimed; the register disposition is unchanged.

## Context

The product must distinguish a browser user, a service principal, an approving authority and a worker acting on a specific operation. Enterprise OIDC is the integration direction, while provider, tenant claims, delegation, revocation and break-glass semantics remain open. Authentication alone cannot authorize a native effect.

## Decision and scope

Enterprise OIDC, service identities, delegation, revocation, approval and break-glass.

Initial checkpoint: PROVISIONAL: P00.03 provider and trust prerequisites before P01.06.

Refinement and validation: Final identity/authorization semantics before P02.01–P02.04; immediate pre-effect rechecks before P06.03.

## Options and trade-offs

| Option | Assessment |
| --- | --- |
| Enterprise OIDC with product-owned scoped authorization | Uses an enterprise login authority while recording domain roles, approvals and operation constraints in governance. |
| Rely entirely on identity-provider groups for operation decisions | Reduces one policy layer but must still represent resource scope, approval binding and immediate revocation checks. |
| Separate product user directory | Adds identity lifecycle and credential custody responsibilities and needs explicit justification against enterprise integration requirements. |

## Consequences

- Services validate identity and enforce their own owned resource boundary; the console is not a universal authorization bypass.
- Delegated worker authority must bind tenant, site, operation, plan revision and expiry, with rechecks before effects.

## Unresolved details and evidence needed

- Confirm issuer/trust configuration, claim mapping, service identity issuance and revocation propagation.
- Specify separation of duties, approval expiry, emergency access and auditable recovery from identity outages.

## Acceptance and validation

- Exercise wrong-tenant, expired, revoked and changed-role requests before P02 acceptance.
- Verify approvals cannot be reused for a different plan or actor scope.
- Recheck authority immediately before native effects, including queued work admitted before revocation.

Record actual reviewer identity, decision date and evidence references when review occurs. Record delivery and gate outcomes in the delivery register; updating this ADR does not complete a work package.

## Revisit conditions

The identity provider or trust model changes, required revocation timing cannot be met, or a new administrative delegation path is introduced.

## Related records

- [Decision register](decision-register.md) — authority for disposition, origin and blocking checkpoint.
- [Phased implementation plan](../implementation/phased-plan.md) — package and gate sequence.
- [ADR authoring template](../templates/adr.md) — required decision-record fields.
