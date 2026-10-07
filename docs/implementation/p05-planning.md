# P05 — Capabilities, immutable plans and admission contracts

P05 engineering is implemented under the user's continuing development
authorization. This record separates implemented behavior, measured evidence and
receiving decisions; the delivery register owns phase/gate state.

## P05.01 / P05.02 — Assessment

Planning retains all eleven profile dimensions for VMware, AHV and OpenStack.
Adapter declarations, Inventory observations and Assurance qualification remain
separate inputs. Qualification matches tenant, site, endpoint, native scope,
installed tuple, operation, method, profile and exact artifact digests. Evidence
must be current, unrevoked and E3/E4 for operational eligibility; synthetic
qualification-shaped fixtures establish no native support.

The deterministic evaluator expands compute, guest, disk, NIC, placement,
recovery, service and communication requirements from P03 intent. Unknown custom
requirements remain visible. Required isolation, custody, location and data-path
controls cannot disappear through an empty policy. Each finding supplies its
source, reason and remediation. Preferred requirements remain visible; unmet
mandatory conditions prevent eligibility. Capacity observations are never receipts.

## P05.04 — Compilation choice

The P05 implementation of [ADR-016](../decisions/adr-016-native-api-plans-and-resource-ownership.md)
uses a canonical native operation plan containing exact resource specifications,
API versions, custody ID/generation and the ownership-map digest. The envelope
pins adapter and API-contract artifacts. A missing plan or ownership map holds
execution. Each native request is separately journaled under current authority;
API-first Inventory observations and administrator validation supply installed facts.

Canonical semantic JSON uses `p05-json-v1`: recursively sorted ASCII object keys,
original array order, compact UTF-8 JSON, escaped Unicode, unescaped slashes,
integers within the interoperable 53-bit range and no floating point or secret
fields. Request IDs, creation time and volatile transport metadata are excluded.
The immutable content digest covers source versions, mappings, artifacts, effects,
reservation intents, budgets, lane, expiry and recovery boundaries. A separate
versioned Governance binding covers that content digest, plan identity, requester,
executors and scope. Changed semantic content therefore changes approval authority.

The effect graph declares ordered preconditions, sole effect owner, scope, exact
artifact and unknown-outcome hold behavior. Target first write separates source
rollback from forward recovery or separately approved reconciled source return.
Plan construction and approval grant no native write authority.

## P05.03 / P05.06 — Journal and admission contract

Lifecycle now owns a PostgreSQL reservation journal with immutable intent-command
receipts and event history. Owner calls happen after durable attempt recording.
Unknown responses require observation; independent owner receipts preserve partial
success. Concurrent plans are checked by the authoritative simulated owner, not
by cached capacity. Expiry records a hold; release requires fresh unused readback
and the owner rechecks live consumption. Late command receipts cannot replace a
newer reconciliation result. No native allocation adapter or execution dispatch
is installed by this increment.

The admission evaluator binds exact current entitlement, commissioned scope,
state/ownership, artifacts, facts, approval and reservation receipts. Revocation,
expiry, changed inputs and missing exact-tuple support deny operational admission.
An isolated campaign additionally binds endpoint/credential/data scope, actor,
impact limit, cleanup owner and expiry; it cannot target production. Its result
specifies the atomic P06 admission/receipt/reservation/outbox transaction and
immediate effect rechecks. Evaluating this contract never creates an executable job.

## Persistence and source boundaries

Planning persists immutable assessments and plans, command receipts and an outbox
in one owned transaction. Identical tenant/actor command retries return the
original pinned result after current delegation checks. PostgreSQL runtime grants
exclude update/delete of history. Current validity is returned alongside immutable
content; it never rewrites reviewed bytes. Tenant command budgets and input/graph
bounds constrain synchronous computation.

Catalogue, Inventory and Assurance expose independently authenticated Planning
source reads. Governance checks the original exact Planning delegation and current
application and site read permissions. No source shares another owner's database
or workload secret. Inventory's P04 declarations and unassessed dimensions remain
held. Assurance reads exact records from independently mounted qualification
custody; an absent record is explicitly unknown. It does not create qualification.

`planning-facts` publishes with mandatory publisher confirms and consumes the
published Catalogue/Inventory fact contracts with durable event-ID deduplication.
Acknowledgment follows inbox/invalidation commit; conflicting/invalid payloads
retain only a quarantine digest. Facts conservatively invalidate tenant plans and
never refresh observations, confer qualification or dispatch effects. Direct
owner rechecks remain required for current validity, including qualification changes.


## P05.05 — Review experience

The compiled Console compares currently authorized destinations, exposes unmet
requirements and remediation, and reviews exact mappings, digests, effects,
expiry and recovery boundaries. Comparison requires authority over both plans.
Approval handoff rereads current validity on the server and binds the submitted
digest to the immutable revision. Revoked or stale source facts disable approval;
actor revocation clears protected access and history. Uncertain command outcomes
freeze the original payload/key for an unchanged retry. Polls are bounded and
back off on unavailable owners.

The browser campaign checks a narrow viewport, keyboard activation, explicit
current-source revocation, accepted-response loss with exactly one persisted plan,
and actual Governance approval handoff. Representative operator and assistive
receiving review remain distinct from these automated observations.

## Delivery and qualification records

See the [verified index](../../verification/p05/final/qualification-index.json),
[check matrix](../../verification/p05/check-matrix.md) and
[corrections](../../verification/p05/corrections.md). The final packet retains
original source-bound local/hosted command logs, real PostgreSQL reservation
observations, owner responses, broker deliveries and three compiled browser
campaigns. No native resource was allocated and no E3 qualification is claimed.

The [completion packet](p05-completion-review.md) supplies the concrete receiving
tasks and P06 handoff. The [runbook](../operations/runbooks/planning-review.md)
specifies mounted policy/profile/qualification custody, separate workload
credentials, current authority, recovery and the combined fact topology.
Formal G05 acceptance remains a designated review, separately recorded in the
canonical delivery register.
