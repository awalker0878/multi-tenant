# Wave 2 read-only discovery and comparison

Status: B14–B22 are partially implemented. Authenticated publication and scoped
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
every claimed native page was actually read. Native collector transport,
constrained credential retrieval, installed API/field-profile binding and full
coverage reconciliation still need integration. The 1 MiB request limit must be
accounted for when designing campaigns and resumable publication.

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

1. Connect the existing bounded VMware, AHV and OpenStack GET adapters to
   independently admitted campaigns and site credential custody. Bind the actual
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
credential issuance and AHV/OpenStack HTTPS composition remain open.
