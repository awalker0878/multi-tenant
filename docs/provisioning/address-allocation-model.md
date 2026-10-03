# Address allocation model

A planning prefix is not an owned prefix. The portable package decides which
prefixes a workload security domain needs and where its names belong, but addressing
is **owned** by authoritative IPAM and DNS systems outside this repository. A plan
that presented its own arithmetic as a held allocation would let a downstream owner
build on addresses nobody allocated, and a plan that released reusable addressing
before the dependent name was withdrawn would hand a live name to a second workload.

This document describes the seam that compiles the reviewed addressing decision into
the exact intent those owners' existing machinery accepts, reads the owners' own
exported records back, and refuses to treat a proposal as ownership. The module is
`provisioner/allocations/addresses.py`. No code here contacts an owner, allocates an
address, registers a name or releases anything.

## The documents

| Format | Producer | Binds |
| --- | --- | --- |
| `hosting-address-view/1` | `address_view(plan)` | the reviewed proposal: inventory digest/status/authority, site, platform, scope and every reviewed zone with its pool, prefix, family, kind, gateway host number and workload addresses |
| `hosting-address-binding/1` | `binding(plan, domain, ...)` | one zone's allocation identity: `allocation_id`, `operation_id`, `generation`, `plan_digest`, `view_digest`, `reservation_id`, `request_id`, the five delivery scope keys, the zone, the domain, the pool and the allocation intent digest |
| `hosting-dns-registration-binding/1` | `registration_binding(plan, domain, ...)` | one zone's registration identity: the same identity plus `registration_id` and the confirmation digest of the allocation it was derived from |
| `hosting-address-owner-handoff/1` | `handoff(plan, ...)` | the whole reviewed chain: the compiled capacity request, the compiled reservation intent, one allocation intent and one registration intent per zone, the staged sibling references, the per-document digests, the limits and the review instant |
| `hosting-address-reconciliation/1` | `reconcile(plan, ...)` | what the owners' exported records actually say about this reviewed identity |

The view deliberately carries **no generation** and no derived operation identity.
Two generations of one WSD propose the same addressing from the same reviewed
decision, so a generation in the view would make an unchanged proposal look changed —
and the view is built before the plan digest exists, so it cannot contain one. The
generation that would own the allocation is in the binding, where it belongs.

## The compiled intents are the owners' own contracts

The repository already owns the contracts for an IPAM allocation intent and a DNS
registration intent, and already owns the contracts for reading the exported evidence
each owner produces. Nothing here restates them.

| Compiled | Validated by | Reached through |
| --- | --- | --- |
| capacity request | `tools/capacity.py` | `provisioner/repository.py` |
| reservation intent | `provisioner/allocations/reservation_preflight.py` | `provisioner/repository.py` |
| allocation intent | `provisioner/allocations/ipam_preflight.py` | `provisioner/repository.py` |
| registration intent | `provisioner/allocations/dns_preflight.py` | `provisioner/repository.py` |
| exported reservation records | `provisioner/allocations/reservation_evidence.py` | `provisioner/repository.py` |
| exported allocation records | `provisioner/allocations/ipam_evidence.py` | `provisioner/repository.py` |
| exported registration records | `provisioner/allocations/dns_evidence.py` | `provisioner/repository.py` |

The owner normalizes a submitted intent before it hashes it, so the provisioner asks
the owner's own preflight for the normalization (`repository.ipam_allocation_spec`,
`repository.reservation_intent_spec`, `repository.dns_registration_spec`) instead of
restating it. The compiled intent carries **no literal address, prefix or DNS name**:
the authoritative owner is the only source of an allocated value, and the exported
record contracts have no field to put one in.

The chain is compiled **in memory** and never written to the checkout. `.gitignore`
ignores `runtime/`, and the release verifier flags untracked source files, so the
operator stages the two sibling documents the owners' preflights resolve from disk —
the capacity request and the reservation intent — under the declared staging root
`runtime/address-handoff/`, exactly as an operator would hand them over. `handoff()`
names those two staged references; `handoff(..., resolved=True)` and `reconcile()`
resolve them.

## Reconciliation states

`reconcile(plan, reservation_index=..., allocation_index=..., registration_index=...,
as_of=...)` validates the exported evidence with the repository's existing checkers
and classifies every zone of the reviewed plan. A missing record is a proposal,
**never** a confirmation, and a malformed or unreadable export is a refusal rather
than an untyped failure.

| Allocation state | Meaning |
| --- | --- |
| `IPAM_INTENT_READY_EXTERNAL_RESERVE_NOT_EXECUTED` | the parent reservation is held and the owner holds no record for this allocation |
| `HOLD_PARENT_RESERVATION_NOT_HELD` | the parent capacity reservation is absent, consumed, released or expired |
| `HOLD_IPAM_IDENTITY_OR_INTENT_CONFLICT` | the owner holds a record for another operation or allocation identity, or the parent reservation carries a different reviewed identity |
| `HOLD_DISCOVER_IPAM_OUTCOME` | the owner's record is `UNCERTAIN` |
| `HOLD_IPAM_RELEASE_LIFECYCLE` | the owner's record is `RELEASE_PENDING` or `QUARANTINED`, so the address is not reusable yet |
| `HOLD_TERMINAL_IPAM_ALLOCATION_NEW_OPERATION_REQUIRED` | the owner's record is `RELEASED` |
| `EXISTING_RESERVED_IPAM_ALLOCATION_IDEMPOTENT` | the owner holds a `RESERVED` record for this exact identity |
| `EXISTING_CONFIRMED_IPAM_ALLOCATION` | the owner holds a `CONFIRMED` record for this exact identity |

