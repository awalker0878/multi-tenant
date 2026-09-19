# Storage ownership, copy-lineage and lifecycle assurance

**Purpose:** close the storage-service portion of I07 without turning this repository into a storage controller, snapshot manager, copy catalogue, backup system, legal-hold system or sanitization executor.

VM or volume creation is not storage assurance. A qualified storage service must retain ownership/categorization/access/key/placement lineage, measurable service semantics, derivative-copy and hold information, and a qualified release/sanitization procedure. Backup/restore remains a separate protection assurance dependency.

## Source obligations

- STO-001 requires every storage resource and derivative copy to carry owner, categorization, access scope, key policy, placement/retention constraints and lineage; cross-scope attachment/export requires explicit authorization.
- STO-002 requires measurable capacity/performance, consistency, replication, snapshot/clone and portability semantics tested under contention and the accepted failure condition.
- STO-003 requires release/reuse to reconcile all known copies and legal/administrative holds, apply an approved sanitization method and retain a receipt covering scope, method, verification and exceptions.
- SVC §4 distinguishes virtual-disk, guest-data, copy/replication and administration paths and requires explicit copy/key ownership.
- ADR-0027 separates virtual-disk, guest-data, replication and administration paths.
- ADR-0033 separates live-service retirement from retained-data disposal.

## Active assurance index

The active index is `sources/capabilities/storage_data_lifecycle_assurance_index.json` and is intentionally empty.

A future service-profile record binds:

- site;
- service class;
- platform profile;
- storage profile;
- protection-assurance dependency;
- storage owner;
- review cadence.

## Ownership and lineage

Current evidence requires:

- resource owner;
- categorization;
- access scope;
- key policy;
- placement/retention rules;
- lineage;
- cross-scope authorization record;
- observed cross-scope denial test.

Network isolation or a platform volume object alone cannot satisfy those ownership and attachment/export controls.

## Service semantics

Current service-profile qualification requires attributable evidence for:

- capacity;
- performance;
- consistency;
- replication;
- snapshot/clone semantics;
- portability;
- contention test;
- accepted-failure test.

No universal numeric target is invented here. The selected service class supplies the accepted values and tested limits.

## Copy inventory and protection boundary

The copy-inventory block requires:

- authoritative copy catalogue;
- derivative-copy lineage;
- retained-copy record;
- legal/administrative hold register;
- key-version mapping;
- copy authority.

The scope also references the separate backup/restore assurance record. This storage gate does not duplicate isolated-restore or protected-copy assurance.

## Release and sanitization capability

Before the service can be considered lifecycle-qualified it requires a current, tested procedure for:

- live-service withdrawal;
- copy/hold reconciliation;
- approved sanitization method;
- sanitization verification;
- resource-specific receipt schema;
- exception handling.

This is **procedure qualification**, not an actual sanitization receipt. Every real resource release/reuse still requires current copy/hold reconciliation and its own completed receipt under the storage authority.

## States

Supported states are:

- `CURRENT_QUALIFIED` — ownership, service semantics, copy/hold and lifecycle procedure evidence are current with no OPEN gaps;
- `REVIEW_DUE` — service-profile or gap review expired;
- `SERVICE_TEST_DUE` — ownership/cross-scope or service-semantics evidence is stale;
- `LIFECYCLE_DUE` — copy catalogue/hold/key-version or retirement/sanitization procedure evidence is stale;
- `GAPS_OPEN` — current evidence exists with unresolved storage gaps;
- `UNCERTAIN` — authoritative storage/copy/lifecycle state requires reconciliation.

## Readiness preflight

`scripts/check_storage_data_lifecycle_readiness.py` evaluates one exact site/service/platform/storage profile.

A successful result is `STORAGE_DATA_LIFECYCLE_CURRENT_NO_STORAGE_MUTATION_AUTHORIZED`.

It does **not** authorize:

- storage provisioning or attachment;
- snapshot/clone;
- data export;
- copy deletion;
- media sanitization;
- release/reuse;
- infrastructure apply;
- production activation.

Current repository state remains held because no native storage profile has supplied current evidence:

```sh
python scripts/check_storage_data_lifecycle_readiness.py examples/storage_data_lifecycle_readiness_intent.json.example --as-of 2026-09-19T01:50:00Z --expected-status HOLD_NO_CURRENT_STORAGE_LIFECYCLE_ASSURANCE
```

Actual resource retirement remains a separate externally accountable storage operation with a resource-specific receipt.

[SVC §4 — Storage, copies and retained-data ownership](../architecture/shared-services/4-storage-copies-and-retained-data-ownership.md) · [STO allocation](../implementation/allocation/sto.md) · [Backup/restore assurance](backup-isolated-restore-assurance.md)
