# ICD-M01 — Infrastructure interface ownership and service agreements

**Version:** 0.4 · **Status:** Proposed · **Accountable role:** Producing and consuming infrastructure owners.

## Scope and authority

Producer/consumer obligations across operator, discovery, workflow, native execution, data transfer, evidence and shared-service ownership boundaries.

This is a newly authored maintained Markdown record, not a reconstruction of an unavailable Word original. Its creation date is not an acceptance date. Source basis: [RA §8](../architecture/reference/8-zone-interfaces-routing-and-security-edge-topology.md) · [NBD §6](../engineering/network-boundaries/6-issue-an-interface-control-and-handoff-record.md) · [SVC §1](../architecture/shared-services/1-shared-service-placement-and-consumption-boundaries.md).

## Design content

For each interface identify producer, actual client, native endpoint, permitted operation, address family, trust material, resource entitlement, initiation/reply path, MTU/packet budget, capacity and security boundary. Record data-path and management-path ownership separately. A shared endpoint does not authorize a tenant to administer its backing service.

The agreement identifies version/feature compatibility, failure detection, retry/backpressure, log attribution, identity/key expiry and recovery order. Define who can change a next hop, firewall scope, service credential or data object, and which observer can independently verify it.

Use a bounded allocation and lifecycle reference across owners rather than credentials or large state dumps. Include expected generation, operation identity and safe stopping conditions for partial success. Name release/retention conditions before reusing an address, attachment, service identity or data copy.

### Control-application interfaces

| Boundary | Required binding and refusal condition |
|---|---|
| Operator to API | Verified organization/tenant identity, entitlement, immutable plan revision/digest, applicable approval and revocation state. A browser/CLI parameter is not authority. |
| API to workflow | Committed job and transactional outbox, exact workflow/run binding and idempotency identity. Dispatch success is not native completion; admission does not approve arbitrary later effects. |
| Collector to discovery ingest | Separate read-only mTLS identity, signed campaign/result, independent native credential witness, exact scope, completeness and freshness. Retain original signed bytes; a discovery credential cannot mint a write grant. |
| Site worker to native owner | Approved operation/resource identity, bounded grant, resource claim and durable intent. Expiry, scope change or uncertain completion prevents a blind retry. |
| Native owner to observer | Exact native IDs and task/attempt identity, independently observed postconditions and complete observation scope. An echoed request or task acknowledgement is insufficient. |
| Source to data-transfer worker | Original repository/snapshot/dataset identity and signed source receipt, separate target binding, integrity/metadata policy and consistency-group membership. Never reconstruct source evidence from target claims. |
| Workload to shared-service owner | Scoped endpoint, operation, entitlement and accepted service outcome. Consuming a resolver, identity service or backup repository does not grant provider administration. |
| Evidence producer to custodian | Original signed content, digest, scope, issuer, validity and controlled retention. Local test artifacts cannot populate native qualification as if they were site observations. |

These are contract obligations, not a statement that every interface is fully wired.
In particular, the admitted workflow still stops at its authority gate and the data
transfer path still needs independent native target/root and worker-authority
composition. Record those gaps instead of presenting a handoff document as execution.

### Versioning, qualification and ownership

The registry now uses a digest-bound 97-dimension vocabulary shared by installed
registry and native-dossier validators. Every platform explicitly declares each
capability. A caller supplies requirements, not support assertions; native support
requires a current exact-tuple dossier and directed routes remain separately qualified.
Portable catalogue/profile revision changes require reassessment and new plan identity.

Commands and import owners for qualification now reside in `provisioner.qualification`;
the former scripts are removed. Consumers must migrate rather than use an alias.
Other retained execution interfaces require the documented freeze/drain/reconcile
and historical-state conversion before their competing writers can be removed.

An agreement must also define failure/retry limits, credential renewal/revocation,
lease expiry, unknown outcomes and independent recovery. Include write cutover and
post-write recovery ownership explicitly: neither producer may assume the other has
excluded the old writer or admitted target writes.

### Versioned capability and discovery property interfaces

Profile `requires.constraints` entries have exactly `property`, `operator` and
`value`; the property owner must occur in required capabilities. The property
vocabulary/digest is closed and integers exclude booleans. Resolution format 3
and policy capsule/realization format 2 carry this digest. Old inputs require
new review, not a compatibility translation.
Discovery normalizer 2 requires source `requiredCapabilities`,
`capabilityRequirements`, `capabilityPropertySchemaDigest` and destination
`observedCapabilities`, `capabilityProperties`, `capabilityPropertySchemaDigest`.
These are observed/reviewed inputs, not client-issued authorization. Signed
control findings must retain raw and normalized snapshot digests and the current
normalizer. Missing, malformed and stale fields stay unknown; exact typed
mismatches remain blockers. Comparison never sets `executionAuthorized` true.

See [verified research decisions](../engineering/platform-migration-research.md) and
[existing wave-plan delta](../product/enterprise-workload-mobility-execution-plan.md#8-research-driven-acceptance-and-implementation-delta).

### Revised native collector contracts

AHV uses `nutanix-ahv-v4.0-hardware-2`; VMware VM-info uses
`vcenter-rest-vm-info-8.0.3.0-visible-only-2`. Old profile IDs are not compatibility
aliases. The site worker must verify campaign admission, current read credentials,
exact native endpoint/scope, API release, TLS origin and response/timeout budgets.
It signs the new raw observation with a matching independent credential witness;
collector output alone is never admitted inventory or mutation authority.

VMware now emits common `DiscoveryPage` records. Its cursors partition one captured
visible set; they do not assert a native pagination mechanism or complete privileges.
Empty visible results remain partial; a failed scan is unknown. Recheck the campaign
before and after every read and before publication. Folder-review and hardware facts
are part of the immutable snapshot, so changes require fresh signed reviews.
AHV keeps tagged disk backing and explicit boot/security/device observations rather
than applying SDK request defaults. Consumer normalization and compatibility remain
separate from native qualification and execution approval.


## Engineering and implementation handoff

Populate the controlled engineering schedule with exact native values and support evidence. Both owners review it. Link each field to the applicable assertion and actual procedure, and retain separately protected evidence. The repository’s examples do not supply those native values.

## Acceptance and open work

Unassigned endpoints, authority, recovery and version terms block the corresponding handoff. A local draft is not a signed agreement.

Adopting authority and approval evidence: **not recorded**. Link the actual design review and its conditions when they exist; a code merge does not authorize a site or service. Keep sensitive site parameters and private credentials in their approved systems.

[Maintained design register](README.md) · [Decision register](../adr/README.md)
