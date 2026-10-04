# Operating the portable hosting service

These documents define deployment, trust, support and operating procedures for the portable hosting control plane and its scoped site workers. Implementation and actual exercise results are tracked in the [delivery register](../implementation/delivery-register.yaml); document existence supplies no installation, native qualification or operational acceptance evidence.

Start with the [deployment model](deployment-model.md) for placement and D01–D09 sequencing, then use the task-specific procedures below. The [support matrix](../implementation/support-matrix.md) separates intended combinations from supported scope; [requirements and qualification](../implementation/requirements-and-qualification.md) defines evidence obligations.

## Operating specifications

| Document | Owns | Accountable role |
| --- | --- | --- |
| [Deployment model](deployment-model.md) | Placement, environment ladder, logical network flows, dependency/recovery architecture | SRE/architecture |
| [Configuration and BOM](configuration-and-bom.md) | Artifact/environment identities, typed configuration, component/dependency inventory and change rules | SRE/delivery |
| [Identity and trust](identity-and-trust.md) | Human/service/worker identity, delegation, bootstrap, rotation, revocation and trust recovery | IAM/security |
| [Threat model](threat-model.md) | Assets, trust-boundary threats, required controls, abuse tests and finding lifecycle | Security architecture |
| [Observability](observability.md) | Correlated signals, freshness/unknown state, indicators, alert payloads/routing and collection failure | SRE/context owners |
| [Support](support.md) | Service boundary, incident responsibility, escalation, communications and operational handover | Service owner |
| [Operating targets](../product/operating-targets.md) | Objective ownership, workload/measurement inputs and accepted-target process | Product/SRE |

## Task procedures

The [runbook index](runbooks/README.md) defines common execution records, evidence and maintenance rules.

| Task | Procedure |
| --- | --- |
| Create a clean environment and establish read-only acceptance | [Install](runbooks/install.md) |
| Verify and transfer an immutable artifact set | [Promote release](runbooks/promote-release.md) |
| Roll out compatible application/dependency/worker versions | [Upgrade](runbooks/upgrade.md) |
| Reverse a failed deployment within its actual compatibility limits | [Rollback deployment](runbooks/rollback-deployment.md) |
| Restore or fail over required stateful/trust services | [Dependency recovery](runbooks/dependency-recovery.md) |
| Restore control-plane state in an isolated environment | [Restore control plane](runbooks/restore-control-plane.md) |
| Reconcile native/data/authority state and resume safely | [Recovery](runbooks/recovery.md) |
| Establish site/worker discovery and native-readiness scope | [Commissioning](runbooks/commissioning.md) |
| Diagnose a signal, contain impact and route an incident | [Handle alert](runbooks/handle-alert.md) |

## Environment records and executable bindings

Real endpoint names, tenant identities, credential references, native resource inventories, network approvals, contacts and production evidence belong in approved restricted operating systems. Repository examples use synthetic identifiers. Preserve only authorized non-sensitive record references in source and change descriptions.

The procedures name actions, owners, required inputs, expected observations, stop/recovery decisions and evidence. Each implementation supplies the release-specific command/API bindings and an actual exercise record before the procedure supports operational acceptance. Do not invent a command or assume a service is installed because a procedure describes its required behavior.

Runtime manifests, schemas and locks belong under `deploy/` as implementation delivers them. Test/campaign code belongs in its owning test area; raw evidence belongs in the approved evidence store. Link those outputs from their work package and procedure without duplicating execution status here.

## Change and acceptance

When deployment topology, identity, configuration, persistence, native scope or operator-visible behavior changes, update its operating specification and affected procedure in the same delivery. SRE reviews runtime changes; security reviews trust/data boundaries; lifecycle and application owners review mutation and data recovery. Qualification reviewers assess actual evidence independently of its producers.

Each exercise records exact artifacts/configuration, operator/reviewer, starting state, action observations, elapsed time, failures/limits and evidence references. An independent operator exercises release-critical install/recovery tasks before P11 acceptance. Historical evidence remains immutable; new versions require explicit impact analysis and any affected reruns.

Use a separate task runbook when a behavior introduces a distinct operator trigger, authority boundary or recovery outcome. Link common trust, upgrade and recovery rules instead of copying them. Future procedures for migration cutover, uncertain operations, rotation or retirement belong with the package that implements those behaviors and must be available before their native enablement.
