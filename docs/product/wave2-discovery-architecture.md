# Wave 2 read-only discovery and comparison

Status: B14–B22 are partially implemented. Durable unreviewed proposals and
independently signed assessment-only owner decisions are separate records. The
owner-review continuation below describes their current composition. The installed-collector checkpoint
below distinguishes working command/library composition from deployed custody gaps. Authenticated publication and scoped
comparison are available in the repository; native collector integration, full
fact coverage, scheduling and estate acceptance remain open. No native route is
qualified by this document or by fixture-backed tests.

## Authority and state boundaries

An `EnvironmentRegistration` is a human selector in `DECLARED_UNVERIFIED`
state. It is not an observed environment, endpoint enrollment, ownership claim
or permission to contact a platform. The B10 `DISCOVER_READ` grant serves a
job-bound, already owned native object. Brownfield enumeration has a separate
campaign authority; it must not create a dummy native owner, broaden a site SQL
login or reuse a mutation lease to obtain read access.

The separate [discovery ingest service](../discovery-ingest.md) verifies the
actual collector's mTLS connection against its pinned TLS context and CRL,
independently signed campaign authority, collector result signatures and fresh
native read-credential witness. Campaigns bind an exact organization, tenant,
WSD, site, endpoint, native scope and platform family, collector identity,
approval reference, allowed resource kinds, time window and page/object budgets.
Signed enrollment separately binds the credential reference. The witness has a
different pinned authority and binds an independently retained native IAM/RBAC
observation. Current signatures, enrollment, witness freshness and revocation are
rechecked with the database clock before publication.

The listener retains original signed request bytes and a fsynced verification
record before inserting campaign or result state. Dedicated ingest SQL roles,
forced tenant RLS and append-only records separate publication from human API
reads and site-worker access. A forwarded certificate, bearer token or environment
registration cannot supply result authority. Signed policy revision floors,
independent custody and actual native witness production remain deployment
obligations; a protected local file is not independent recovery evidence.

Campaigns, generations, observations and absence candidates are durable and
append-only. The page assembler checks sequence, cursor chain, identity and
collection budgets, preserving errors and missing privileges as partial/unknown
coverage. The HTTP publication is a bounded signed aggregate, not proof that
every claimed native page was actually read. The installed command now connects
bounded native transports, independently attested credential material and original
signed publication. Deployed credential issuance, complete installed field profiles
and independent coverage reconciliation remain open. The 1 MiB request limit must
be accounted for when designing campaigns and resumable publication.

Partial generations cannot establish absence or retire a native object. Even
complete same-scope inventory produces an absence candidate, not deletion or
ownership authority. Native IDs remain identity keys across renames. Only
currently authorized endpoint-scoped reads expose generation summaries and
object identities to an operator; raw collector credentials are never returned.
Brownfield adoption and application grouping currently provide review models,
not persisted owner acceptance or native mutation.

## Comparison semantics

[Signed assessment inputs](../operations/assessment-evidence-ingest.md) retain
independently reviewed installed tuples, directed route claims and control
findings in a separate append-only tenant store. Readback verifies both retained
signature provenance and live reviewer authority; revoked, expired, mismatched or
tampered evidence cannot fall back to an older accepted claim. A route binds exact
source and destination tuples, method, guest profile, data mode and network mode.
Source-exit and target-operation conclusions are independent. Family similarity
and the reverse direction do not imply support.

The assessment service reconstructs the selected immutable generations and binds
normalized facts to original result digests and a normalizer version. Conflicting
CPU, memory, NIC or capacity aliases remain unknown, including contradictions
between available capacity and fully observed quota arithmetic. Independent
policy, security and recovery reviews bind both original and normalized source
and destination snapshot digests. Missing facts and incomplete coverage remain
visible; normalization cannot create qualification.

