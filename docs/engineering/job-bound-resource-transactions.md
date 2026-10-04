# Job-bound resource transaction composition

The installed `provisioner.allocations.transactions` owner now connects admitted
jobs to the existing capacity database. `capacity_owner` is the former live owner,
relocated with its same reservation/envelope/event tables. `capacity_demand` is
the same native-shape sizing implementation. There is no additional allocation
database, competing capacity authority or generic execution journal.

## Immutable selection and current admission

`PoolDemand` serializes the reviewed sizing catalogue and workload inputs at
construction, so later caller dictionary edits cannot alter their interpretation.
Every selected pool includes its seven-field `PlanScope`, current commissioned
envelope digest, accepted sizing and explicit workload, staging, snapshot and
retained-source resource components. Workload demand derives from the actual
selected flavors, placement and disk sizes; decimal memory/storage owner units
round upward. Temporary and retained budgets are explicit additive charges.
Combine purposes before charging one native pool. Do not reserve an already
accounted baseline source footprint again without an owner's deliberate envelope
accounting decision.

`ResourceBundle.digest` hashes workload identity/revision and resource selection
only. It excludes the admitted job, plan digest and execution-artifact digest,
which prevents the plan → execution artifact → resource bundle dependency from
hashing itself. At reservation time, `hosting-capacity-request/2` records the
admitted job, exact plan revision/digest, authority epoch and native scopes beside
the selection/demand/sizing/envelope digests. Stable reservation IDs are scoped
to admitted job and native pool; changed requests cannot rebind an existing ID.

`PostgresResourceAuthority` locks the admitted job and reuses the existing
authoritative approval revalidation. It requires a running job, unchanged start
payload, exact canonical plan/workload/native scope and a protected execution
artifact whose `resourceBundleDigest` matches this selection. The server-side
selection store is a required custody owner; a queue does not supply filenames or
resource approval booleans. Legacy plans without the explicit execution selection
remain ineligible. The PostgreSQL authority context remains open through each
short SQLite accounting transaction, serializing revocation with that effect.

## Admission, renewal and occupancy

| Action | Required current evidence | Owner result |
| --- | --- | --- |
| Reserve | Selected commissioned envelopes, native sizing, exact admitted plan and tenant/pool budgets | All selected pools commit together in the one database, or none commit |
| Renew | Same immutable resource request, current commissioned envelope/demand and current plan authority | Speculative lease extends; accounting remains charged |
| Inspect | Current scoped plan/execution selection and original request | Retained owner receipt; no native claim or mutation |
| Require readiness | Current scoped authority, catalogue/envelope and unchanged live receipt | Expired speculative hold blocks creation while its charge remains retained |
| Confirm | Fresh independently verified native identity/occupancy evidence covering workload and retained-source demand | Same charge becomes confirmed, without speculative expiry |
| Release | Fresh independently verified complete cleanup/no-effect evidence, zero occupancy and coverage of every confirmed native identity | Charge is released; original reservation identity remains terminal |

UNKNOWN and IN_PROGRESS are unconditional holds. Native timeouts, lease expiry,
missing tasks, failed jobs and copied success flags never release capacity.
The evidence port must authenticate observation custody and re-read native state,
operation uncertainty and old-worker exclusion when no effect is claimed. Merely
constructing `ResourceObservation` does not verify evidence. There is no permissive
default implementation. Every receipt keeps native acceptance and production
activation false.

## Authoritative IPAM composition

`NetBoxResourceTransactions` delegates effects to the existing NetBox allocation
owner and existing address ledger. `bind_selection` adds runtime job generation,
operation and capacity-parent references to a plan-independent protected address
selection. Allocation must match the reserved capacity's scope and an immutable
workload member. The current execution artifact must select the exact IPAM
allocation. Native address reservation starts only after resource admission;
address activation requires independently observed and confirmed native resource
occupancy. Address retirement/reuse follows observed resource cleanup and the
NetBox owner's DNS withdrawal, cleanup and reuse-quarantine procedure.

The adapter uses the selected NetBox 4.7 API, scoped v2 token, explicit HTTPS trust,
native uniqueness, conditional writes and durable uncertainty marker. A lost
successful POST remains uncertain in the address owner and retains the capacity
charge. Reconciliation reads the original allocation instead of repeating POST.
Dependent work consumes the exact current owner receipt only after namespace,
ownership, native allocation and ledger-head readback. No copied receipt or source
expiry grants reuse. IPAM and capacity effects deliberately do not pretend to be
an atomic remote transaction.

## Verification and remaining qualification

`tests/test_resource_transactions.py` executes real SQLite transactions and event
replay: multi-pool rollback, immutable selection, stale/revoked admission refusal,
expiry/renewal accounting, verified occupancy bounds and complete cleanup. Its
admission/readback authorities are local-only fixtures.
`tests/test_ipam_resource_transactions.py` executes the actual package IPAM adapter,
real loopback TLS and both existing owner stores with synthetic NetBox responses;
it covers pre-contact refusal, parent/selection binding, confirmed lifecycle,
foreign ownership and lost successful POST without a second mutation.

The selected application workflow now composes this owner through
`FileResourceBundleStore`, current `PostgresExecutionAuthority` and immutable
execution selection. Its OpenStack creation owner binds the exact counted
resource receipts before a native intent can be claimed; see
[planned native creation](planned-openstack-creation.md). Actual PostgreSQL
resource-authority revocation cases are included in `test_planned_creation.py`
and require the isolated PostgreSQL campaign environment.

Local results do not qualify PostgreSQL runtime permissions, a deployed capacity
owner, NetBox privileges/conditional-update support or native platform occupancy.
The first migration still needs selected-site capacity commissioning, independently
enrolled resource/worker-fencing observers, actual cleanup, failure/recovery
campaigns, retained-owner-state conversion and native acceptance.
