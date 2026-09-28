# RAD-M01 — Reference adoption and deviation design

**Version:** 0.2 · **Status:** Proposed · **Accountable role:** Architecture authority.

## Scope and authority

Reference adoption for enterprise workload mobility and secure hosting across qualified on-premises environments; no site-specific control assessment or production acceptance is implied.

This is a newly authored maintained Markdown record, not a reconstruction of an unavailable Word original. Its creation date is not an acceptance date. Source basis: [RA §1](../architecture/reference/1-purpose-scope-and-architectural-authority.md) · [RA §7](../architecture/reference/7-tenant-environments-and-security-domain-placement.md) · [RA §29](../architecture/reference/29-architecture-decisions-and-alternatives.md).

## Design content

The available proposed baseline is the v1.4 infrastructure reference and linked delivery-kit v1.1 engineering. Adopt its physical/logical views as a versioned set, then identify service demand, independent information impacts, eligible locations, assurance sharing and required native platform profiles. Do not equate Tenant Namespace, WSD, security-domain intent and native domain instance.

Every variation names the original requirement/decision, requested scope, competing options, route/data/management consequences and accountable authority. Existing proposed ADRs explain why the base design uses commissioned cells, local overlays, explicit ZIP mediation, scoped services and separated administration. Acceptance must record actual applicability and exceptions, not rewrite source history.

The source-scope inventory records previously described but unavailable originals. This newly identified record covers adoption guidance without asserting that the missing RAD file was recovered. Unresolved file recovery and organizational adoption are different conditions.

### Workload mobility product boundary

The product is one authenticated operator control application for administrators
assessing, provisioning and moving workloads between qualified on-premises VMware,
Nutanix and OpenStack environments. Browser and CLI clients use the same durable
records and authority. A workload/application identity, its datasets and dependency
group are not the WSD: the WSD remains the tenant security and placement boundary.
A vendor-native domain is a realization of that boundary, not its portable identity.

The reference architecture still supplies commissioned fabric cells, locally owned
overlays, tenant VPC/domain isolation, ZIP mediation and independently governed
shared services. The control application coordinates accepted changes to those
resources; it does not replace their accountable owners or flatten their trust
boundaries. Provider-specific APIs remain behind typed native adapters. Removing
obsolete entry points must not remove independent observation or one-writer safety.

### Capability and placement architecture

A selected platform family is insufficient evidence for placement. Match the exact
installed product/API/provider/hardware/licence tuple and current qualification
against every required compute, storage, network, security, guest, discovery,
migration, service and operational capability. The programme now represents 97
such dimensions in one package-owned vocabulary. Every platform must declare every
row explicitly; omitted and unknown requirements are rejected, not downgraded.

The grouped vocabulary digest is bound into the engineering registry. Portable
profile versions and the complete catalogue digest are bound into derived plans.
Compute, storage, recovery and service requirements participate in eligibility;
network support alone cannot qualify a useful workload. Preserve every selected
profile's limitations through resolution. A resolvable profile is a policy
expansion, not an assertion of installed feature support or successful execution.

Keep source implementation state, native capability qualification, directed
migration-route qualification and live mutation authority separate. The current
registry has unselected installed tuples and no native-qualified claims. Newly
enumerated dimensions remain explicitly unassessed. The deferred GPU, encryption,
public-exposure and address-family profiles are not enabled by enumeration.

### Authority, discovery and migration invariants

Scope requests, inventory generations, immutable plans, approvals, jobs and evidence
to the organization, tenant and relevant native environments. The durable database
is the business authority; Temporal is the workflow engine, not a second approval
ledger. Use transactional admission/outbox dispatch, fresh per-effect checks,
resource intents, bounded worker grants and independently reconciled native IDs.
An ambiguous native result retains the hold; a process exit is not a fence.

Discovery is read-only authority. Preserve original signed campaign/result bytes,
collector identity, exact native scope, freshness and completeness before publishing
a generation. A result, inventory comparison or owner grouping proposal cannot
implicitly adopt resources or grant mutation rights. Scope incomplete disk, NIC,
firmware, policy and dependency facts as unknown and expose their impact to operators.

Migration is preservation of an application outcome: datasets and metadata, guest
identity, policy, routes, shared services, consistency and recovery. Rebuild/restore
and whole-VM movement are distinct strategies. Each directed route requires its own
source capture, target reconstruction, isolated rehearsal, source-writer exclusion,
final synchronization and independent activation postconditions. After target
writes, recovery requires a reviewed reverse-sync/restore/repair decision; simply
restarting the old source is not a general rollback.

### Implementation and acceptance boundary

The current repository contains control-plane foundations, signed discovery and
comparison paths, disabled portable planning, native execution primitives and
transfer/evidence contracts. It does **not** contain a complete admitted provisioning
or migration workflow. The admitted Temporal workflow currently verifies authority
and returns a gate result; it must not be described as executing the native chain.

Use the [all-waves execution plan](../product/enterprise-workload-mobility-execution-plan.md)
for B01–B50 closure. Repository code, automated checks, installed native qualification
and operational acceptance are four separate evidence columns. Prior W/C ledger
completion and current CI success do not close this product programme.

## Engineering and implementation handoff

The TAD and selected solution inherit the approved baseline version, topology boundaries, sharing choices and service constraints. They identify which fields need actual supported values and which require architecture/security decisions. Independent controls such as physical OOB and key recovery need real owners and design artifacts, not references to an API reader.

## Acceptance and open work

Review the explicit scope inventory, current risks and unresolved values. Choose whether this new maintained record meets the service’s documentation need. That owner decision remains open; the repository can validate its completeness of structure, not supply authority.

Adopting authority and approval evidence: **not recorded**. Link the actual design review and its conditions when they exist; a code merge does not authorize a site or service. Keep sensitive site parameters and private credentials in their approved systems.

[Maintained design register](README.md) · [Decision register](../adr/README.md)