The authenticated `POST /v1/assessments/compare` endpoint, portal and thin CLI
compare one observed native VM with 2–20 distinct authorized destinations. Each
request rechecks exact-scope access and installed authority. Results retain input
generations/digests and report `ELIGIBLE`, `CONDITIONAL`, `BLOCKED` or `UNKNOWN`,
with reasons, remediation and confidence. Copy-phase estimates are explicitly
uncertain. The [operator guide](wave2-operator-guide.md) describes selectors and
failure behavior. Comparisons never mint plan approval or start a native job.
Multiple registrations for one native scope cannot pad the comparison. A newer
generation supersedes an older pin for current eligibility even when the new
collection is partial or unknown; the historical digest stays unchanged and the
new observation metadata and hold reason remain visible.

## Remaining delivery and acceptance sequence

1. Deploy the installed VMware, AHV and OpenStack collector composition with
   independently admitted campaigns and actual site credential custody. Bind the
   installed profile, required field coverage and retained native page evidence.
   Complete VM/device/network/storage/capacity normalization one platform at a time.
2. Qualify pagination, stable IDs, project/tenant isolation, missing privileges,
   timeout behavior and installed API compatibility on selected native sites.
   Reconcile independently collected inventory, including VMware's visible-list
   limit and inherited privilege omissions.
3. Persist attributed enrichments, reviewed application membership, owner and
   dependency decisions, consistency groups and no-change adoption review state.
4. Add bounded scheduling, per-endpoint concurrency/rate budgets, resumable
   publication and operational freshness. Keep retry authority distinct from a
   still-current independent signed campaign.
5. Exercise reconciliation and reproducible synthetic scale measurements, then
   perform the agreed native estate benchmark. The plan's 50,000-workload/100-
   endpoint target and p95 under two seconds require measured operation-specific
   evidence; synthetic model timing cannot qualify native or PostgreSQL latency.

The repository exit is a deployable read-only path from authorized collection to
useful scoped comparisons. Real installed platform tuples, native inventory
reconciliation and reviewed destination claims remain separate qualification
requirements. Wave 2 stays partial until its remaining repository work is complete.


## Platform semantic comparison increment

Normalizer `hosting-assessment-normalizer/2` now binds typed source requirements
and target observed capability/property sets to the current property schema digest.
Old-normalizer signed reviews cannot authorize the new interpretation. Whole-VM
compatibility requires explicit source boot/architecture/security/device facts and
target driver/key/writer readiness, with unknowns preserved. Warm-transfer
comparison requires bounded dirty-rate and throughput samples; disk pre-copy never
claims preserved running memory. Cross-family native relocation is a per-target
blocker, not a reason to discard all destination rows.

