# Commission a site and its workers

Procedure ID: OPS-COMMISSION. Owners: inventory and native platform/site owner; contributors: SRE, IAM/security, network/storage and shared-service owners. Scope: R08–R11/R13/R16/R17/R21/R31/R32; P04.01–P04.04, P07 and P09; Q02/Q05/Q06.

Commissioning establishes a site's usable, owned and evidenced scope. Registering an endpoint or successfully authenticating to it is only an input. Read-only discovery commissioning and permission for a specific native mutation remain separate decisions.

## Inputs

Record site/trust/residency boundary, accountable site/platform owners, endpoint identities, installed platform/API/backend/features/entitlements, compute/storage/network/failure-domain inventory, permitted tenant/domain scopes and capacity budgets. Identify management, data-transfer, backup and workload paths separately.

Obtain constrained read credentials, independently verified endpoint certificates/trust, enrolled worker artifacts/identities, approved network flows, collector budgets, fixture/scope for denied-path checks and an evidence destination. Supply actual DNS/IPAM/identity/time/PKI/backup/monitoring owner contracts and contacts through the restricted site record.

Use the [configuration/BOM](../configuration-and-bom.md) for installed values and [identity/trust](../identity-and-trust.md) for enrollment and revocation. Do not copy sensitive topology, credential references or live native inventories into repository examples.

## Read-only commissioning

| Step | Owner action | Expected observation and stop condition |
| --- | --- | --- |
| 1. Establish ownership | Site/platform owners identify who operates each endpoint/resource/service and which objects/fields may become managed | Unowned/externally managed scope remains observation-only; stop on ambiguous ownership needed for the intended capability |
| 2. Validate paths | Network/security verify exact approved control/management flows, trust, DNS/time and route symmetry as applicable | Required paths work; unintended egress/cross-boundary paths denied; no assumption that API reachability permits data transfer |
| 3. Enroll collector | Inventory/IAM bind artifact, worker identity, site/endpoint allowlist, read scope, queue and API budget | Trusted read-only handshake; wrong issuer/site/endpoint and expired worker denied; native mutation denied |
| 4. Discover generation | Collector records installed tuple, stable native IDs, timestamps, pagination, visibility scope and completeness | Complete generation or explicit partial/unknown coverage; throttle/retry respects endpoint budget |
| 5. Reconcile coverage | Platform owner compares scoped independent native observations with discovered counts/identities and hidden privilege boundaries | Missing pages or inaccessible resources remain unknown; absence from incomplete discovery creates no deletion inference |
| 6. Record topology | Inventory links actual transport/compute/storage/edge/management and failure-domain records | Logical tenant/WSD/domain intent stays separate from native realization; resource IDs preserve native scope |
| 7. Exercise interruption | Operators revoke a test collector or interrupt approved test connectivity, then recover its read-only session | No extra authority; old registration denied; stale/partial data and refresh state remain explicit |
| 8. Review discovery scope | Inventory/platform owner records accepted read coverage, freshness bounds, limits and next refresh | Only the reviewed scope becomes usable input; no qualified native write claim is created |

## Native readiness extension

Before a site is eligible for a planned write, the responsible owners provide the following observations for the exact intended capability and tuple:

| Domain | Required readiness record |
| --- | --- |
| Compute and resilience | Eligible placement, quotas, surviving capacity, maintenance/HA constraints and accepted failure domains |
| Storage and data | Required block/file/object characteristics, keys, snapshots/backup/restore, staging and retained-source budgets |
| Tenant networks/security | Routing/address/MTU/domain bindings, mandatory isolation, protected selectors, ZIP/edge/inspection capacity and return paths |
| Guest/service usability | Guest image/readiness scope and DNS/IPAM/identity/time/trust/logging/monitoring/backup owner interfaces and receipts |
| Worker mutation scope | Separate infrastructure/guest/service/data identities, allowed actions/endpoints, short-lived authority and effective fencing |
| Recovery/stop | Verified containment path, uncertain-effect readback, evidence delivery, reservation reconciliation and authorized recovery method |
| Qualification | Exact operation/method/guest/data/policy/topology/artifact claim, limitations, freshness/retest triggers and reviewer reference |

An isolated authorized native campaign may evaluate a candidate tuple before qualification exists. That campaign has separately bounded endpoint/data/credential/impact scope and cannot authorize routine operational admission. Ordinary work requires current qualification plus its own approved plan and current authority.

## Change and failure handling

On changed API/backend version, entitlement, trust, network/storage realization, resource ownership or material capacity/failure topology, record a new site revision and qualification impact. Hold affected eligibility until required observations are refreshed; an endpoint hostname staying the same does not prove compatibility.

If read authority is unexpectedly broader than commissioned scope, hold that collector, restrict/revoke its credential and review captured evidence access. If mutation occurred unexpectedly, fence the affected writer and use [recovery](recovery.md) to establish native outcomes before any further operation.

On partial discovery, retain the last valid generation with explicit age and distinguish new incomplete observations. Do not merge incomplete generations into an apparently complete inventory or tombstone unseen resources. Use the platform owner's coverage reconciliation to determine the next bounded collection.

## Evidence and closure

Record site/endpoint/worker/configuration revisions, accepted discovery scope, native ownership maps, allowed/denied identity/network checks, completeness reconciliation, freshness/budget values, dependencies and owner decisions. Native enablement additionally needs actual safety/policy/service/recovery and qualification evidence.

Publish only the accepted scope and limitations to authorized operators. Schedule refresh and re-review using the recorded expiry/change triggers. Do not represent this procedure's completion as support for another tenant scope, native platform version, migration direction or untested data path.
