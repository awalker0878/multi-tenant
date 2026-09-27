# ADR-0039 — Build an enterprise workload mobility product

**Status:** Proposed<br>
**Decision class:** New product direction; organizational adoption pending<br>
**Date:** 2026-09-26<br>
**Accountable role:** Product and architecture owners; named organizational acceptance is pending<br>
**Scope:** Future product behavior across qualified on-premises environments; no site or platform authorization is implied<br>
**Basis:** [Enterprise workload mobility audit and implementation plan](../product/enterprise-workload-mobility-audit-and-implementation-plan.md) at `e5347986cb736df525c1fc3ace100af26d2d4f27`, [portable provisioning interface](../provisioning/README.md), [automation delivery program](../implementation/automation/README.md) and [ADR-0013](0013-compose-provisioning-across-separate-platform-and-service-authorities.md)

## Context

The repository has validated WSD intent, planning, placement, candidate Terraform/Ansible realization, native owner tools and assurance gates. Its public `apply` and `mobility-apply` commands refuse execution. A sysadmin cannot discover an existing application, compare on-premises destinations, provision its prerequisites, migrate it and verify useful service through one authorized product path. The existing infrastructure architecture remains the basis for security, site topology and service ownership.

## Decision

Build one enterprise application with a workload portfolio, read-only discovery, destination assessments, immutable plans, authenticated approvals, durable provisioning and migration jobs, evidence and recovery. Provide a web console and a thin API-based CLI for sysadmins. The product must answer what can move, to which installed destination, by which qualified method, with what remediation, capacity, policy, data, downtime and recovery implications.

Run control services in an approved management environment. Use site-local workers and data movers for native changes and workload bytes. Keep Terraform and Ansible as declarative realization and guest configuration engines behind typed workflow activities. Use one durable execution authority and one canonical request/plan contract. A specific workflow engine is a later technical decision, subject to a restart/replay and restricted-network spike.

Allow assessment when facts are incomplete, but display unknowns and block execution that depends on them. A route is directional and bound to installed source and destination tuples, method, guest/data/network profile and current native qualification. Same-family moves between sites or clusters are in scope. An unqualified extension is shown as unsupported or assessment-only.

## Alternatives considered

- Retaining a repository-only handoff boundary would leave the requested provisioning and migration job to an external unimplemented system.
- Exposing the current local runner directly as a multiuser API would give local journals and recorded approval strings authority they do not possess.
- Building one generic platform mover would obscure directed capabilities, native identity, data consistency and recovery limitations.

These are new product choices, not historical infrastructure decisions. Native platform, shared-service and security authorities remain separate under [ADR-0013](0013-compose-provisioning-across-separate-platform-and-service-authorities.md).

## Consequences and delivery obligations

- Implement enterprise identity, scope-bound approvals, separation of duties and grant revocation before privileged execution.
- Bind plans to observed source identities, current policy/capacity/qualification, exact code and driver versions, and a server-held revision.
- Add read-only discovery and explainable comparison before offering an executable migration plan.
- Implement native postcondition checks, data integrity, source writer exclusion, traffic cutover, application acceptance and held-outcome reconciliation.
- Keep quarantine, saved Terraform plan binding, one native writer per owned object/field, fail-closed qualification and retained-data protection.
- Publish a capability ledger distinguishing contract, local test, native qualification and operational release state for every route and action.

## Acceptance

Product engineering may implement this proposed direction. A production release requires a named adopting authority, independently protected approval and native evidence for each advertised tuple and route. The current repository does not provide that release evidence. See [remaining work](../NEXT_WORK.md).

[Decision register](README.md)
