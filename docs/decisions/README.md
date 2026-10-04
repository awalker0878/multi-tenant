# Architecture decision records

The [decision register](decision-register.md) is the authority for origin, disposition, owner role and blocking checkpoint. These records explain the choices, trade-offs, consequences and required validation. ADR-001 and ADR-002 retain the explicit accepted user directions; all other dispositions remain as recorded in the register.

A decision record is not implementation evidence. Update an ADR and the register together when an accountable review changes a decision. Preserve a superseded record and link its replacement.

## Records

| Record | Question it owns |
| --- | --- |
| [ADR-001](adr-001-greenfield-product-reset.md) | Greenfield product reset |
| [ADR-002](adr-002-requested-application-stack.md) | Requested application stack |
| [ADR-003](adr-003-runtime-and-dependency-baseline.md) | Runtime and dependency baseline |
| [ADR-004](adr-004-service-context-boundaries.md) | Service context boundaries |
| [ADR-005](adr-005-deployables-and-worker-pools.md) | Deployables and worker pools |
| [ADR-006](adr-006-service-owned-persistence.md) | Service-owned persistence |
| [ADR-007](adr-007-durable-workflow-engine.md) | Durable workflow engine |
| [ADR-008](adr-008-domain-event-transport.md) | Domain event transport |
| [ADR-009](adr-009-identity-delegation-and-authorization.md) | Identity, delegation and authorization |
| [ADR-010](adr-010-secrets-keys-and-evidence-custody.md) | Secrets, keys and evidence custody |
| [ADR-011](adr-011-kubernetes-topology-and-site-workers.md) | Kubernetes topology and site workers |
| [ADR-012](adr-012-contracts-and-event-evolution.md) | Contracts and event evolution |
| [ADR-013](adr-013-product-aggregate-invariants.md) | Product aggregate invariants |
| [ADR-014](adr-014-first-native-provisioning-and-migration-slice.md) | First native provisioning and migration slice |
| [ADR-015](adr-015-platform-and-enterprise-integration-tuples.md) | Platform and enterprise integration tuples |
| [ADR-016](adr-016-terraform-plans-and-resource-ownership.md) | Terraform plans and resource ownership |
| [ADR-017](adr-017-service-and-application-objectives.md) | Service and application objectives |
| [ADR-018](adr-018-qualification-lane-and-operational-admission.md) | Qualification lane and operational admission |
| [ADR-019](adr-019-console-rendering-and-session-model.md) | Console rendering and session model |
| [ADR-020](adr-020-restricted-network-and-disconnection-behavior.md) | Restricted-network and disconnection behavior |
| [ADR-021](adr-021-retained-data-and-import-boundary.md) | Retained data and import boundary |
| [ADR-022](adr-022-release-support-and-requalification.md) | Release support and requalification |

## Review and maintenance

1. Confirm the affected product requirement, service boundary, work package and latest safe checkpoint.
2. Compare options using the same criteria and identify missing evidence rather than assuming a successful experiment.
3. Record the selected scope, assumptions, actual reviewer and decision date; distinguish a directed constraint from unresolved implementation details.
4. Update affected service, contract, deployment and support documents in the same change.
5. Record verification and qualification results in the delivery register and retain references here when they support the decision.

Use the [ADR template](../templates/adr.md) and [documentation guide](../documentation-guide.md) when adding a decision. Never recycle an ADR ID or treat a document’s existence as a passed gate.
