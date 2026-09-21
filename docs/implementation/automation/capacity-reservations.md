# Capacity reservation owner

`tools/capacity.py` supplies the missing compute/storage reservation transaction
before native provisioning. It accounts for vCPU, memory MB and storage GB against
both a qualified pool budget and tenant entitlement. Reserved and confirmed
allocations both consume capacity; a controller timeout or expired approval never
recycles them automatically.

## Reference deployment decision

Use one independently recoverable capacity-owner host with a private local SQLite
database. All callers execute through this owner; do not put the database on NFS,
copy it to each runner or run independent active owners. SQLite immediate
transactions and full synchronous commits serialize admission and atomically
publish reservation plus audit event. A competing transaction receives a hold;
it can inspect the exact reservation ID before trying the same idempotent request.
This selects a concrete reference implementation, not a distributed capacity
service or native hypervisor fence.

The accepted envelope is the budget exclusively delegated to this owner, after
accounting for unmanaged allocations, fragmentation, placement restrictions and
the platform's overcommit policy. It is not a transient native free-space counter.
Native capacity observers and engineering acceptance must establish this budget.
Avoid subtracting these reservations twice when refreshing the envelope. The
explicit failure reserve is never available to ordinary reservations.

## Envelope and request schemas

An envelope has `format: hosting-capacity-envelope/1`, `owner_id`, positive integer
`revision`, `valid_from`, `valid_until`, `acceptance_ref`, `pools` and `tenants`.
Windows last at most one hour. Each pool key maps to `origin`, `native_id`,
`platform`, `site_key`, `capacity`, `reserve`, `capabilities` and
`qualification_ref`. Capacity and reserve each contain exactly nonnegative
integer `vcpu`, `memory_mb`, and `storage_gb`. A native origin/ID pair cannot be
counted under two pool names. Each tenant entry has the same unit map in `limit`,
an explicit list of eligible `pools` and `entitlement_ref`.

Each request has `format: hosting-capacity-request/1`, `owner_id`,
`reservation_id`, `operation_id`, positive integer `generation`, `scope`,
`pool_id`, `units` and `capabilities`. Scope contains `environment_key`, `site_key`,
`platform`, `tenant_key` and `wsd_key`. Requested platform/site and capabilities
must match the pool, and the tenant must be entitled to that pool. Reservation
IDs and operation/generation/scope cannot be reused to reserve a second copy.
Use a single aggregate reservation for one WSD operation in the selected pool.
Multi-pool workflows require separate operation identities and explicit partial
allocation cleanup; there is no implicit cross-pool atomic transaction.

Initialize the controlled owner once:

```sh
python tools/capacity.py initialize --database /private/capacity.db \
  --envelope /private/accepted-capacity.json --execute
```

The database, its parent, requests and authority files must be private. An existing
database is never overwritten by initialization. If initialization is interrupted,
reconcile that incomplete owner record before enabling callers.

## State transitions

Every mutation requires a current `hosting-capacity-authority/1` record with
`request_sha256`, `action`, `native_ids_sha256`, `envelope_sha256`,
`previous_receipt_sha256`, `valid_from`, `valid_until`, `change_ref` and
`evidence_ref`. Object digests use `tools.readback_core.digest`. Native ID digests
cover the sorted ID list, or `[]` for reserve/release. The previous receipt digest
is JSON null for the initial reserve and the exact current receipt for a new
confirmation or release. This comparison occurs inside the transaction.

| Operation | Required evidence | Result |
| --- | --- | --- |
| `reserve` | Current qualified envelope and tenant admission authority | `RESERVED`; pool and tenant capacity are charged immediately |
| `confirm` | Exact observed native resource ID list and accepted ownership handoff | `CONFIRMED`; capacity remains charged, native identities cannot change |
| `release` | Accepted resource-by-resource cleanup/retention and dependency evidence for the exact current receipt | `RELEASED`; capacity becomes available, old reservation IDs remain tombstoned |
| `inspect` | Private owner access and exact original request | Current retained receipt; no state change or fresh native claim |

```sh
python tools/capacity.py reserve --database /private/capacity.db \
  --request /private/reservation.json --authority /private/reserve-authority.json \
  --output /private/reservation-receipt.json --execute
```

Confirmation additionally takes `--native-ids /private/native-ids.json`, a JSON
list of exact unique IDs. A native ID already charged to another live reservation
is rejected. References are custody pointers to accepted evidence; this local
transaction does not query a hypervisor or create native approval. Do not release
capacity merely because an API request timed out, the workflow failed, or an
address was withdrawn. A release prepared before confirmation cannot release the
subsequently confirmed allocation because its receipt digest has changed.

Identical already-completed actions return their receipt without double charging
or changing identities. Expiry of the original envelope does not prevent current
authorized confirmation or cleanup of an existing reservation. New admission
requires a current envelope. The [delivery runner](delivery-runner.md) exposes
these three transitions as the `capacity` stage kind.

## Refresh, retention and recovery

Use `update-envelope` with `--envelope` and `--authority`. The authority is
`hosting-capacity-envelope-authority/1` with `envelope_sha256`,
`previous_envelope_sha256`, current `valid_from`/`valid_until` and `change_ref`.
Only the next revision for the same owner is accepted. Existing live reservations
must still fit the new limits and qualified capabilities; their pool's native
origin, ID, platform and site cannot change. Renewal, growth and entitlement
changes therefore cannot silently strand live ownership or reduce available
capacity below existing commitments.

Every transaction verifies the event digest chain and reconstructs final
reservation/receipt membership before updating the database. Direct table edits,
orphan allocations and conflicting journal data hold all new work. This detects
inconsistency, not forgery by a privileged database custodian. Back up through a
consistent SQLite backup or an offline copy with the owner stopped; retain the
envelope authority and external native evidence alongside it. After restoring
an older backup, fence admission and reconcile every subsequent native allocation
before reopening the owner. Restoring older accounting never releases actual
resources. No automatic database reset, record deletion, lease reclamation or
native provisioning rollback is provided.
