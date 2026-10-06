# P05 — Capabilities, immutable plans and admission contracts

P05 engineering is being implemented under the user's continuing development
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

The P05 implementation of [ADR-016](../decisions/adr-016-terraform-plans-and-resource-ownership.md)
uses a reviewed saved-plan digest, toolchain digest, backend/workspace/state
lineage and serial, lock owner, and one writer per resource/field. Missing native
state or ownership is an explicit proposal hold. This selects the representation
for engineering; actual backend/tool/provider choices and accountable review
remain external P06/P07 inputs and no acceptance is invented.

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

## Qualification in progress

The first local Planning suite passes 90 tests, including each missing dimension,
all three platform profiles, exact-scope evidence failures, sovereignty/service
controls, graph cycles, ownership collisions and canonical binding changes.
Strict typing and lint pass. Subsequent PostgreSQL, owner-wire and browser evidence
will bind the final source; this initial local observation is not G05 acceptance.
