# Q09 — Deployment and recovery

Q09 verifies R02, R29–R32 and R35–R36. It supports P01.02/P01.04–P01.06 baseline checks and P10.02–P10.06 enterprise qualification. Relevant criteria are G01.02/G01.04–G01.06 and G10.01–G10.04; G11.03 requires receiving-operator use of the qualified procedures.

## Scope and ownership

SRE owns installation and coordinated recovery, security reviews trust/custody, and independent qualification observes the resulting state. E2 covers isolated integration exercises; E3/E4 cover representative preproduction/native outcomes and receiving-owner acceptance. An installed dashboard alone does not establish operational recovery.

Use the [deployment model](../../operations/deployment-model.md), [operations index](../../operations/README.md), [Q04 execution recovery](q04-durable-execution.md) and [status rules](../../implementation/status-model.md). Run targets and allowed outage/data loss must be approved before measuring pass/fail.

## Preparation

1. Pin signed release manifest, image/lock/SBOM digests, configuration and supported contract/workflow versions; verify approved artifact access and trust roots.
2. Inventory databases, Temporal state, broker/outbox/inbox, evidence/object store, automation state, secrets, identities/keys and independent backups.
3. Establish restore ordering, consistency points, key custody, isolated networking, read-only startup and write re-enable authority.
4. Select normal and restricted/disconnected installation scope as required by the approved deployment; record external dependency and mirror assumptions.
5. Seed synthetic application intent, active/held jobs, a known accepted native effect, immutable evidence and a measured recoverable dataset.

## Case matrix

| Case | Action or injected fault | Required observation | Evidence |
| --- | --- | --- | --- |
| Q09.01 | Install exact release into an empty isolated environment and seed fixtures | Required services authenticate and become healthy in the documented order without undeclared endpoints | Install manifest/logs, health/auth and endpoint observations |
| Q09.02 | Promote valid artifacts, then unsigned/mismatched images or evidence | Signature/digest policy accepts exact artifacts and rejects tampered or untrusted material | Provenance verification and negative admission results |
| Q09.03 | Exercise cross-database access, schema administration and invalid/revoked workload identity | Runtime roles remain service-scoped; migrations use controlled authority; revoked callers cannot regain access | Role/grant matrix and negative access observations |
| Q09.04 | Restore coordinated DB/workflow/evidence/automation state and keys into isolation | Digests/identities and selected recovery point reconcile; startup remains read-only | Backup/restore versions, integrity comparisons and mode checks |
| Q09.05 | Restore an older workflow snapshot while native accepted effects and old workers exist | Epochs, intent, journals and native results reconcile before approved write re-enable; no duplicate effects | Q04.08 timeline and independent native readback |
| Q09.06 | Lose a failure domain/site or identity/key/secrets dependency | Surviving service behavior and holds meet accepted targets; protected data remains recoverable with authorized keys | Fault/restore timings, availability and custody observations |
| Q09.07 | Perform rolling service/worker upgrade with active jobs, then present incompatible contracts | Version routing and expand/contract rules preserve history; incompatible consumers/workers are rejected | Mixed-version matrix, replay results and rejection evidence |
| Q09.08 | Interrupt deployment or require recovery across a schema boundary | Documented rollback or forward-recovery path succeeds within stated constraints; irreversible changes are not hidden | Deployment fault and recovery record |
| Q09.09 | Install through the approved restricted-network path; rotate trust/keys and inspect custody flows | Required dependencies are supplied and verified; no unapproved egress/access or key-location assumption | Artifact/egress observations, rotation and access review |
| Q09.10 | Export retained evidence and apply historical import/archive or reviewed non-applicability | Counts/digests/native IDs reconcile; originals persist; old writers freeze before any ownership transfer | Retention/export checks and R36 disposition review |

## Execution and observations

Baseline P01 runs exercise only their selected implemented foundation scope, with native writes disabled. They cannot claim completion of the P10 coordinated recovery or enterprise acceptance obligations.

Restore into isolated infrastructure first. Validate data, evidence, key availability and authoritative native outcomes before reconnecting workers; stale persisted authority must not become fresh permission merely because the database restored successfully.

For upgrade cases, record which schema changes permit rollback and which require forward recovery. Do not test a destructive downgrade against shared environments. Use approved disposable state and preserve its recovery inputs.

## Pass criteria and evidence

All applicable install, trust, isolation, restore and upgrade checks must pass at the release revision. Measured recovery meets approved control-plane targets; native effects remain contained and reconciled. Required security findings and custody/location constraints must be resolved for the accepted deployment scope.

Preserve signed manifests, actual installation/dependency versions, role/custody review, backup/restore inventories, integrity comparisons, measured timing, upgrade matrices, actual alert/support observations and reviewer decisions. Link to individual G01/G10/G11 criteria through the [delivery register](../../implementation/delivery-register.yaml).

## Cleanup and reruns

Revoke restored/test identities, prevent stale worker reconnection and dispose of isolated restores under retention rules. Retain failed recovery evidence. Repeat affected cases after release packaging, persistence, workflow versioning, key custody, trust, install topology or recovery changes.
