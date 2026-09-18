# SOL-M01 — Internal two-tenant protected workload solution

**Version:** 0.1 · **Status:** Proposed · **Accountable role:** Hosting solution architect.

## Scope and authority

A newly maintained selection view of the existing two-tenant OZ/RZ reference fixture; no fresh addresses or service promises are invented.

This is a newly authored maintained Markdown record, not a reconstruction of an unavailable Word original. Its creation date is not an acceptance date. Source basis: [WD §2](../solutions/internal-protected-workload/2-reference-decisions-and-infrastructure-boundaries.md) · [WD §5](../solutions/internal-protected-workload/5-dedicated-handoff-inventory-and-route-ownership.md) · [WD §9](../solutions/internal-protected-workload/9-build-sequence-with-explicit-acceptance-dependencies.md) · [RA §28](../architecture/reference/28-architecture-acceptance-and-verification.md).

## Design content

Use the source’s two tenants and independent OZ/RZ domains to exercise tenant isolation, one explicitly approved application path, scoped service consumption and deny-by-default exposure. Retain the original worked resource/address/route schedules rather than copying disconnected values into this record. They are documentation fixtures, not current allocations.

The path is workload → native gateway → domain-specific security context → approved receiving context → workload, with a corresponding accepted reply. Shared resolver replies select the originating tenant context. Native connected routes, defaults, same-host forwarding and shared attachment neighbours cannot be presumed to follow a diagram.

Require the selected image/template, storage/placement profile, mandatory policy, permitted bootstrap clients and protection/key dependencies before admitting a workload. Network disconnection and guest power state are distinct properties on each stack. A native task completion or matching API projection does not prove quarantine or readiness.

Tests need healthy control endpoints and a temporary same-domain probe when a fixture otherwise has only one endpoint per domain. Account for temporary test demand and cleanup; do not describe route absence as firewall denial.

## Engineering and implementation handoff

Bind the worked source’s identities to actual accepted allocations only in the site engineering package. Map each applicable assertion to the allocation register. Use real native tests for selected stacks and dependencies after engine validation. The activation decision follows required initial operational/recovery readiness.

## Acceptance and open work

No production exposure or service SLO is granted. Actual platform/edge selection, owner-reviewed scope, data consistency, restore, retirement and operational acceptance remain required.

Adopting authority and approval evidence: **not recorded**. Link the actual design review and its conditions when they exist; a code merge does not authorize a site or service. Keep sensitive site parameters and private credentials in their approved systems.

[Maintained design register](README.md) · [Decision register](../adr/README.md)

## Commissioning working material

The [native reference-service kit](../implementation/native-reference/README.md) elaborates this maintained solution into site-input collection, per-stack build responsibilities, actual service-client paths and W14 observation worksheets. It changes no selected topology or approval state; actual site and native execution remain unrecorded.
