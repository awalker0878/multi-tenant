# Reconcile recovery and resume service

Procedure ID: OPS-RECOVERY. Owners: SRE incident lead and lifecycle; contributors: IAM/security, assurance, native/service owners and application/data owners. Scope: R14–R17/R22–R25/R29–R32/R35; P01.06, P06/P07 and P10.02; Q04/Q07/Q09.

Use this procedure after lost control-plane state, uncertain native effects, site isolation, restored authority, or an incident that makes current writer/data ownership uncertain. [Restore control plane](restore-control-plane.md) and [dependency recovery](dependency-recovery.md) perform restoration; this procedure governs reconciliation and safe resumption.

For Governance identity admission, execute the
[independent custody and resumption ceremony](identity-recovery-custody.md). It
requires two independently enrolled signers and a separate release of the held
installation. The broader native/data reconciliation obligations below still apply.

## Required recovery record

Record incident/recovery ID, procedure/release/configuration revisions, last trusted state, chosen recovery points/watermarks, affected jobs/resources/tenants, backup and key references, current writer locations, incident lead and authoritative owners. Preserve available journals, workflow histories, native request IDs, external reservation receipts, approval/revocation records and independent audit before changing state.

Define recovery scope explicitly. Control-plane RPO/RTO and application dataset/outage objectives are separate. A recovered database is insufficient when its referenced workflow/evidence/native state cannot be reconciled.

## Contain before restore or resume

1. Hold new affected admissions and stop unsafe task dispatch. Verify enforcement at the authoritative admission boundary; record exceptions for explicitly permitted observation work.
2. Fence old mutating workers using the selected effective native credential/network/platform mechanism. If a worker is partitioned, confirm containment through an independently controlled boundary. Changing a database epoch or task queue alone does not stop it.
3. Keep restored services/workers isolated from native mutation paths. Preserve scoped read access for independent outcome observations.
4. Identify in-flight native/data actions and retained source/target datasets. Hold release/deletion of reservations, snapshots, staging and keys until their actual use and retention obligations are known.

If effective old-writer containment cannot be established, remain held and escalate to the native/security owner. A time budget expiring never turns uncertainty into permission.

## Reconciliation order

| Step | Owner action | Required result |
| --- | --- | --- |
| 1. Trust | Recover verified identity/PKI/keys; reconcile post-backup revocations and time validity | Current caller/worker authority established independently of stale restored grants |
| 2. Durable stores | Compare restored context DB, operation/idempotency/outbox/inbox journals and recorded backup watermarks | Missing or later records identified; no invented successful operations |
| 3. Workflow history | Compare admitted jobs, stable workflow IDs, histories, attempts and supported worker versions | Each workflow maps to one admitted job; gaps and incompatible histories held |
| 4. Messaging | Compare retained events/consumer receipts with owning records; rebuild safe projections under controlled replay | Duplicate facts are deduplicated; replay cannot grant authority or redispatch native effects |
| 5. Evidence | Compare assurance metadata with object bytes/digests, custody and keys | Missing/unverifiable artifacts quarantined; dependent claims and completion held |
| 6. Native/state | Independently read actual platform resources, request outcomes, IaC bindings and ownership | Each intended effect classified using actual observations and exact resource identity |
| 7. Reservations | Reconcile authoritative IPAM/capacity/snapshot/staging/service receipts and actual resource use | Existing allocations retained correctly; partial acquisitions resolved explicitly |
| 8. Current authority | Re-evaluate grants/revocations, plan digest/freshness, change window, site commissioning and exact qualification | Fresh scoped authority recorded; restored approval/lease is never accepted by age alone |

## Native operation decisions

| Outcome | Permitted next action |
| --- | --- |
| Known not started | Revalidate plan/authority/ownership and existing idempotency identity before dispatch under the recovered workflow |
| Confirmed failed | Inspect partial resources/data; choose scoped compensation or corrected/reapproved plan; preserve original attempt |
| Confirmed succeeded | Record independent observation; continue from the established postcondition without repeating the effect |
| Outcome unknown | Hold affected resources and subsequent dependent writes; obtain additional authoritative observation or owner-assisted reconciliation |

Absence from a partial inventory generation is not proof a resource was never created. A missing native request history is not proof the operation failed. A timeout or expired reservation/lease does not release a resource observed in use.

Use lifecycle's bounded reconciliation/recovery request contracts with expected operation revision, exact action and recorded authority. Do not edit private tables or replace the original operation with a new job to bypass its hold.

## Application data boundary

Before target writes, source-return may be allowed only after proving the target is fenced, source data remains valid and all traffic/service bindings are reconciled. After any accepted target writes, compare all authoritative writers and dataset consistency boundaries with the application owner. Use the approved target-forward recovery or explicit source-return replication/reconciliation strategy.

Never restart an old source merely because it is bootable. Preserve target changes, keys and audit; reconcile external effects such as messages or business transactions separately from disk recovery. If divergence cannot be resolved within the agreed objective, keep the controlled outage/hold and obtain the accountable data-owner decision rather than silently discarding data.

## Resume and close

Establish a new effective fencing epoch with demonstrable old-worker exclusion, then enroll only compatible trusted workers. Resume a bounded scope of reconciled workflows under fresh authority. Independently verify native/application/service postconditions, policy denials, evidence finalization, alert delivery and remaining reservations. Expand admission only while these observations remain valid.

Record actual data recovery point, complete recovery time including reconciliation, unknown/held scope, native and application evidence, current support limits and owner decisions. Preserve the incident and original evidence; register corrective work and affected qualification reruns. Recovery is complete only for the expressly reconciled and validated scope.
