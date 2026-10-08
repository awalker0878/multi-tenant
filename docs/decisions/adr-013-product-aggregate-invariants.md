# ADR-013 — Product aggregate invariants

Owner role: Product/architecture leads. Related phases: P00, P03, P05. Record date: 2026-10-04.

Origin: `DESIGN`. Disposition: `ACCEPTED` for the initial Catalogue development baseline as recorded in the [decision register](decision-register.md).

The requesting user accepted the initial DC03 development choices through the [2026-10-04 G00 decision](../qualification/gate-reviews/g00-user-decision-2026-10-04.md). This scoped update records that existing acceptance; it is not a new approval or native qualification. P03 implements and verifies these Catalogue rules. Native placement refinements remain due before P05.02.

## Context

Tenant, WSD, SecurityDomain, DomainInstance, Application and Workload describe different business and placement responsibilities. Ambiguous cardinalities would create inconsistent APIs, authorization and deletion behavior. The domain model separates the accepted logical Catalogue baseline from later managed/native realization details.

## Decision and scope

Tenant/WSD/SecurityDomain/DomainInstance/Application/Workload cardinalities and sharing/deletion rules.

Initial checkpoint: NOW: P00.02 / G00.02 baseline invariants.

Refinement and validation: Aggregate constraints before P03.01; real placement semantics before P05.02.

## Options and trade-offs

| Option | Assessment |
| --- | --- |
| Explicit aggregates with owned invariants and references | Keeps business identity separate from placement and makes authorization and lifecycle constraints reviewable. |
| Single deployment object containing all concepts | Reduces initial entities but conflates tenant policy, application identity and native realization. |
| Mirror native platform inventory directly | Simplifies discovery mapping but makes the product model depend on provider structure and weakens portable intent. |

## Consequences

- Catalogue owns desired application structure; inventory observations and native identifiers remain separately sourced facts.
- Cross-aggregate deletion and sharing need an explicit lifecycle protocol rather than implicit cascading writes across services.

## Accepted initial Catalogue rules

- One owning tenant for applications and reference definitions; one application owns each stable workload identity.
- One deployment identity per application/environment. A workload placement selects exactly one same-tenant WSD and logical security domain; an application may span several of each.
- WSD/domain reuse across applications requires explicit sharing. Ordinary NICs cannot cross their placement domain. Controlled interfaces are dependency intent; ZIP is never a workload placement zone.
- Publish complete immutable snapshots with explicit device order, requirement strength, data/service ownership and recovery intent. Startup/shutdown order graphs are checked independently from possibly bidirectional communication.
- The strong application ETag serializes all deployment streams. Tenant/actor command receipts bind action, payload and expected revision; current authority is checked before returning a receipt.
- Reference versions remain immutable. Names/zones cannot be reassigned; retirement cannot invalidate a current deployment. Historical references remain retained.

## Remaining refinement

Native DomainInstance/ManagedDomainBinding realization, cross-domain appliance exceptions, cross-tenant shared routing, cross-application dependency attachments and any regional deployment-key extension require their own scoped design and qualification. None is enabled implicitly by P03. The accepted baseline does not establish native placement semantics or receiving acceptance.

## Acceptance and validation

- Review valid and invalid model examples at G00.02.
- Verify owned aggregate constraints before P03.01 and reject ambiguous tenant ownership.
- Validate the model against real placement cases before P05.02.

Record actual reviewer identity, decision date and evidence references when review occurs. Record delivery and gate outcomes in the delivery register; updating this ADR does not complete a work package.

## Revisit conditions

A required application or site topology cannot be represented without breaking an invariant, or a proposed sharing rule changes the authorization boundary.

## Related records

- [Decision register](decision-register.md) — authority for disposition, origin and blocking checkpoint.
- [Phased implementation plan](../implementation/phased-plan.md) — package and gate sequence.
- [ADR authoring template](../templates/adr.md) — required decision-record fields.

## P00 domain review

The [P00.02 domain review](../implementation/p00-domain-review.md) now provides concrete valid/invalid cases, command/event concurrency and one-writer assignments, including logical datasets, observed native identity, managed workload bindings and reservation journals. These examples informed the accepted G00/DC03 development baseline. They do not import the historical schema, authorize native effects or replace later architecture/service/security receiving review.
