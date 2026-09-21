# Dependency-safe retirement orchestration

The repository now provides a non-mutating retirement coordination contract in
`tools/retirement.py`. It exists to stop otherwise-correct owner tools from being
combined in an unsafe order. It does **not** delete native resources, release data
holds, prove sanitization, or declare a site retired.

This closes a repository integration gap under W25 while leaving the original
native acceptance criteria intact.

## Why this exists

The implementation already has independently owned operations for edge withdrawal,
DNS tombstones, IPAM retirement, retained-data protection and capacity release.
Those operations must not be treated as interchangeable cleanup steps:

1. exposure must be withdrawn before dependent service closure;
2. access and service memberships must be revoked;
3. retained copies, catalogues and key dependencies must have explicit custody;
4. native owned resources must be reconciled and cleaned up under their actual
   platform owners;
5. DNS ownership must be withdrawn before IPAM reuse;
6. IPAM retirement must precede capacity/address reuse;
7. capacity can be released only after all applicable cleanup owners have completed;
8. live-service closure remains separate from later retained-data destruction.

The coordinator validates that dependency graph and exact owner receipts. Missing,
foreign, reordered or broadened evidence keeps retirement held.

## Plan format

A retirement plan uses `format: hosting-retirement/1` and binds:

- the exact source commit;
- one operation ID and monotonic generation;
- the exact environment/site/platform/tenant/WSD scope;
- every owned resource and its accountable owner;
- the native identity for anything being removed or deprecated;
- explicit `remove`, `deprecate`, `retain` or `transfer` disposition;
- whether the resource is shared;
- retained-data records and their copy/key/hold/disposition authorities;
- one topologically ordered action graph.

Shared resources cannot be marked for blind removal. Retained or transferred
resources require explicit retained-data custody. A resource selected for removal
or deprecation must be covered by an accountable retirement action.

Supported action types are intentionally narrow:

| Action | Purpose |
| --- | --- |
| `withdraw_exposure` | Remove owned live exposure before destructive work |
| `revoke_service_access` | Revoke owned identity/service memberships |
| `protect_retained_data` | Establish retained copy/catalogue/key custody |
| `cleanup_native_resources` | Bind native platform cleanup evidence |
| `withdraw_dns` | Bind authoritative DNS tombstone evidence |
| `retire_ipam` | Bind IPAM retirement/deprecation evidence |
| `release_capacity` | Release capacity only after applicable cleanup owners |
| `close_service` | Record live-service closure after every prior action |

The graph must end at `close_service`. When retained data exists, destructive
actions must descend from `protect_retained_data`. DNS withdrawal precedes IPAM
retirement, and capacity release must descend from every applicable native/DNS/IPAM
cleanup action.

## Evidence format

Evidence uses `format: hosting-retirement-evidence/1`, the exact plan digest and
ordered owner receipts. Every receipt binds:

- the exact action ID;
- `COMPLETED` status;
- the exact sorted resource ID set;
- an observation timestamp;
- an external evidence reference.

Receipts can advance only after all declared predecessor receipts. A missing action,
different resource set, changed plan digest or skipped predecessor is rejected.

Running:

```sh
python tools/retirement.py \
  --plan /private/retirement-plan.json \
  --evidence /private/retirement-evidence.json \
  --output /private/retirement-review.json
```

produces one of:

- `RETIREMENT_HELD_PENDING_OWNER_EVIDENCE` with the exact next action; or
- `RETIREMENT_EVIDENCE_COMPLETE_REQUIRES_ACCEPTANCE`.

Neither status is native acceptance or production authority.

## Delivery-runner integration

`retirement_review` is a registered delivery stage. Its packet has no arbitrary
command surface and binds exactly two private files:

- `plan`;
- `evidence`.

The retirement plan must use the delivery's exact source commit and exact scope.
The durable delivery runner records `retirement-review.json` and an owner
completion receipt. Because the stage is read-only, recovery reuses the retained
completion artifact; it does not replay native cleanup.

A normal retirement graph should still use the existing native/service-owner
stages for actual edge, DNS, IPAM, backup, platform and capacity operations. The
review stage proves that their accepted evidence has been assembled in the
required dependency order.

## What remains native work

This coordination layer does not satisfy W25 by itself. Site completion still
requires actual, accepted evidence for:

- edge/public/service exposure withdrawal;
- identity and certificate revocation;
- useful-data retention and independently recoverable keys/catalogues;
- platform-specific VM/volume/network/policy cleanup or retained ownership;
- DNS tombstone propagation and address/name reuse quarantine;
- IPAM retirement;
- capacity release against authoritative current ownership;
- absence of orphan active dependencies across shared services;
- sanitization/destruction when a retained object later becomes eligible;
- proof that other tenants/shared objects were not damaged.

Those are owner and commissioning activities against actual infrastructure. Their
receipts can be consumed by this contract; CI fixtures cannot substitute for them.