| Registration state | Meaning |
| --- | --- |
| `DNS_INTENT_READY_EXTERNAL_CHANGE_NOT_EXECUTED` | the allocation is confirmed and the owner holds no record for this name |
| `HOLD_IPAM_ALLOCATION_NOT_CONFIRMED` | the allocation this name depends on is not confirmed |
| `HOLD_DNS_IDENTITY_OR_INTENT_CONFLICT` | the owner holds a record for another registration identity or another intent |
| `HOLD_DISCOVER_DNS_OUTCOME` | the owner's record is `UNCERTAIN` |
| `HOLD_DNS_RELEASE_LIFECYCLE` | the owner's record is `RELEASE_PENDING` or `TOMBSTONED`, so the name is not withdrawn yet |
| `HOLD_TERMINAL_DNS_REGISTRATION_NEW_OPERATION_REQUIRED` | the owner's record is `RELEASED` |
| `EXISTING_REGISTERED_DNS_IDEMPOTENT` | the owner holds a `REGISTERED` record for this exact identity |

Both vocabularies deliberately borrow the refusal vocabulary of the preserved
preflights (`provisioner/allocations/ipam_preflight.py` and
`provisioner/allocations/dns_preflight.py`) so an operator reads one vocabulary.
The reconciliation itself is the repository's own: `CONFIRMED`, `REFUSED` or
`PENDING_OWNER`.

## Identity binding

An authoritative allocation is bound to the exact reviewed decision it was obtained
against. `parent_spec_sha256`, `allocation_intent_digest` and
`registration_intent_digest` recompute the digest the owner recorded **from the
reviewed chain**, not from the owner's own record, so a record that answers a
different operation, a different generation, a different parent reservation, a
different site, zone, pool or intent is a conflict rather than a silently adopted
allocation. `allocation_id_for`, `registration_id_for`,
`allocation_operation_id_for` and `registration_operation_id_for` derive every
identity from the reviewed plan, so a retry reconciles the first attempt instead of
creating a second allocation or a second name.

A **confirmed allocation may differ from the proposal without changing the approved
plan**. The authoritative prefix is the owner's, and the plan digest is unchanged by
reading it — the plan binds the addressing *identity* it was reviewed against, not a
value the owner has yet to return. The reconciliation never contains a literal prefix
or address, so a differing allocation cannot leak into an approval.

## Settlement gates

| Gate | Refuses |
| --- | --- |
| `require_confirmed(reconciliation)` | `IPAM_ALLOCATION_CONFLICT` (a definite no), `IPAM_ALLOCATION_UNRESOLVED` (the owner has not answered), `IPAM_ALLOCATION_UNCONFIRMED` (the answer is not a confirmation) |
| `require_registered(reconciliation)` | `require_confirmed` first, then `DNS_REGISTRATION_CONFLICT`, `DNS_REGISTRATION_UNRESOLVED`, `DNS_REGISTRATION_UNCONFIRMED` |
| `require_releasable(reconciliation)` | `ADDRESS_RELEASE_ORDER_VIOLATION` |
| `require_settled(reconciliation)` | `IPAM_ALLOCATION_UNRESOLVED` or `IPAM_ALLOCATION_UNCONFIRMED`, and `DNS_REGISTRATION_UNRESOLVED` |

`require_settled` is what a transport calls: an absent owner reply is the owner's
work, and only a definite refusal or an unknown outcome stops the plan.

## Retirement release ordering

Reusable addressing is never handed back before the dependent native state is safely
withdrawn. `require_releasable` refuses with `ADDRESS_RELEASE_ORDER_VIOLATION` when a
reusable allocation's dependent registration is still live
(`REGISTERED`, `RELEASE_PENDING`), when the exported cleanup is not complete, or when
a `RELEASED` allocation's name is only `TOMBSTONED`. The owner's own record contract
enforces the same ordering: a `QUARANTINED` or `RELEASED` allocation must carry a
complete cleanup, a `REUSE_NOT_BEFORE` instant, and a release that does not predate
it. A `RELEASED` registration requires the full registration, release request,
tombstone and release receipt chain. Nothing here releases anything; the gate reads
the owner's records and refuses.

## Authority

`EXISTING_CONFIRMED_IPAM_ALLOCATION` is the only allocation state where `confirmed`
is true, and it is reachable only from a live record the authoritative owner exported.
An allocation is addressing, never change authority: `may_allocate` and `may_register`
are permission for the *owner's* next step, not an authorization for this repository to
apply anything. `reconcile` is a reading — it allocates, registers and releases nothing.

The `address-intent` conformance check is repository-side and reports the reviewed
proposal as intent, naming `PLANNING_PROPOSAL_NOT_AUTHORITATIVE_ALLOCATION` as the
authority and `address-confirmation` as the check that settles it. The
`address-confirmation` and `dns-registration` checks are `EXTERNAL`: they are
`PENDING_EXTERNAL_EVIDENCE` until the owners answer, `PASS` only on a confirmed
allocation and a registered name, and `FAIL` on a definite refusal. The `allocation`
and `registration` evidence records are bound to the view digest and report the owners'
states, so an approval never has to guess whether addressing is held.

A reading is only evidence for the plan it names. A reconciled addressing reading whose
operation identity, generation or view digest is not this plan's stays
`PENDING_EXTERNAL_EVIDENCE` and reports the mismatched keys, so another operation's
allocation is never read as this operation's.

## What this does not claim

No document here asserts that a prefix was allocated, that a name was registered,
that an owner was contacted or that addressing was released. Every plan stays
`PLANNED_DISABLED_NOT_AUTHORIZED` with `native_contact: false`; the repository
compiles an intent, reads exported evidence and refuses. The authoritative IPAM and
DNS systems, their records and their credentials are external, and this repository
holds none of them.