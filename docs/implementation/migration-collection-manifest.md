# Migration VM collection manifest — VMware, AHV, OpenStack

**Data:** [`contracts/capabilities/migration-collection-manifest-v1.json`](../../contracts/capabilities/migration-collection-manifest-v1.json)  
**Schema:** [`contracts/schemas/capabilities/migration-collection-manifest-v1.json`](../../contracts/schemas/capabilities/migration-collection-manifest-v1.json)  
**Registry:** [`contracts/capabilities/definitions-v1.json`](../../contracts/capabilities/definitions-v1.json)

This is an **immutable version-controlled requirements catalogue**, not a native
observation, API success, migration approval, supported-API declaration or
completed E3/E4 qualification. No collection result can be silently inferred
from the presence of a field definition. The actual supported vendor/API
release and entitlements must be discovered in each installation, and its
operation qualified independently.

## Coverage

| Platform | Source VM facts | Destination facts | Owner / independent facts | Total |
| --- | ---: | ---: | ---: | ---: |
| VMware vSphere / VI JSON | 44 | 15 | 27 | **86** |
| Nutanix AHV / Prism v4 | 41 | 21 | 27 | **89** |
| OpenStack (Nova, Cinder, Neutron, Glance, Placement, Keystone) | 48 | 28 | 27 | **103** |
| **Total** | **133** | **64** | **81** | **278** |

Each collection row owns a stable `id`, `scope`, `api_family`,
`api_field`, `owner_evidence_field`, `collection_method`,
`max_age_seconds`, `severity`, `condition`, `collector_source`
and `collection_status`.

- **Critical:** absence, stale evidence, incomplete discovery or a failed
  required probe **blocks** the chosen migration method until resolved by
  independently reviewed evidence or a qualified equivalent. Examples:
  source disk inventory and backing identity, boot configuration, firmware,
  required network flow and isolation, host version, encryption/key custody,
  source fencing, guest drivers, physical capacity/reservations and recovery.
- **Optional:** a candidate nonessential feature may be omitted **only** after
  its effect and security/dependency impact are reviewed and an independently
  accepted E4 omission/suppression receipt is recorded. Examples:
  description/tags, replaceable SSH key metadata, a truly nonessential
  disconnected CD-ROM, or an explicitly proven redundant firewall rule.
  **Firewall rules affecting required traffic, isolation or a compliance
  boundary are critical**, irrespective of how the native API labels them.
- **Conditional:** `when:volume_backed`, `when:encrypted`,
  `when:vtpm_present`, `when:guest_dependent_method`, etc. mean
  **mandatory when the condition applies**; uncertainty about applicability
  itself is an unknown/hold, not permission to ignore the attribute.
  `cutover` requires a current observation at its write boundary.

## Collection and freshness

| Method | Source of truth and required handling |
| --- | --- |
| `native_get` | A scoped, credentialed GET from an enrolled vendor API; save timestamp, raw-response checksum, installation and exact API version |
| `native_list` | Bounded complete pagination, stable object identities, and an explicit continuation/no-incomplete check |
| `derive` | Deterministic transform from native responses; retain the original evidence digest and extraction version |
| `operator` | Named accountable owner inputs for matters not accessible from a vendor API; attribution and approval required |
| `probe` | Authorized isolated create/read/cleanup plus task and lost-response reconciliation; independent native reviewer must qualify results |
| `independent` | Separate measured or witnessed fact, such as actual allowed/denied paths or a representative restore; not the adapter's self-assertion |

A null `api_field` means **no single vendor API can provide that fact**.
The non-null `owner_evidence_field` names the independent or operator-owned
input. These critical items are still blocking obligations. Every vendor
field is labelled `native_field_candidate`; that means the collection
requirement is defined, **not** that the source collector currently returns
it successfully. `external_evidence_required` means an external authority
or active probe must be commissioned. Both statuses are intentionally
non-affirmative; neither is `supported`.

The maximum age is **seconds**. The stated initial budgets depend on how
rapidly a fact can change and how soon native effect admission will use it:

| Evidence category | Initial maximum age | Examples |
| --- | ---: | --- |
| Current VM power state | 10 s | Before snapshot/export/fence |
| Native remaining/reserved capacity | 15 s | Exclusive physical allocation |
| NIC connection, cluster availability | 30 s | Live attachment/host readiness |
| Disk identity, backing, network routing/policy | 60 s | Full disk/NIC list, security-group rules |
| Guest configuration and CPU/RAM | 120–300 s | Firmware, boot mode, capacity, quota |
| Installed API release, guest-driver profile, objectives | 3,600 s | Review binding before the next stage |
| Only proven noncritical owner metadata | Up to 86,400 s | Descriptive tags |

At planning, approval, reservation and every native effect boundary, calculate
`age = evaluated_at - observed_at`. Reject future observations, expired
signed receipts, missing timestamps, stale records, or a changed installation,
API/namespace version, entitlement, identity, topology, policy or generation
**even if the nominal age budget has not elapsed**. For a conditional row,
evaluate the condition from independently bound source facts; an unknown
condition is a hold for a critical feature. Retain an **append-only** history
of observations and their source/expiry; never rewrite prior negatives.

For example, `storage.disk_backing_chain` on VMware identifies a
`VirtualDisk.backing.parent` chain. OpenStack additionally requires each
Cinder volume to be inventoried separately from the Nova local root;
`os-volume_attachments` only lists the attachment identities, not the
volume's contents. Nutanix AHV's `backingInfo` similarly needs exact
disk object and storage-backend validation. None of these observations
can independently establish application consistency or qualified export.

## Implementation and acceptance boundary

The manifest maps to the repository's current
`workers/inventory/.../{vmware_workload,ahv_workload,openstack_workload}.py`
source collectors and destination profiles. The version-controlled tests in
`scripts/assurance/test_migration_collection_manifest.py` check IDs,
field custody, native field names, canonical required source disk/target
resource areas, severity limits and freshness bounds. The
`capability-assurance.yml` workflow contains an explicit check.

**Follow-on implementation required:** bind every manifest row and evaluated
conditional to the actual versioned Inventory observation stream; validate
authoritative source and API-family discovery rather than blindly reading
field candidates; store append-only evidence/expiry; reconcile missing
vendor fields; surface per-VM missing/optional attributes in Console; wire
critical values into Planning and native Lifecycle effect admission; make
E3 probe/cleanup and E4 omission evidence available from Assurance. The
manifest and E2 validation do not prove these workflows are already connected.

The authoritative work queue is [`next_work.md`](../../next_work.md),
and the [API compatibility design](migration-api-capability-compatibility.md)
describes the separately qualified version-selection/omission gate.

## Source references

The public API fields were cross-checked against the actual implementation
and the vendor references: [VMware VI/JSON
VirtualMachineConfigInfo](https://developer.broadcom.com/xapis/virtual-infrastructure-json-api/latest/data-structures/VirtualMachineConfigInfo/),
[Nutanix v4 API references](https://developers.nutanix.com/),
and [OpenStack Nova](https://docs.openstack.org/api-ref/compute/),
[Cinder](https://docs.openstack.org/api-ref/block-storage/v3/),
[Neutron](https://docs.openstack.org/api-ref/network/v2/), and
[Glance](https://docs.openstack.org/api-ref/image/v2/).
Versions, endpoints and optional response properties are verified against
each installed instance before forming native support evidence.