OpenStack reads additionally retain bounded native port binding/security/group/
QoS/address and volume encryption/multiattach/type facts. These do not create
policy-equivalence findings or installed support. Missing extension/privilege data
stays unknown. Full VMware/AHV fact wiring and independent native qualification
remain open under the [existing wave plan](enterprise-workload-mobility-execution-plan.md#8-research-driven-acceptance-and-implementation-delta).


### Native hardware collection follow-up — 28 September 2026

B14/B15 now retain more native facts without manufacturing capability claims.
AHV's VMM v4.0 collector records the explicit boot union, returned Secure Boot and
vTPM booleans, native live-migration hint, disk bus/index and NIC model/MAC/link
state. A tagged volume-group attachment cannot masquerade as a VmDisk or supply
its disk-image capacity. Duplicate addresses, malformed types and oversized facts
remain unknown; missing SDK response fields never acquire request defaults.

The VMware REST collector now retains VM-info CPU, memory, firmware, disk layout,
NIC model/MAC/link and native network bindings, with instance UUID and reviewed
folder identity/digest. Summary/detail disagreements hold the scan. Its new
`collect_vmware_vms` path emits the common campaign pages and rechecks campaign
lifetime around each native GET. Those pages are always `PARTIAL` for visible-only
REST inventory, even when the result is empty. Native read failures emit `UNKNOWN`
without publishing a truncated scan as complete; expiry cannot produce late evidence.
The emitted cursors partition the captured observations, not a native paging API.

Collector identities are `nutanix-ahv-v4.0-hardware-2` and
`vcenter-rest-vm-info-8.0.3.0-visible-only-2`. Re-admit campaigns and reissue the
matching worker/credential witnesses; old collector identities are rejected rather
than aliased. Raw hardware and folder-evidence changes affect snapshot digests.
The normalizer remains version 2: its interpretation is unchanged, and the changed
raw snapshots require new signed review bindings. No existing approval is restamped.

This is bounded read-only mapping and campaign integration, not completion of
B14/B15 or Wave 2. Site transport/credential wiring and independent visibility
reconciliation remain open, as do full controller/boot-order/opaque-network,
ISA, encryption/key, shared-disk and passthrough mapping and attributed application
requirements. REST VM-info does not supply SOAP ConfigInfo security fields.
The native live-migration hint is not directed route or entitlement qualification.
No native system or guest was contacted; no execution or qualification gate changed.

### Native schema references for this follow-up

Read 28 September 2026. These document response shapes, not installed tuple support.

- [vCenter VM-info REST schema](https://developer.broadcom.com/xapis/vsphere-automation-api/latest/api/vcenter/vm/vm/get/)
  defines the CPU/memory/boot objects and disk/NIC maps. Do not import fields from
  a different API family; `efi_legacy_boot` is not Secure Boot enablement.
- [AHV v4.0 Disk](https://developers.nutanix.com/api/v1/sdk/namespaces/main/vmm/versions/v4.0/languages/python/ntnx_vmm_py_client.models.vmm.v4.ahv.config.Disk.html)
  distinguishes VmDisk and ADSFVolumeGroupReference backing members;
  [DiskBusType](https://developers.nutanix.com/api/v1/sdk/namespaces/main/vmm/versions/v4.0/languages/python/ntnx_vmm_py_client.models.vmm.v4.ahv.config.DiskBusType.html)
  documents the supported response enum, including SPAPR. A bus type does not prove ISA.
- [AHV v4.0 UefiBoot](https://developers.nutanix.com/api/v1/sdk/namespaces/main/vmm/versions/v4.0/languages/python/ntnx_vmm_py_client.models.vmm.v4.ahv.config.UefiBoot.html),
  [VtpmConfig](https://developers.nutanix.com/api/v1/sdk/namespaces/main/vmm/versions/v4.0/languages/python/ntnx_vmm_py_client.models.vmm.v4.ahv.config.VtpmConfig.html)
  and [EmulatedNic](https://developers.nutanix.com/api/v1/sdk/namespaces/main/vmm/versions/v4.0/languages/python/ntnx_vmm_py_client.models.vmm.v4.ahv.config.EmulatedNic.html)
  supply separate observations. API/SDK construction defaults are not returned facts.

Regression coverage lives in `tests/provisioning/controlplane/test_ahv_hardware.py`
and `tests/provisioning/discovery/test_vmware_hardware.py`, alongside existing
collector, normalization and ingestion tests. It covers missing versus false/empty,
union/type confusion, overflow, duplicate device identities/slots, fact-size bounds,
redaction, immutable digests, scope/role/version mismatches, native read failures,
clock expiry, campaign budgets and normalized output. Real native captures,
privilege-loss enumeration reconciliation and signed transport campaigns remain
required under B14/B15/B18/B47; these unit fixtures do not replace them.

## Signed native HTTPS transport follow-up

The [VMware native read transport](../engineering/vmware-discovery-https.md) connects
the existing collector to real bounded HTTPS using independently signed session
material and current campaign/enrollment/native-witness checks. It pins IP, TLS
hostname and CA, restricts paths to the selected folders and their observed VM IDs,
and rejects expired, revoked, rotated, ambiguous or oversized inputs. Loopback TLS
is a protocol test, not a vCenter qualification. The output remains visible-only
and partial; original collector signatures and mTLS ingestion are still required.
OpenStack now verifies campaign validity before each native GET as well as after
responses, so an expired campaign cannot perform even its first read. Actual site
credential issuance remains open; the OpenStack client continuation below supplies
the bounded HTTPS implementation, not deployed issuance or result publication.


## AHV signed native HTTPS continuation

[AHV HTTPS discovery](../engineering/ahv-discovery-https.md) now connects the existing
collector to actual GETs with a signed service-account API key, exact cluster/page
allowlist and independently witnessed read-only authority. It shares the real
provider-neutral HTTPS mechanism with VMware, not the VMware adapter. Scope,
authority, credential rotation, TLS identity, deadlines and response bounds are
rechecked; failed clients do not automatically retry. Successful/empty lists stay
visible-only and partial. API totals are not independent native coverage evidence.

New owners are `adapters/ahv_credentials.py`, `adapters/ahv_https.py` and the common
`native_https.py`. Existing collector IDs, normalizer and signed-result contracts
remain unchanged. Site composition, key issuance/revocation, durable revision
floors, original result signing/publication and owner/dependency review remain open.
The subsequent OpenStack client uses this shared mechanism with distinct project
and service-version contracts. Actual TLS fixtures test protocol enforcement, not native
Prism support or production authority.

## OpenStack signed native HTTPS continuation — 29 September 2026

The [OpenStack HTTPS client](../engineering/openstack-discovery-https.md) implements
actual project-scoped Nova/Cinder/Neutron collection and quota reads, not login or
mutation. `openstack-project-https-1` pins compute 2.79, volume 3.60 and network v2.0
contracts. Its independent signed binding selects project/user, catalog evidence,
region/interface, all three endpoint/IP/CA records, token digest/validity and revision.
The native read-only witness must cover each service; a GET-only client does not
prove native RBAC. New campaigns need matching enrollment and credential material.

The provider constructs only consecutive admitted routes/markers. Neutron ports
carry the exact project filter. The shared HTTPS mechanism checks protocol version
headers without permitting authentication/Host/framing overrides. Scope mismatch,
ambiguous URL, wrong versions, stale material, exhausted budgets, native errors,
revocation and late responses hold the collection. Successful and empty results
remain partial/visible-only, not complete point-in-time inventory.

All three native clients now have bounded HTTPS implementations. Deployed site
composition, credential issuance/renewal/revocation, persistent revision floors,
Glance and remaining native facts, independent visibility reconciliation and B17
persistence still require work. Signed publication is implemented in the following checkpoint.
Normalizer 2 and policy formats remain unchanged; no native qualification or
migration execution is implied by this continuation.

## Campaign-bound signed publication recovery — 29 September 2026

The [publication/recovery owner](../engineering/discovery-publication-recovery.md)
now connects admitted collection, original collector signatures, private retained
wire bytes and explicit mTLS delivery through the existing ingest routes. It does
not replace the listener, SQL writer, native read adapters or signature verifier.

`stage_submission` locates an already-retained submission by tenant/campaign identity
and verifies it again without recollecting or re-signing. Payload storage precedes
a create-only reference that binds environment, authorization and request digest.
Competing submissions, reused identities, corrupt references and missing originals
hold before any publisher POST. A valid local record is still not a server receipt.

After a lost campaign/result acknowledgement, delivery stays unknown until explicit
current-authority retry of original bytes or independent reconciliation. PostgreSQL
continues to enforce identical retry idempotency and reject independent-outbox
conflicts. Restart recovery cannot renew an expired campaign or change captured-at.
Missing references from older outboxes require reviewed original-digest reconciliation;
no automatic rescan/import is provided. Local files are not independent DR custody.

Actual signing/publication and the installed command below are implemented. Deployed
signer/native credential lifecycle, persistent authority
floors, independent retention, visibility reconciliation, full facts, B17 persistence
and B22 scheduling/freshness/estate measurements remain open. Collector/normalizer/
policy contracts and partial/unknown inventory semantics are unchanged.

## Installed collector command — 29 September 2026

[The protected-configuration runtime](../engineering/discovery-collector-runtime.md)
connects the three existing native adapters, original signer/outbox and mTLS publisher
through `hosting-discovery-collect`. Staging and publication are separate explicit
actions. Restarted staging reuses original bytes; publication without an original
holds and cannot start native collection. Fresh authority and exact profile/scope
checks remain in the active owners. Partial inventory is not promoted to complete.

The command reports bounded JSON and distinct success, held, delivery-unknown and
interrupted exits without credentials or raw observation dumps. It is package-owned,
not a forwarding shim or new SQL writer. Deployed site custody, persistent revision
floors, independent visibility, full facts, B17 persistence and B22 fleet scheduling
still require implementation/qualification. The existing one-MiB aggregate and
pre-reference recovery limitations remain explicit.

## Generation-bound application drafts — 29 September 2026

The [application-draft API and store](../engineering/application-drafts.md) persist
membership, proposed consistency and dependency assertions without modifying native
inventory. Drafts can select actually observed members from partial generations;
reviewed candidates retain their prior COMPLETE requirement and exact owner review.
Authenticated authors/database timestamps are separate from logical owner and source
claims. Both known and unresolved dependencies remain in the immutable proposal.

Each new revision pins the latest fresh source, uses expected-revision comparison,
and atomically appends its audit event. Source publication and saving share a scoped
advisory lock; current authorization is rechecked after waiting and before commit.
Exact retries retain the original record, while historical GETs identify superseded
source pins. No accepted ownership, review result or execution permission is created.
Migration 0021 and existing API role checks protect tenant/native scope and history.

The [operator CLI continuation](../engineering/application-draft-operator.md) adds
scoped listing and explicit draft save/load; the
[browser workspace](../engineering/application-draft-browser.md) edits existing
metadata/startup order. Signed exact-draft review persistence and GET-only candidate
evaluation are implemented in the continuation below. Independent enrichment,
owner-facing signing and application-wide comparison remain open. These checkpoints
supersede the earlier in-memory-only grouping scope without closing B17/B20 or
native migration acceptance.


## Signed application-owner review continuation — 30 September 2026

[Owner-review evidence](../engineering/application-owner-review.md) now persists
through the existing separate assessment-ingest role and immutable signed store.
Exact owner enrollment, signature, draft revision/content and source pins precede
acceptance. A read-only endpoint consumes the latest valid decision through the
existing grouping validator, without fallback after revocation or expiry. Old
draft/inventory references remain held and external dependency claims are not
promoted to independently verified evidence. This is a separately evaluated review;
the original draft remains UNREVIEWED and no native ownership or write grant exists.

The source-publication lock now also orders owner-review ingest and shared review
reads. Live trust is checked after lock waits and before evidence/audit commit.
Application-wide destination planning, reviewer onboarding/signing UX, trusted
third-party enrichment and full browser editing remain open. Existing collectors,
normalizer and per-VM comparison contracts are unchanged.


## Read-only operator review consumption — 30 September 2026

The [owner-review command](../engineering/application-owner-review.md#inspect-the-review-from-the-operator-cli)
now exposes exact-draft review status in the existing thin operator CLI. Its
standard-library-only helper validates response identity, source, evidence, UTC
validity and status consistency, without importing the review service or issuing
signatures. It performs one GET and can check a previously retained record digest.
Missing/mismatched replies never refresh an approval or change a draft. A retrieved
assessment-only candidate still denies native ownership/execution and third-party
dependency verification. Browser review presentation, owner signing/enrollment and
application-wide assessment/planning remain separate unfinished integrations.

## Reviewed application-wide comparison

The [application comparison endpoint](../engineering/application-comparison.md)
now evaluates all members of an exact independently reviewed draft against multiple
authorized destinations. It retains per-member route/profile issues and compares
combined instance/CPU/memory/logical-disk demand with one selected capacity identity.
Unreviewed/partial/superseded application input holds; missing or changed evidence
cannot become eligibility. It does not reserve resources or authorize provisioning.
The API is implemented; a guided application-wide browser/CLI comparison is not yet
provided. Wave 2 remains open for the documented visibility, fact, review and
scheduling work before the Wave 3 execution handoff can be considered complete.
