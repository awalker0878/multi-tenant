# Foundation services: actual clients, paths and ownership

**NRC-M01 supporting engineering schedule — Proposed.**
Parent: [ICD-M01](../../current/interface-agreements.md). Complete one controlled record
per **actual client and operation**, not one universal `dns: true` or `backup: true`
flag. The producer may be shared while its consumer scopes remain isolated.

| Interface | Consumer to identify in the actual design | Path, entitlement and prohibited shortcut | Failure / lifecycle evidence |
| --- | --- | --- | --- |
| Recursive DNS | Each guest, platform host, control service and approved proxy that resolves names | Permitted resolver endpoints and actual domain/management source path; UDP/direct TCP/fallback tested separately; recursion is not authoritative registration | Resolver loss/return path, cache and selected resolver behaviour; stale names/reuse handled by the name owner |
| Authoritative registration / address allocation | Address/name automation and its approved record owner | Exact allocation/name scope and native write authority; no guest authority to allocate arbitrary ranges or update provider names | Conflicting claims, lost replies, tombstones/quarantine and release only after dependent cleanup; existing DNS tooling is not IPAM |
| DHCP / metadata / initialization | Selected guest or platform-specific initialization client | Record whether each service is used at all; accepted options, identity and placement-specific reachability; no invented universal DHCP/metadata path | First boot, renewal/rebuild and loss recovery; reject unauthorized source/options and remove temporary initialization grants |
| Time | Each client needing the selected time/trust profile | Select the actual protocol, server and protection instead of assigning a port from the service name | Detect offset/loss under the accepted limits and confirm time-dependent identity/certificate behaviour after recovery |
| Image / package distribution | Installer, host, workload clone or guest updater as actually used | Verify image/template origin and integrity; distinguish management retrieval from guest bootstrap; no unrestricted egress merely to obtain an image | Revocation/update/rollback support, image availability during rebuild and declared exit limitations |
| Identity / PKI | Human admin, runner, host, proxy and guest clients separately | Authentication scope does not imply resource entitlement; protect enrollment and administration separately from use | Rotation, old-credential withdrawal, expiry/revocation and independently recoverable minimum trust |
| KMS / key custody | Actual hypervisor, storage service, backup service or guest consumer | Do not invent a guest KMS route when the native host/storage service is the consumer; separate key use, administration, recovery and destruction | Key-service outage, retained-data access, accepted recovery material and prevention of plaintext fallback |
| Telemetry and audit | Native platform/edge/service/runner collectors and workload agents separately | Ingestion and attribution remain distinct from log administration/query/delete authority; do not rely solely on a cooperative guest | Expected event arrival, identity correlation, buffering/backpressure, collection-loss alert and approved operational restrictions |
| Hypervisor-mediated disk I/O | Host/controller and native storage service | This is not a guest-routed service flow through the tenant ZIP; separate datastore/container/volume attachment and backend replication/admin authority | Foreign attachment/copy prevention, rebuild load, retained volume/copy ownership and eligible restore placement |
| Guest file/object/data endpoint | Actual guest identity and entitled share/bucket/object/dataset | Network/TLS success is not data entitlement; test authorized operations against the specific resource and deny another tenant's object and service administration | Session/credential changes, data consistency, failover semantics and retained-copy lifecycle |
| Backup orchestration | Actual backup coordinator/proxy and platform API identity | Protected management path for snapshots/capture control; not inherited by guest backup consumers | Scoped capture authority, lost operation discovery, snapshot cleanup and catalogue recovery |
| Backup data transfer | Actual agent/proxy/host/storage transfer mechanism | Select the native supported transfer mode and its endpoints; distinguish traffic from management and from ordinary guest access | Throughput under failure, independent retention/delete authority, useful-data restore and cleanup of temporary mounts/proxies |
| Hardware / platform administration | Authorized administrator, foundation runner and break-glass custodian | Separate management/OOB controls and identity; workload-to-management denial is tested against a healthy management endpoint | Covered fault recovery, audit continuity and removal of temporary/supplier grants |

The table elaborates [shared-service placement](../../architecture/shared-services/1-shared-service-placement-and-consumption-boundaries.md),
[initialization profiles](../../architecture/shared-services/2-name-time-initialization-and-telemetry-profiles.md),
[key recovery](../../architecture/shared-services/3-identity-certificates-keys-and-independent-recovery.md),
[storage/copy ownership](../../architecture/shared-services/4-storage-copies-and-retained-data-ownership.md)
and [backup/restore](../../architecture/shared-services/5-backup-capture-independent-protection-and-isolated-restore.md).
It does not select a product-specific protocol where the sources leave that open.

## The record each pair of owners needs

Identify the exact producer/service instance, actual consumer and resource operation,
source domain or management path, family and selected protocol, native attachment,
forward and return route ownership, enforcement and logging points, credential/trust
custodian, capacity units, retry/session/backpressure behaviour and recovery order.
Record configuration generation and the acceptance references held by both owners.

For a shared resolver or other endpoint, explicitly show how a reply selects the
originating tenant context. A route to the shared-services subnet is not authorization
for every service or administration endpoint in it. Avoid a third-domain transit path
through the service network. Where mediation or translation is necessary, document its
identity, logging, state/failure and reply-routing consequences rather than hiding it.

## Minimum acceptance experiment

First prove the client and approved endpoint/resource are healthy and observed. Then
exercise the authorized operation, an unauthorized endpoint/operation, another tenant's
resource, and any separately prohibited management interface under approved test scope.
Correlate client outcome with native policy and service evidence. An unreachable target
or absent route alone cannot distinguish deliberate enforcement from unrelated failure.

Repeat family, placement and failure variants that the actual offered service requires.
An IPv4 resolver result cannot qualify an IPv6 path. Record client/producer changes that
invalidate earlier evidence. These are planned experiments; none was performed on a
native environment by publishing this document.

[Kit index](README.md) · [Campaign method](campaign.md)
