# Reviewed application comparison and combined capacity

Reviewed 30 September 2026. This B17/B19/B20 continuation follows the
[existing B01–B50 plan](../product/enterprise-workload-mobility-execution-plan.md).
It adds bounded application-wide **advice**, not a migration plan, reservation,
source adoption, data-transfer job or native execution grant.

## Exact retained inputs

The authenticated API exposes one read-only calculation endpoint:

```text
POST /v1/assessments/applications/compare
```

The closed request contains `source` (`environmentId`, `generation`),
`applicationGroupId`, `draftRevision`, `draftRecordDigest`, `memberProfiles`,
`destinations`, `method`, `networkMode` and `dataMode`. Each member profile has
exactly `workloadId` and `guestProfile`. Destinations use the existing comparison
selection: environment/generation plus optional exact capacity kind/native ID.
At least two distinct authorized destinations and all 2–100 retained application
members are required, with at most **200 member/destination combinations**.
Requests exceeding that bound are refused, not silently split or truncated.

Every declared member must appear once in `memberProfiles`. The server reads
native VM identities, membership, startup order, datasets and dependency assertions
from the exact retained draft. The caller cannot submit substitute members,
accepted-owner flags, native capability claims, tuple evidence or target capacity.
Mixed guest profiles are checked per member. Method/network/data selections are
common to this bounded comparison; heterogeneous per-member methods and split
placement across target pools are not implemented.

`ApplicationAssessmentService` in
`provisioner/controlplane/discovery/application_assessment.py` composes the existing
draft repository, independent signed owner-review service and assessment service.
Source and every destination are authorized before any draft or inventory is read.
The signed review must bind the selected immutable draft and original generation.
Unreviewed, revoked, stale, partial or superseded review inputs return
`HELD_APPLICATION_REVIEW`, with no application destination calculations.
Invalid signature/custody or contradictory retained bindings hold the request;
there is no fallback to older accepted evidence or browser-supplied approval.

## Shared comparison engine, not another native path

`AssessmentService.compare_many` uses the same implementation as the existing
single-VM comparison. Each member retains its guest-specific directed-route,
policy, security, recovery, hardware, driver and key checks. A blocked member
cannot disappear behind a successful sibling. Cross-family native relocation
blocks the affected destination without discarding other destinations.

Only immutable inventory hydration is cached within one call, under the exact
tenant, generation and installed tuple. Source and target generations are loaded
once, not once per VM. Authorization, latest-generation metadata and signed
route/control evidence are **not** cached. The service rechecks current installed
selections, evidence and generations after member evaluation; changed proofs and
revoked authority hold the report. Superseded or newly stale observations affect
all members, including ones evaluated earlier.

After comparison, the application service reconstructs the same reviewed candidate
from original observations and the retained proposal, checks its digest, and reads
the independent owner decision again. New drafts, inventory, owner decisions,
revoked keys or expired review cannot silently reuse the earlier acceptance.
The API finally reauthenticates the same human subject and every selected scope.
These are bounded live rechecks over immutable inputs, **not one atomic snapshot
across all databases, native platforms and independent trust services**. No result
can authorize a later effect without that effect's own fresh admission checks.

## Combined capacity and honest unknowns

Each destination places the entire application against **one selected observed
capacity identity**. Capacity in another cluster, pool or environment cannot fill
a missing or insufficient value. The baseline checks are:

| Dimension | Required value | Selected capacity observation |
|---|---|---|
| VM count | Number of retained members | `availableVmCount` |
| vCPU | Sum of normalized `vcpuCount` for every member | `availableVcpu` |
| Memory bytes | Sum of normalized `memorySizeBytes` | `availableMemoryBytes` |
| Logical disk bytes | Sum of normalized `diskCapacityBytes` | `availableStorageBytes` |

Each quantity must be an explicit bounded integer; booleans are not integers here.
Missing or invalid requirements and signed-64-bit sum overflow remain **unknown**,
not zero. Available VM slots are not inferred from vCPU/memory or a quota limit.
`availableVmCount` is an additional explicitly observed input consumed by this new
application calculation; existing normalizer/VM comparison semantics are unchanged.
A VM-slot observation does not prove all quota dimensions or placement feasibility.

For example, two observed four-vCPU VMs each fit a six-vCPU pool in individual
comparison, but their eight-vCPU application does not. The aggregate reports
`APPLICATION_VCPU_CAPACITY_INSUFFICIENT`, even if both member rows are eligible.
Tests exercise the equivalent memory, storage and instance-slot cases.

The disk sum is **logical provisioned per-VM demand**, not unique physical storage.
No shared-disk deduplication, thin-provisioning savings, CPU overcommit, temporary
conversion space, rehearsal copies, retained source, backup/replication footprint,
HA/N+1 headroom, anti-affinity admission or application performance is inferred.
Those inputs and actual reserve/renew/confirm/release remain B23 and later work.
The result explicitly sets `reservationHeld: false` and
`transientAndRecoveryFootprintIncluded: false`.

## Response and remaining application obligations

`hosting-application-comparison/1` retains the exact signed review, raw/normalized
source and destination bindings, and per-destination member status and issue codes.
The complete report is bounded to **1 MiB**; an oversized result is refused rather
than dropping members or problems. Member rows identify workload, native VM, guest
profile and evaluation time. Application metadata retains startup order and dataset/
consistency-group counts, not a newly approved execution DAG.

An unresolved dependency makes aggregate eligibility unknown. CMDB, guest or
monitoring labels do not prove independently verified external dependency evidence.
Even with every member eligible, the application stays **CONDITIONAL** pending
application-wide policy/data review and actual reservations. Group traffic,
consistency and outage objectives are not qualified by per-VM reviews.
Explicit blockers outrank unknowns, which outrank conditions. The top-level
`ASSESSED_NOT_AUTHORIZED` means calculations were produced, not that a destination
was approved. Every response denies ownership, execution and reservation authority.

No new migration, database table, SQL privilege, permanent workflow, native driver,
compatibility alias, CLI command or browser workflow is added. Existing operator
clients continue their supported per-VM and draft operations. An application-wide
browser/CLI selection experience and full migration planning remain future work.
The installed distribution includes the real calculation owner. Contract/HTTP tests
use synthetic inventories and real owner signatures; separate PostgreSQL tests use
the actual draft, signed-review and inventory repositories. Native route inputs in
these tests remain fixtures, not installed-platform qualification.

## Wave transition decision

Wave 2 is **not closed** by this increment. B14–B16 still need independent inventory
visibility and remaining image/hardware/security facts; B17 requires verified
external dependencies and deployed owner/key onboarding; B20 needs the complete
guided application workflow; B22 still needs scheduling/concurrency/freshness,
larger resumable publication and measured estate-scale acceptance.

Wave 3 B23/B24 must consume current assessment inputs, commissioned envelopes,
transactional capacity/IPAM/staging reservations and per-effect authority. This
increment supplies combined baseline demand for that handoff, not those owners.
Do not promote comparison output into an approved provisioning job or remove
remaining wave criteria to advance the status. No installed native platform or
production dataset was contacted during this repository work.
