# ADR-016 — Native API plans and resource ownership

Owner role: Infrastructure lead. Related phases: P00, P05, P06, P07, P08.

Origin: `DESIGN`. Disposition: `ACCEPTED` in the [decision register](decision-register.md).

## Context

An approved operation identifies its exact platform resources, API contracts,
requested changes, dependencies and accountable writer. Provider acceptance and
application readiness are separate observations. Interrupted requests can have
effects even when no response reaches the worker.

## Decision and scope

Provisioning, modification, recovery and retirement use native platform APIs.
Planning produces an immutable native operation plan; Lifecycle is the sole
product writer for its explicitly owned resources and fields. OpenStack adapters
call Keystone, Nova, Neutron, Cinder and Glance directly. VMware adapters use the
vSphere APIs. The product contains one execution path for each admitted operation.

Each plan binds tenant/site/project, confirmed Inventory configuration revision,
installed API/capability tuple, adapter and contract digests, object identities,
resource generation, approved payloads, dependency order, ownership, expiry,
campaign and independently administered custody epoch. Credentials are resolved
through protected workload identities and never included in plan content.

Inventory pulls installed API versions, enabled features and configured options.
Console administrators validate those observations, explain permissible
interpretation overrides and supply only facts that cannot be discovered.

## Ownership and execution

- A resource/field ownership map names one authoritative writer. Adoption requires
  explicit owner approval and independent object matching before any mutation.
- Lifecycle and its worker maintain append-only operations, per-request intent,
  provider request/object identifiers and independent observations. These are the
  product's durable state; native objects remain authoritative for observed state.
- Every request is bound to the approved plan and current scoped authority.
  Persist intent before submission, check authority at each privileged boundary,
  and hold accepted-but-unconfirmed work without automatic replay.
- Native asynchronous tasks are polled by exact identity within bounded deadlines.
  A timeout, credential expiry, local process exit or empty listing does not prove
  provider quiescence or safe absence.
- Independently administered fencing excludes stale writers and accepted requests
  before recovery or another generation can write. Restoring a product database
  cannot restore old write authority.

## Acceptance and validation

Wrong scope, plan digest, object ownership, configuration revision, API contract,
generation or custody epoch must fail before mutation. Exercise response loss,
partial acceptance, restart, asynchronous failure, revocation, drift and competing
writers through real transport/database tests and the commissioned native campaign.
Verify exact native objects independently before service enrollment or activation.
Retirement has separate authority, retention/key checks and independently observed
deletion before allocation release.

Migration uses the native export/import route in [ADR-014](adr-014-first-native-provisioning-and-migration-slice.md).
Unsupported API, disk, firmware, guest or security combinations remain ineligible.
No alternate tool or migration method is selected automatically.

## Qualification inputs

Commission the actual endpoint/trust/identity scope, installed APIs, adapter images,
object ownership, request-fencing mechanism and independent observer. API discovery
and an accepted plan do not establish native qualification. G07/G08 require original
native observations and the applicable receiving decisions.

## Revisit conditions

API semantics, ownership, consistency boundaries or provider exclusion change, or
an installed capability cannot satisfy the approved operation's postconditions.

## Related records

- [Decision register](decision-register.md)
- [Native workflow control](../operations/runbooks/native-workflow-control.md)
- [Phased implementation plan](../implementation/phased-plan.md)
