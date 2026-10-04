# ADR-005 — Deployables and worker pools

Owner role: Architecture/SRE leads. Related phases: P00, P01, P10. Record date: 2026-10-04.

Origin: `DESIGN`. Disposition: `PROPOSED` as recorded in the [decision register](decision-register.md).

This record develops the existing baseline for review. No accountable-owner acceptance, experiment result or native qualification is claimed; the register disposition is unchanged.

## Context

Service boundaries need a concrete build and deployment model. The proposed baseline keeps seven principal deployables and separately scoped worker pools in one repository. Repository colocation must not require simultaneous rollout or grant a site worker central administrative reach.

## Decision and scope

Seven principal deployables plus independently scoped worker pools in one repository.

Initial checkpoint: NOW: P00.03 before P01.01/P01.02.

Refinement and validation: Independently build/deploy proof at G01; reassess operational cost at P10.

## Options and trade-offs

| Option | Assessment |
| --- | --- |
| Monorepository with independent deployables and workers | Shares review and contract tooling while keeping build, release, scaling and identity boundaries explicit. |
| Separate repositories per service | Strengthens repository ownership but introduces cross-repository contract and release coordination. |
| Single combined application deployment | Reduces initial deployment units but couples scaling, fault isolation and rollout of the proposed contexts. |

## Consequences

- Each deployable needs its own image, runtime identity, health checks and configuration contract.
- Worker pool assignment follows site, operation and trust scope; queue routing is not by itself authorization.

## Unresolved details and evidence needed

- Define image boundaries, shared package rules and which workers require site-local deployment.
- Choose release manifest composition and the supported independent version compatibility window.

## Acceptance and validation

- Build and deploy one service without rebuilding or redeploying unrelated services at G01.
- Verify that a worker cannot claim work outside its assigned identity and scope.
- Measure deployment and operating overhead and reassess the decomposition at P10.

Record actual reviewer identity, decision date and evidence references when review occurs. Record delivery and gate outcomes in the delivery register; updating this ADR does not complete a work package.

## Revisit conditions

The service count prevents an operable deployment, a trust boundary requires stronger isolation, or shared package coupling prevents independent release.

## Related records

- [Decision register](decision-register.md) — authority for disposition, origin and blocking checkpoint.
- [Phased implementation plan](../implementation/phased-plan.md) — package and gate sequence.
- [ADR authoring template](../templates/adr.md) — required decision-record fields.
