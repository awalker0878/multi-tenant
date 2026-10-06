# P06 engineering completion and receiving packet

The six engineering packages deliver isolated simulation admission, durable
workflows, current effect authority, independent readback, evidence custody and
the Jobs experience. Use the [implementation record](p06-execution.md),
[phase scope](phases/p06.md), [G06 procedure](../qualification/gate-reviews/g06.md)
and [operator runbook](../operations/runbooks/durable-simulation.md). Exact-source
verification and the canonical register determine which observations are complete.
Development authority and automated passes do not appoint receiving reviewers.

## BL-P06-001 — designated receiving and operator review

| Reviewer role | Concrete observations to examine | Decision to record |
| --- | --- | --- |
| Product and qualification | Full Catalogue → Inventory → Planning → Governance → Lifecycle → simulator → Assurance → Console journey; E2 labels, scope and IDs. | G06.01 end-to-end acceptance. |
| Security and Lifecycle | Immediate plan/approval/actor/campaign/epoch/hold checks; tenant, worker, ownership and operational-lane denials; restored-epoch quarantine. | G06.02 authority acceptance and ADR-018/020 disposition. |
| Quality and SRE | Before/after acceptance crashes, sealed absence, accepted target write, lost admission/start/command replies, engine/worker restart and real history replay. | G06.03 uncertainty/recovery acceptance and ADR-007 disposition. |
| Assurance, security and SRE | Digest/source/scope binding, independent observation, tenant denial, tamper rejection, append-only privileges, older-journal restore, stable alert receipt and emergency stop. | G06.04 custody/control acceptance and ADR-010 disposition. |

Record actual identities, dates, immutable evidence, scope, findings and decisions.
The existing PROPOSED ADR status remains until its accountable reviewer records
the disposition. No development or test result silently changes that status.

A representative operator and product/quality reviewer should perform these tasks
on the managed browser/OS/policy and assistive combinations selected under OP07:

1. Admit an eligible isolated plan and identify scope, source revision, E2 level,
   workflow and job identities; recover the unchanged request after a lost reply.
2. Explain why an uncertain effect is held, why resources remain reserved and why
   reaching the target-write boundary prohibits an automatic return to the source.
3. Request stop and cancellation, recover a lost control receipt, and distinguish
   a received request from proof that an external effect stopped or was undone.
4. Observe an unavailable dependency and revoked access. Confirm controls become
   unavailable, protected content clears, and history does not resurrect it.
5. Open finalized evidence, compare job/plan/source/digest and independent readback,
   and explain why accepted simulation review does not qualify native support.
6. Follow the restore runbook: keep the independent epoch, inspect the old journal
   against retained external effects, confirm the hold, and record the re-enable
   decision without restoring an old authority epoch or blindly retrying.

Automated keyboard, narrow-screen and history checks cover measured engineering
behavior. They do not substitute for these named operator observations. Resolve
mandatory defects before the designated G06 decision.

## Next engineering work — P07.01 site readiness

Inventory the actual OpenStack installation tuple, approved project/endpoints and
trust, scoped identities, compiler/provider/adapter artifacts, state backend and
locking/custody owners, network/storage/image constraints, quotas and independent
observer. Map each input to the [P07 card](phases/p07.md) and Q05 authorization
record. Missing installation or receiving inputs remain explicit holds.

P06 contains no native mutation adapter. Simulation completion, a synthetic
qualification record, or an E2 review cannot authorize production effects. Carry
the earlier native and operating obligations forward, and preserve the separate
Gate, native qualification and operational acceptance axes.
