# RAD-M01 — Reference adoption and deviation design

**Version:** 0.9 · **Status:** Proposed · **Accountable role:** Architecture authority.

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

### Semantic portability and research boundaries

The migration contract now includes typed capability properties beneath the existing
97 IDs. A feature name does not establish equivalence: routing context, policy
rule model, enforcement coverage, performance guarantees, encryption/key custody
and hardware preservation remain distinct requirements. Every selected profile
contributes constraints; incompatible intersections are rejected, never overridden.
The destination must enforce the source requirement or a demonstrably stronger
compatible requirement. Vendor documentation supports design assumptions, not
installed qualification or mutation authority.

See [verified research decisions](../engineering/platform-migration-research.md) and
[existing wave-plan delta](../product/enterprise-workload-mobility-execution-plan.md#8-research-driven-acceptance-and-implementation-delta).

### Persisted application drafts and attributed assertions

The control API now stores immutable, revisioned application proposals pinned to
an exact observed discovery generation. Selected members must be observed VMs;
partial inventory may support a draft but never an accepted or complete application.
The authenticated author and database time are separate from asserted owner IDs,
dependency sources and consistency groups. Unresolved dependencies remain visible.
Saving a draft creates no owner review, adoption, capability claim or execution grant.

The [application-draft contract](../engineering/application-drafts.md) defines the
actual package owners, scoped PUT/GET routes, expected-revision conflict checks,
original retry semantics, SQL migration and deployment grants. Source-generation
publication and draft creation share their cooperative lock; authority is rechecked
after waits and before commit. Exact retries retain original author/time; later
source generations are reported without relabelling history. The separate signed
owner-review path below evaluates exact-draft assessment decisions. Independent
enrichment verification, owner-facing workflow integration and B17 closure remain open.
The [operator continuation](../engineering/application-draft-operator.md) now supplies
bounded latest-draft listing and CLI save/load/history through the existing API.
Explicit source/revision pins and matching content acknowledgements prevent silent
rebase or success claims after an ambiguous PUT. Listing is a live page, not an
immutable export. Neither commands nor summaries accept ownership or migration.

### Bounded browser draft workspace

The [browser workspace](../engineering/application-draft-browser.md) now lists and
loads existing unreviewed drafts and edits name, proposed owner and startup order.
It retains the exact source/revision and every read-only membership, dataset and
dependency assertion. Historical/superseded records cannot be edited. Explicit save
confirmation, exact content acknowledgements and GET-only uncertain-save
reconciliation use the existing API; no browser action accepts ownership or launches
migration. Tab identity changes clear state and suppress late replies. Full browser
creation/evidence editing and owner-facing signing/review presentation remain open.
Independently signed review evaluation is provided by the separate service below.

### Independently signed application-owner decisions

The existing signed assessment store now accepts exact-draft `APPLICATION_REVIEW`
decisions from independently enrolled `APPLICATION_OWNER` subjects. Owner identity
must match the proposal and differ from its editor. Acceptance/revocation is bound
to the complete saved draft, inventory generation and proposal digest. Live trust,
revocation and scope are rechecked; newer drafts or inventory cannot inherit an old
review. No draft status, native ownership or execution approval is rewritten.

The scoped read-only review endpoint composes retained proof with the existing
application-candidate validator. Incomplete/stale inventory remains held and unknown
dependencies stay explicit; external dependency evidence remains unverified.
Migration 0022 and narrowly scoped ingest-role SELECT rights are required. See the
[signed owner-review contract](../engineering/application-owner-review.md) for
fields, locking, API states, deployment, tests and remaining application-wide
planning and owner-facing workflow integration.

### Operator inspection of signed owner review

The existing thin CLI now reads an exact draft's current signed owner-review status,
optionally checking its retained record digest. It preserves source/evidence/time
references and rejects contradictory status or authority claims without issuing
signatures, changing drafts or launching migration. A successful read of a hold or
revocation does not make it acceptance. The
[review command contract](../engineering/application-owner-review.md#inspect-the-review-from-the-operator-cli)
records exact request/response, tests and remaining signing/browser/application-wide
planning work. No new database migration, privileges or execution authority are added.

### Reviewed application comparison

The [application comparison contract](../engineering/application-comparison.md)
connects exact retained application drafts and independent owner decisions to the
existing per-member destination engine. Every member and guest profile is checked;
combined VM-slot, CPU, memory and logical-disk demand is checked against one selected
capacity identity. Missing facts, source changes, evidence revocation and unresolved
dependencies cannot disappear behind eligible member rows. No capacity is reserved,
no application-wide data/policy outcome is qualified, and no native work is admitted.

Inputs are immutable and current authority/evidence is rechecked, not represented
as an atomic estate snapshot. Results retain all members and exact source/review
bindings. B17/B19/B20 progress does not close Wave 2: independent visibility,
remaining native facts, verified external dependencies and B22 scheduling/scale
still precede wave closure. Wave 3 reserve/apply owners remain separate work.

## Engineering and implementation handoff

The TAD and selected solution inherit the approved baseline version, topology boundaries, sharing choices and service constraints. They identify which fields need actual supported values and which require architecture/security decisions. Independent controls such as physical OOB and key recovery need real owners and design artifacts, not references to an API reader.

## Acceptance and open work

Review the explicit scope inventory, current risks and unresolved values. Choose whether this new maintained record meets the service’s documentation need. That owner decision remains open; the repository can validate its completeness of structure, not supply authority.

Adopting authority and approval evidence: **not recorded**. Link the actual design review and its conditions when they exist; a code merge does not authorize a site or service. Keep sensitive site parameters and private credentials in their approved systems.

[Maintained design register](README.md) · [Decision register](../adr/README.md)
