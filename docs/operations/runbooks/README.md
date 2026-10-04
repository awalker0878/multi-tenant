# Operating procedures

Owner: SRE with the domain and native resource owners named in each procedure. Apply a procedure only to the release, configuration, environment and operation scope for which its supporting exercise evidence is current. The [deployment model](../deployment-model.md) defines architecture and sequencing; these pages define operator actions and decision points.

## Select a procedure

| Task | Procedure | Principal owner |
| --- | --- | --- |
| Install a clean environment through read-only acceptance | [Install](install.md) | SRE |
| Verify and promote an immutable release into an environment | [Promote release](promote-release.md) | Delivery/SRE |
| Change application, dependency or worker versions safely | [Upgrade](upgrade.md) | Delivery/SRE/lifecycle |
| Recover a failed deployment when compatible reversal exists | [Rollback deployment](rollback-deployment.md) | SRE/service owner |
| Recover persistent dependencies while retaining consistency | [Dependency recovery](dependency-recovery.md) | Persistence owner/SRE |
| Restore the control plane in isolated recovery | [Restore control plane](restore-control-plane.md) | SRE/lifecycle |
| Reconcile recovered control/native/application state and resume | [Recovery](recovery.md) | Lifecycle/SRE/application owner |
| Commission a site and its constrained worker pools | [Commissioning](commissioning.md) | Inventory/platform owner |
| Diagnose an alert, contain impact and route an incident | [Handle alert](handle-alert.md) | Receiving responder/incident lead |

The task-specific recovery procedures use the common reconciliation and no-duplicate-write rules in [recovery](recovery.md). Do not duplicate those rules into a local shortcut. Use [support](../support.md) for ownership/escalation and [observability](../observability.md) for signal definitions.

## Execution record

Every execution records procedure revision, incident/change/campaign ID, operator, reviewer where required, environment/release/configuration identities, affected tenant/site/job/resource scope, starting state, required authority and evidence locations. Capture each action's time, expected observation, actual result and decision. Redact credentials and sensitive native details in repository-visible references.

Release-specific command bindings identify the selected runtime/API version and exact argument sources from controlled configuration. Validate those bindings in the relevant environment before use. A named action in these procedures does not imply that a CLI or endpoint already implements it; implementation adds executable bindings and actual exercise references in the same delivery as the behavior.

## Common execution rules

1. Read current authority, artifact/configuration and state evidence before mutation. Resolve an unknown prerequisite explicitly; do not infer it from a previous run.
2. Apply scoped admission holds and verified fencing before disruptive recovery or incompatible changes. Preserve observation access and already-dispatched operation records.
3. Use stable request/operation identities for retries. A lost response becomes a reconciliation task until the authoritative result is known.
4. Observe actual native and application state independently. Workflow completion, healthy pods or an API success code alone cannot establish the business postcondition.
5. Preserve retained source/target data, encryption keys and evidence until their separate retention/disposal authority permits release.
6. Stop at missing trust, failed integrity, unknown writer, incompatible schema/history, unavailable recovery key or unresolvable operation outcome. Record the hold and escalate to the owner rather than broadening authority.

Timeouts and recovery objectives come from the accepted [operating targets](../../product/operating-targets.md) and environment record. At expiry, record uncertainty and escalate; a timeout never proves an external effect was cancelled. Recovery time measurement includes reconciliation and validation, not just process startup.

## Evidence and maintenance

Procedure acceptance requires exact artifact/configuration identities, initiating conditions, independent observations, measured durations, operator/reviewer references, failures/limits and resulting support scope. Store actual runs through assurance and reference them from the delivery register. The presence of this document does not supply an execution result.

Update the procedure when its behavior, dependency, API, authority, configuration or recovery boundary changes. Assess which prior exercises remain applicable and rerun affected cases. Keep historical evidence immutable and maintain current command bindings with the supported release.
