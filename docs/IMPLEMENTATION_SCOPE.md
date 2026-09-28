# Current implementation scope and evidence boundary

The [all-waves execution plan](product/enterprise-workload-mobility-execution-plan.md)
is the current B01–B50 delivery baseline. Earlier numbered implementation increments,
W01–W29 and C01–C13 records describe narrower historical scopes; they are not current
product-completion claims. This record replaces the obsolete Increment 04-only scope.

## Implemented repository components

The repository includes the authenticated control application/portal/CLI foundation,
PostgreSQL business state and isolation, approval/admission/outbox primitives,
Temporal authority gating, scoped workers and native-intent/evidence controls.
Read-only VMware/AHV/OpenStack discovery components, signed mTLS result publication,
generation-pinned normalization and destination comparison have repository tests.

Portable planning, reviewed Terraform roots, native lifecycle/readback primitives,
guest/service handoffs and cross-scope transfer/integrity contracts are present.
They are not yet a fully composed admitted provisioning or migration workflow.
`AdmittedMigrationJob` verifies authority and stops at its gate result.

The registry explicitly covers 97 workload capability dimensions for every platform.
One package-owned vocabulary feeds registry and native qualification validators;
registry version 2 binds its digest. Compute/storage/recovery/service profiles now
supply mandatory workload capabilities, preserve every selected limitation and
reject ambiguous/malformed catalogue input. All platform tuples remain unselected
and no capability is native-qualified. Unsupported/deferred profiles stay refused.

## Removed obsolete runtime paths

The capability-registry and native-qualification script owners were moved into
`provisioner/qualification/registry.py` and `provisioner/qualification/native.py`.
All known consumers were migrated and the old files deleted, with retirement and
installed-package checks. No compatibility wrapper was retained. This is a partial
B05 closure, not a claim that every top-level owner has been relocated.

## Still unimplemented or unqualified

Complete native collector/profile/credential wiring, persisted dependency review,
scheduling/estate-scale discovery, admitted native provisioning, all guest/service
postconditions, independently bound data-transfer workers, source fencing, final
sync, cutover, post-write recovery and directed whole-VM route breadth remain open.
HA/DR, native security/failure/recovery campaigns, pilot and operating acceptance
must be demonstrated for the exact installed scope before release.

## Verification meaning

Use the current [RAD](current/RAD-adoption.md), [TAD](current/TAD-infrastructure.md),
[testing guide](TESTING.md) and execution plan together. Repository/unit/protocol
fixtures, real CI database tests, native qualification and production authorization
are distinct evidence. No native site, workload, credential or production data was
contacted or changed by this review. Historical signed evidence remains immutable.
