# ICD-M01 — Infrastructure interface ownership and service agreements

**Version:** 0.9 · **Status:** Proposed · **Accountable role:** Producing and consuming infrastructure owners.

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


### Signed native discovery transport

The VMware collector now has a package-owned HTTPS transport with signed native
session custody, pinned IP/hostname/CA, exact folder/list-derived detail paths,
finite I/O and total deadlines, strict response parsing and per-use live authority.
The native attestor is independent of campaign/collector signing identities. Its
credential reference must match the signed campaign enrollment and current native
read-only witness. Token bytes never enter observations or logs. This is an actual
GET implementation, not a claim of deployed Vault/session issuance or completeness.

OpenStack checks campaign validity before every page/quota GET and after native
responses, including errors. A late response or regressing clock cannot publish
fresh evidence. See [native read custody and tests](../engineering/vmware-discovery-https.md)
for exact fields, deployment obligations and rejection cases. Independent visibility
reconciliation, remaining site integration and native qualification remain open.

### OpenStack native discovery integration

`adapters/openstack_https.py` now connects the project collector to the actual
shared HTTPS mechanism. Its independently signed token binding names the exact
project/user, region/interface, all three service endpoints, API versions and
native token validity. Only consecutive project collection and quota GETs are
admitted. Compute/volume version response headers must match; service failures,
revocation, expiry and mid-read rotation discard the scan. Valid and empty scans
remain partial/visible-only. URL normalization cannot change signed endpoint
meaning. The [OpenStack read contract](../engineering/openstack-discovery-https.md)
documents fields, tests and unresolved issuance, publication and native evidence.

The native client requires `openstack-project-https-1` campaign enrollment and
matching independent read-only witnesses. No old collector identity is aliased.
This adds no mutation path or native qualification. Normalizer and policy formats
are unchanged; fresh observations require fresh signed review. Glance/image reads,
remaining hardware/key facts and deployed custody remain unfinished B10/B16
integration. The publication owner described below now supplies signed delivery.

### Signed discovery publication and campaign restart recovery

`discovery/publication.py` now composes collection with the original issuer and
collector signatures, immutable request bytes and a private tenant outbox.
`stage_submission` resumes an existing campaign reference without recollecting,
re-signing or changing capture time; all resumed evidence still needs current
verification. Payload durability precedes the create-only campaign reference.
Changed results, environment or authorization under one campaign ID conflict;
corruption and missing referenced bytes hold rather than trigger a replacement.

`discovery/publication_https.py` sends those retained bytes through the existing
mTLS ingest routes. The server remains the sole inventory writer. Exact TLS identity,
CA/CRL/certificate hashes, live authority, bounded acknowledgement fields and
request deadlines are checked. An attempted request with a lost or invalid reply
is explicitly unknown. Retry is deliberate, uses original bytes and still depends
on server-side campaign/result idempotency; it never grants native execution.

See [the publication and recovery contract](../engineering/discovery-publication-recovery.md).
Library signing, custody, authenticated delivery and the installed command below
are implemented. Fleet scheduling, deployed custody, independent retention and
persistent restart/DR authority floors remain open. Pre-reference outboxes require reviewed
original-digest reconciliation, not automatic rescanning. Local atomic references
do not prove global uniqueness, complete inventory or native qualification.

### Installed one-shot collector composition

`discovery/collector_runtime.py` now owns `hosting-discovery-collect`. A protected
versioned configuration selects the existing signed campaign, trust/witness stores,
private outbox and exact native/publisher settings. `adapters/collector_config.py`
constructs only the three registered native owners; no dynamic import or shim exists.

`stage` collects/signs/retains only when no original campaign reference exists;
resumed staging verifies original bytes without native credentials or signing keys.
`publish` requires an existing original and never falls back to collection. Distinct
held, unknown-delivery and interrupted exits avoid claiming that an uncertain POST
never committed. All outcomes retain `executionAuthorized: false`.

See [the installed collector contract](../engineering/discovery-collector-runtime.md).
The shared native GET mechanism also stops inherited TLS session-key logging while
retaining pinned certificate/hostname verification and bounded requests. Command and
real-TLS tests exercise fresh-process recovery; database and installed-wheel checks
cover publication identity and package ownership. Deployed credential/signer custody,
independent retention, durable revision floors, visibility, B17 and B22 remain open.
The command is not a scheduler, credential issuer, migration workflow or native qualification.

## Engineering and implementation handoff

Populate the controlled engineering schedule with exact native values and support evidence. Both owners review it. Link each field to the applicable assertion and actual procedure, and retain separately protected evidence. The repository’s examples do not supply those native values.

## Acceptance and open work

Unassigned endpoints, authority, recovery and version terms block the corresponding handoff. A local draft is not a signed agreement.

Adopting authority and approval evidence: **not recorded**. Link the actual design review and its conditions when they exist; a code merge does not authorize a site or service. Keep sensitive site parameters and private credentials in their approved systems.

[Maintained design register](README.md) · [Decision register](../adr/README.md)


### AHV native read interface

The AHV adapter accepts only an already-admitted VM campaign and independently
signed `hosting-ahv-read-credential/1` material. It binds the service-account UUID,
credential reference, API profile, exact endpoint trust and campaign digest; the
current native read-only witness and campaign enrollment remain independent checks.
Only the bounded VMM cluster VM-list GET is exposed. Failed/rotated/revoked reads
cannot publish current observations. Successful lists stay partial/visible-only.
The [AHV HTTPS contract](../engineering/ahv-discovery-https.md) specifies fields,
consumer obligations, request/response limits, key custody and remaining deployed
integration. This is not a source-signing interface, write grant or migration route.
