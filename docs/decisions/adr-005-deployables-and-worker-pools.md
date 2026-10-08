# ADR-005 — Deployables and worker pools

Owner role: Architecture/SRE leads. Related phases: P00, P01, P10. Record date: 2026-10-04.

Origin: `DESIGN`. Disposition: `ACCEPTED` for the P01 development baseline as recorded in the [decision register](decision-register.md).

Reviewer: the requesting user, accountable G00 reviewer. Decision time: `2026-10-04T17:23:57-04:00`. The [G00 decision](../qualification/gate-reviews/g00-user-decision-2026-10-04.md) accepts the seven-deployable and scoped-worker model for P01. Independent builds, actual deployment and worker authorization still require implementation evidence.

## Context

Service boundaries need a concrete build and deployment model. The accepted baseline keeps seven principal deployables and separately scoped worker pools in one repository. Repository colocation must not require simultaneous rollout or grant a site worker central administrative reach.

## Decision and scope

Seven principal deployables — Console, Governance, Catalogue, Inventory, Planning, Lifecycle and Assurance — plus independently scoped Inventory/Lifecycle worker pools in one repository. Keep service-private source, locks, images, data and identities. Actual runtime topology, operated providers and deployment scope remain separate P01 inputs.

Initial checkpoint: P00.03 deployable model accepted by the recorded G00 decision before P01.01/P01.02.

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

- Implement the accepted image and ownership boundaries; determine the actual site-local worker placements from their trust and operation scope.
- Choose release manifest composition and the supported independent version compatibility window.

## Acceptance and validation

- Build and deploy one service without rebuilding or redeploying unrelated services at G01.
- Verify that a worker cannot claim work outside its assigned identity and scope.
- Measure deployment and operating overhead and reassess the decomposition at P10.

The reviewer and decision reference are recorded above. Record implementation and gate outcomes in the delivery register; accepting this ADR does not complete a work package.

## Revisit conditions

The service count prevents an operable deployment, a trust boundary requires stronger isolation, or shared package coupling prevents independent release.

## Related records

- [Decision register](decision-register.md) — authority for disposition, origin and blocking checkpoint.
- [Phased implementation plan](../implementation/phased-plan.md) — package and gate sequence.
- [ADR authoring template](../templates/adr.md) — required decision-record fields.
