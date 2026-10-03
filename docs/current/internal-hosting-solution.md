# SOL-M01 — Internal two-tenant protected workload solution

**Version:** 0.5 · **Status:** Proposed · **Accountable role:** Hosting solution architect.

## Scope and authority

A maintained internal two-tenant reference solution for isolated provisioning and application migration; fixture values are not current allocations or service promises.

This is a newly authored maintained Markdown record, not a reconstruction of an unavailable Word original. Its creation date is not an acceptance date. Source basis: [WD §2](../solutions/internal-protected-workload/2-reference-decisions-and-infrastructure-boundaries.md) · [WD §5](../solutions/internal-protected-workload/5-dedicated-handoff-inventory-and-route-ownership.md) · [WD §9](../solutions/internal-protected-workload/9-build-sequence-with-explicit-acceptance-dependencies.md) · [RA §28](../architecture/reference/28-architecture-acceptance-and-verification.md).

## Design content

Use the source’s two tenants and independent OZ/RZ domains to exercise tenant isolation, one explicitly approved application path, scoped service consumption and deny-by-default exposure. Retain the original worked resource/address/route schedules rather than copying disconnected values into this record. They are documentation fixtures, not current allocations.

The path is workload → native gateway → domain-specific security context → approved receiving context → workload, with a corresponding accepted reply. Shared resolver replies select the originating tenant context. Native connected routes, defaults, same-host forwarding and shared attachment neighbours cannot be presumed to follow a diagram.

Require the selected image/template, storage/placement profile, mandatory policy, permitted bootstrap clients and protection/key dependencies before admitting a workload. Network disconnection and guest power state are distinct properties on each stack. A native task completion or matching API projection does not prove quarantine or readiness.

Tests need healthy control endpoints and a temporary same-domain probe when a fixture otherwise has only one endpoint per domain. Account for temporary test demand and cleanup; do not describe route absence as firewall denial.

### Operator provisioning and migration scenario

Use the existing two-tenant internal fixture to exercise isolation and planning
across all three platform families without inventing installed site parameters.
An operator selects reviewed profiles, receives explicit requirement/unknown-fact
blockers, compares eligible destinations and creates an immutable proposed plan.
The capability catalogue now covers compute/storage/guest/data/service/operation
requirements as well as networking. Every selected profile's limitations must be
visible; a successful synthetic placement remains unauthorized.

The first application-migration scenario in the execution plan is rebuild/restore,
not arbitrary transparent VM mobility. Bind every workload, dataset, dependency,
source/target native scope and approved directed route. Construct an isolated target,
rehearse restore and service readiness without production side effects, then require
source quiesce/fencing, final synchronization and independent activation evidence.
The current admitted workflow does not yet execute that complete chain. Whole-VM
capture/conversion, Windows and additional directions need their own implementation
and qualification, not a renamed fixture.

### Site engineering and qualification inputs

Supply actual installed product/API/provider/hardware/licence tuples, native resource
IDs, compute/storage/network constraints, credential scopes and service-owner
agreements through controlled operator systems. Address preservation, disk/NIC order,
firmware, secure boot, vTPM, accelerators, shared disks and guest dependencies must be
assessed explicitly. Missing facts hold the affected strategy. Do not infer that a
feature exists merely because the platform profile contains its capability row.

Service usability requires accepted DNS, identity, time, trust, logging, monitoring
and backup/restore outcomes in addition to VM reachability. Retain the selected
policy/route equivalence assessment and the separate activation decision. After
target writes, use a qualified reverse-sync/restore/repair path; retain the source
until its declared retention and retirement gates are met.

### Current evidence boundary

The reviewed example corpus still contains five requests across three platform
realizations. Catalogue changes regenerate their resolution, placement, desired-state
and plan fingerprints; the examples remain `PLANNED_DISABLED_NOT_AUTHORIZED` with
no native contact. The [all-waves plan](../product/enterprise-workload-mobility-execution-plan.md)
and [current TAD](TAD-infrastructure.md) distinguish implemented components from the
unfinished native workflow and operating acceptance.

### Explicit profile semantics in internal examples

Internal reference profiles now require independent routing contexts, enforced
deny-default gateway policy and x86_64 compute; profiles selecting distributed
firewalling also require enforcement across every selected workload NIC. Test
inventory supplies explicit per-cluster properties solely for disabled planning.
No source profile is weakened to fit a target. Unknown hardware/key/service facts
must be observed and reviewed before a migration comparison becomes useful;
application rebuilding is distinct from preserving an opaque whole VM.

See [verified research decisions](../engineering/platform-migration-research.md) and
[existing wave-plan delta](../product/enterprise-workload-mobility-execution-plan.md#8-research-driven-acceptance-and-implementation-delta).

### Catalog and discovery correction — 1 October 2026

Availability catalog 18 distinguishes security zones from physical failure domains;
no zone name establishes HA, restart reserves or recovery. Typed requirements now
reject malformed flags/quantities and insufficient workload counts; independent-site
recovery remains unsupported. New catalog digests require regenerated examples and
fresh plan review. All five-request/three-platform examples stay disabled.
OpenStack collector selector 3 preserves bounded native allocation/image/attachment
facts without converting them into qualification. The [current research review](../engineering/platform-capability-review-2026-10-01.md)
records these changes and remaining coverage. No deferred public, encryption, GPU,
whole-VM, provisioning or migration capability is enabled by this correction.

## Engineering and implementation handoff

Bind the worked source’s identities to actual accepted allocations only in the site engineering package. Map each applicable assertion to the allocation register. Use real native tests for selected stacks and dependencies after engine validation. The activation decision follows required initial operational/recovery readiness.

## Acceptance and open work

No production exposure or service SLO is granted. Actual platform/edge selection, owner-reviewed scope, data consistency, restore, retirement and operational acceptance remain required.

Adopting authority and approval evidence: **not recorded**. Link the actual design review and its conditions when they exist; a code merge does not authorize a site or service. Keep sensitive site parameters and private credentials in their approved systems.

[Maintained design register](README.md) · [Decision register](../adr/README.md)

## Commissioning working material

The [native reference-service kit](../implementation/native-reference/README.md) elaborates this maintained solution into site-input collection, per-stack build responsibilities, actual service-client paths and W14 observation worksheets. It changes no selected topology or approval state; actual site and native execution remain unrecorded.
