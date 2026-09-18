# Authoritative IPAM allocation handoff

**Purpose:** define the IPAM owner handoff for reservation, confirmation and controlled release without making this repository an allocator or storing actual site addresses/prefixes.

RA §10 requires authoritative IPAM to reserve before dependent network creation, confirm after realization, and release only after routes, leases, DNS and policy are reconciled. IPAM-001 through IPAM-004 require an authoritative owner, unique-by-default allocation, idempotent operation identity, conflict detection, dependency-aware reuse quarantine, and a hard prohibition on guessed allocations when IPAM is unavailable.

## External authority and value minimization

The authoritative IPAM remains external. `sources/capabilities/ipam_allocation_index.json` stores exported lifecycle evidence only and is intentionally empty today. The repository record stores a stable `allocation_ref` into the authoritative service, but not the actual address or prefix value.

That separation is deliberate. Downstream network/DNS owners receive the exact allocated value through the approved IPAM handoff; Git is neither a second address database nor a fallback allocator.

## Allocation intent

The preflight intent contains immutable allocation and operation IDs, generation, the parent reservation ID, WSD/request identity, the parent reservation-intent reference, unique-default versus explicit-overlap policy, family, ADDRESS/PREFIX kind, optional prefix length, delegated scope reference, hold expiry and owner roles.

There is **no address or prefix value field**. Any unexpected caller-supplied value is rejected by the closed schema. This structurally enforces the source rule that IPAM failure cannot cause guessed allocations.

The IPAM operation ID must match exactly one `ipam` dependency handoff in the parent reservation intent. A new external IPAM reserve is considered ready only while the parent exported reservation is confirmed `HELD` and unresolved.

## Exported lifecycle evidence

The repository implementation model uses `RESERVED`, `CONFIRMED`, `RELEASE_PENDING`, `QUARANTINED`, `RELEASED`, and `UNCERTAIN`. These are repository record states, not a requirement that a selected IPAM product expose those exact names.

- `RESERVED`: authoritative IPAM reference exists and its hold has not expired; dependent creation is still pending.
- `CONFIRMED`: realization has occurred and the allocation owner has confirmed the authoritative allocation against that realization.
- `RELEASE_PENDING`: release was requested, but one or more cleanup dependencies remain unresolved.
- `QUARANTINED`: route/DHCP/DNS/policy/logging/incident-response cleanup is complete or explicitly not applicable, and the allocation is still held from reuse until the recorded reuse boundary.
- `RELEASED`: cleanup and quarantine are complete and the authoritative owner has recorded release.
- `UNCERTAIN`: a reserve/confirm/release result is ambiguous; known partial lifecycle evidence is retained and no retry/reuse is inferred.

The implementation does not claim that every environment uses DHCP; a cleanup item can be `NOT_APPLICABLE` only with an owner/evidence reference. The same applies to the other source-named cleanup obligations.

## Idempotency and conflicts

Same allocation ID + operation ID + generation + exact intent returns the existing authoritative allocation reference. Reusing an allocation/operation identity with a changed intent is a conflict. An `UNCERTAIN` record requires authoritative discovery before retry.

`RELEASE_PENDING` or `QUARANTINED` state cannot be reused for a new allocation. `RELEASED` is terminal for that operation; a new allocation attempt requires a new approved operation identity.

Unique allocation is the default. An overlap allocation is accepted by the record/preflight schema only when it carries an explicit external exception reference. The checker does not invent translation or migration design from that reference.

## DNS relationship

`docs/DNS_LIFECYCLE.md` already requires accepted allocation/name ownership before DNS mutation. This IPAM layer supplies only the authoritative allocation reference and lifecycle evidence. The DNS owner must resolve the exact A/AAAA/PTR value through the approved IPAM/name-assignment process; it must not derive an address from this repository example.

## Current expected result

Because the exported reservation/IPAM indexes are empty, the repository example remains held:

```sh
python scripts/check_ipam_allocation_preflight.py examples/ipam_allocation_intent.json.example --as-of 2026-09-18T18:00:00Z --expected-status HOLD_PARENT_RESERVATION_NOT_HELD
```

Every IPAM/DNS/apply/activation mutation flag remains false.

[Addressing lifecycle](../architecture/reference/10-addressing-name-services-and-end-to-end-traffic.md) · [ADR-0020](../adr/0020-use-authoritative-unique-by-default-address-allocation-and-controlled-reuse.md) · [DNS lifecycle](../DNS_LIFECYCLE.md) · [Reservation preflight](reservation-preflight-and-reconciliation.md)
