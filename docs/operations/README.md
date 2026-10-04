# Operating the portable hosting service

**Status: candidate operating documentation.** The product has not been implemented, installed, native-qualified or accepted for operations. This directory describes the operating design to build and the records operators will need; it does not authorize a deployment.

Start with the [deployment model](deployment-model.md) for component placement, trust, dependencies, installation, recovery and upgrades. Use the [support matrix](../implementation/support-matrix.md) to distinguish intended scope from qualified capability, and the [requirements register](../implementation/requirements-and-qualification.md) for the obligations each operating procedure must satisfy. The [status model](../implementation/status-model.md) governs completion claims.

## Documentation to grow with implementation

| Future location | Contents and owner | First required delivery |
| --- | --- | --- |
| `docs/operations/runbooks/install.md` | SRE: executable clean-install procedure, validated dependency order, health checks and failure containment | P01 development/integration install; native prerequisites before P07 |
| `docs/operations/runbooks/upgrade.md` | Delivery/SRE: tested version compatibility, migrations, workflow routing and downgrade limits | P01 compatibility policy; each released upgrade; Q09 in P10 |
| `docs/operations/runbooks/recovery.md` | SRE/lifecycle: coordinated backup, isolated restore, native reconciliation and controlled resume | Design in P01; rehearsal before P07 writes; complete Q09 in P10 |
| `docs/operations/runbooks/commissioning.md` | Inventory/platform owners: site identity, credential scopes, flow checks and accepted resource/service readiness | Read-only in P04; mutation readiness before P07 |
| `docs/operations/runbooks/` | Owning service plus operations: task-specific diagnostic, containment and recovery procedures | With the corresponding behavior, before native enablement |
| `docs/operations/observability.md` | SRE/service owners: indicators, redacted telemetry, alert conditions, routing and exercised receipt | P01 baseline; before P07 actionable alerts |
| `docs/operations/support.md` | Service owner: responsibilities, incident triage, escalation roles, support hours and handover | Draft in P00/P01; accepted in P10/P11 |
| `deploy/` | SRE: versioned manifests, environment schemas, secret-reference definitions and dependency locks | P01; updated with changes |
| `tests/acceptance/` | Quality: executable campaign definitions and non-sensitive synthetic fixtures | With each associated work package |

Paths in this table are the planned structure, not a claim that these files exist. Split a runbook by an operator task or failure outcome, not by arbitrary document size. A service specification links to its operating procedures; it must not reproduce the same instructions.

Real endpoint names, tenant identities, credential references, native resource inventories, firewall approvals, contacts and production recovery evidence belong in approved restricted operational systems. Repository examples use synthetic identifiers. Documentation links to access-controlled records through non-sensitive record references only where policy permits; credentials and private evidence never belong in example files, commits or issue bodies.

## Runbook contract

Every runbook must include these fields before it can support operational acceptance:

| Field | Required detail |
| --- | --- |
| Identity | Stable runbook ID, owner role, service/workflow, revision and related R/Q/work-package IDs |
| Applicability | Supported release and platform tuple, environment, triggering symptoms and exclusions |
| Authority | Roles, approved scopes, required change/incident context and separation of duties |
| Preconditions | Required dependency health, evidence freshness, data retention, available keys and safe state |
| Diagnose | Read-only checks first, expected observations and ways to distinguish missing evidence from confirmed failure |
| Contain | Exact admission hold, fencing and isolation actions; what continues safely and what must stop |
| Execute | Ordered commands or API operations, exact inputs, idempotency behavior and expected outputs |
| Decision points | Conditions to proceed, retry, reconcile, compensate or escalate; named point of no return |
| Validate | Independent native and application observations establishing the postcondition |
| Recover | Partial-failure handling, target-write implications, reverse-operation limits and safe abort |
| Record | Redacted evidence receipt, correlation/job/operation identifiers, time and protected artifact references |
| Prove | Last exercise on exact artifacts/environment, result, reviewer, open limits and retest triggers |

A design-only runbook is labelled unexercised. Copying commands from a development environment does not qualify a production procedure. An operator other than its author must exercise release-critical installation and recovery procedures before P11 acceptance.

The first runbook backlog covers: lost native response; duplicate delivery; expired execution authority; disconnected site worker; failed evidence delivery; exhausted reservation; partially completed provisioning; failed activation; rejected/stale approval; migration before and after target writes; backup/restore; signing-key or certificate rotation; and mixed-version workflow upgrade. Each attaches to the owning work package rather than creating an independent completion list.

## Change and review rules

When a change modifies deployment topology, configuration, identity, persistence or operator-visible behavior, update the applicable procedure in the same delivery. Record required rehearsal changes alongside tests. SRE reviews runtime procedures; security reviews trust and credential changes; lifecycle and the application owner review mutation and data-recovery behavior. Qualification reviewers assess actual evidence independently of the authors.

Configuration examples, commands and manifest references must match the tested release. Keep immutable historical evidence in its approved store and publish a current evidence reference; never edit old evidence to describe a newer revision. A failed or stale rehearsal leaves the corresponding operational gate open.
