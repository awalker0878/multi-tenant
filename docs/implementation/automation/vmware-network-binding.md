# Observe VMware network associations

The [VMware build design](../../engineering/platform-build/5-vmware-nsx-bind-domain-workload-and-policy-lifecycles.md)
requires evidence connecting vSphere NIC backings to the intended NSX domain.
Names, independently matching VM/policy snapshots and an accepted mapping record
alone do not observe that association on the installed systems.

## Exact NSX-backed portgroups

`tools/vsphere_network_observe.py` uses profile
`vsphere-vi-json-8.0.3.0-nsx-portgroups` and the common
[readback envelope](../../NATIVE_READBACK.md), with platform `vmware` and no task.
Each resource has `kind: nsx-portgroup`, an exact `dvportgroup-*` MoID,
`segment_path` and `expected`. The segment path is an accepted cross-owner binding;
the portgroup reader alone does not prove it belongs to that NSX segment.

`expected.config` contains `_typeName: DVPortgroupConfigInfo`, `key`,
`configVersion`, `distributedVirtualSwitch`, `backingType: nsx`, `type: ephemeral`,
`uplink: false` and `logicalSwitchUuid`. The switch reference must identify an
accepted `VmwareDistributedVirtualSwitch`/`dvs-*`. `expected.switch` contains
`_typeName: DVSSummary` and its native `uuid`, preserving the native string format.
Obtain these expectations independently from accepted site evidence.

The reader GETs the exact portgroup `config` and switch `summary` properties twice
per sample and requires two stable rounds. Missing, changed or contradictory
identities/revisions hold. Shared switch identities must agree across portgroups;
duplicate backing keys are refused. Unrelated switch inventory and descriptions
are excluded from reports. Normal CLI session/TLS/contact/output controls apply:

```sh
python3 tools/vsphere_network_observe.py /private/operator/portgroups.json
```

This profile covers NSX-backed distributed portgroups only. Standard portgroups,
opaque networks, direct port attachment, DFW membership/exclusions, forwarding,
HA and writer fencing require their separate evidence. No network or VM is changed.

Interfaces: [portgroup config](https://developer.broadcom.com/xapis/virtual-infrastructure-json-api/latest/data-structures/DVPortgroupConfigInfo/),
[NSX backing type](https://developer.broadcom.com/xapis/virtual-infrastructure-json-api/latest/data-structures/DistributedVirtualPortgroupBackingType_enum/)
and [switch summary](https://developer.broadcom.com/xapis/virtual-infrastructure-json-api/latest/data-structures/DVSSummary/),
also checked against the provider-pinned
[govmomi 0.49.0 types](https://github.com/vmware/govmomi/blob/v0.49.0/vim25/types/types.go).
Published interfaces and local HTTPS fixtures do not qualify an installed tuple.

## NSX segment realization identity

`tools/nsx_segment_observe.py` uses profile
`nsx-local-policy-v1-segment-switches`. Keep the existing NSX envelope, full
selected policies and exact revision/intent-version/enforcement-point expectations.
Every segment additionally has `logical_switch`, an independently accepted
selected `GenericPolicyRealizedResource` with `entity_type: RealizedLogicalSwitch`,
`id`, `path`, `_revision`, `intent_reference: [<segment path>]`,
`enforcement_point_path`, `realization_specific_identifier` and `state: REALIZED`.
This profile supports one Local Manager enforcement point per segment. Its native
switch UUID must not be reused by a different accepted segment.

The reader calls the exact segment's `realized-entities?intent_path=...` endpoint
before and after the existing policy/config/intent-status reads. It requires one
stable logical-switch result matching the accepted identity, native revision and
segment reference, with an explicit empty alarms list. Other realized entity types
are outside this association check; their presence does not establish attachment
or enforcement. Fault/description text is not persisted.

Reports retain selected before/after logical-switch witnesses, including an
explicit `alarms_empty` verdict. Offline review recomputes identity, revision,
stability and outcomes; a changed summary and digest cannot conceal a
contradictory switch witness. Recollect older reports without these witnesses.

The result list must be complete: at most 100 entries, a matching integer
`result_count`, no duplicate paths and no continuation cursor. A paginated or
ambiguous response holds for native-owner investigation; the tool never broadens
the query or infers an association from a display name. Missing/changed identity,
failed realization and pending publication retain their corresponding holds.

```sh
python3 tools/nsx_segment_observe.py /private/operator/nsx-segments.json
```

Interfaces: [segment-scoped realized entities](https://developer.broadcom.com/xapis/nsx-t-data-center-rest-api/latest/method_ListRealizedEntities.html)
and [realized resource fields](https://developer.broadcom.com/xapis/nsx-t-data-center-rest-api/latest/types_GenericPolicyRealizedResource.html).
The installed API version, entity/path shape, omission behavior and RBAC visibility
must be qualified independently. This selected identity check does not replace
effective policy, per-port membership, packet-path or recovery qualification.

## Campaign v6: bind the member's assigned network

Use `hosting-target-campaign/6` with the existing
[campaign command and authority](target-qualification.md). It extends v5 with
three additional private, hash-bound assets:

| Asset | Content and binding |
| --- | --- |
| `portgroup_manifest` | The enabled vCenter profile above; same vCenter origin, operation, tenant/WSD and engineering/target references as the VM manifest |
| `domain_outputs` | Original VMware domain outputs for the exact campaign scope; every owned segment path must appear once in NSX observation |
| `workload_inputs` | Original workload inputs with exact member names, `domain_key`, `quarantine_network_id`, scope and vCenter endpoint |

Use `nsx-local-policy-v1-segment-switches` for `native_manifest`; retain the accepted
full policy expectations as well as segment resources. Keep a supported vSphere
VM snapshot/task profile for `workload_manifest`. The VM UUIDs must cover the owned
workload outputs exactly. Every NIC must use a distributed-port backing whose
switch UUID and portgroup key match the member's assigned portgroup MoID. That
portgroup's `logicalSwitchUuid` must match the NSX realized switch for the member's
specific domain. An attachment to a different owned domain still fails. Extra
unused portgroups, omitted segments, ambiguous native IDs and unsupported opaque
or standard backings are refused before contact.

The campaign authority binds all supplied asset bytes. Obtain inputs/outputs from
their private execution records and independently accept their provenance; this
campaign does not authenticate receipts or infer ownership from names.

Before and after traffic, v6 collects NSX policy/segment evidence, portgroup
evidence, VM/task evidence, portgroup evidence again, then NSX evidence again.
Every reader must match its independently accepted expectations. The phase digest
binds all five reports; failures stop collection and keep exposure held. vCenter
uses only its VI session/CA, and NSX uses only its own credentials/CA. Each child
retains its bounded transport and expiring campaign authority checks.

These reads are not an atomic cross-system snapshot. They check selected configured
associations, not actual per-port attachment, effective DFW membership/exclusions,
hidden policy, guest IP identity, forwarding or writer exclusion. Preserve those
independent tests and evidence. Task-aware VM profiles retain their separate
coverage limits; snapshots do not imply task completion. Neither v6 nor the new
standalone profiles release a held Terraform attempt or authorize a power action.
Do not downgrade to v5 to bypass an association failure.

## Exact native port attachments

`tools/vsphere_port_observe.py` uses profile
`vsphere-vi-json-8.0.3.0-nsx-port-attachments`. Keep the portgroup envelope and
expectations above and add `ports` to each resource: 1–64 independently accepted
selected `DistributedVirtualPort` objects, at most 100 across the manifest.
Each port has exactly these selected fields:

| Field | Required expectation |
| --- | --- |
| `_typeName`, `key`, `dvsUuid`, `portgroupKey` | `DistributedVirtualPort`, exact port key and the enclosing group's accepted switch UUID/portgroup key |
| `config` | `_typeName: DVPortConfigInfo`, native `configVersion` |
| `proxyHost` | Exact `HostSystem` managed reference |
| `connectee` | `_typeName: DistributedVirtualSwitchPortConnectee`, exact `VirtualMachine` reference in `connectedEntity`, string `nicKey`, `type: vmVnic` |
| `connectionCookie`, `lastStatusChange` | Native signed int32 connection cookie and accepted timestamp; never substitute a default for missing data |
| `conflict` | `false` |
| `state` | `_typeName: DVPortState`, with `runtimeInfo` containing `_typeName: DVPortStatus`, `linkUp: true`, `blocked: false` and native lowercase `macAddress` |

Managed references use `type` and `value`, optionally `_typeName:
ManagedObjectReference`. Duplicate switch/port identities or VM/NIC occupants are
refused. These are selected attachment fields, not complete effective port policy.
Descriptions, traffic statistics, address hints and vendor extensions are excluded
from evidence. Configuration revisions and runtime status changes remain bound.

The client calls the exact accepted switch's VI JSON `FetchDVPorts` method using
POST with `{"criteria":{"portKey":["<exact accepted keys>"]}}`. This is a
read-only `System.Read` method; the implementation has no port mutation method.
It never omits criteria, requests all inventory, or filters out inactive ports.
Each response must be an array covering the exact requested keys once. Missing,
duplicate, extra, unreadable or malformed results hold. Missing connectee fields
because of restricted visibility also hold.

Port reads bracket the existing portgroup/switch reads, with two stable rounds
required. Changed occupant, host, cookie, revision, link state or selected runtime
data cannot pass. Normal explicit contact, session, CA, origin and private-output
controls apply. Without the contact flag this command validates inputs only;
the preview's `planned_get_targets` counts property GETs, excluding method POSTs:

```sh
python3 tools/vsphere_port_observe.py /private/operator/port-attachments.json
```

Interfaces: [FetchDVPorts](https://developer.broadcom.com/xapis/virtual-infrastructure-json-api/latest/sdk/vim25/release/VmwareDistributedVirtualSwitch/moId/FetchDVPorts/post/),
[port fields and connection cookie](https://developer.broadcom.com/xapis/virtual-infrastructure-json-api/latest/data-structures/DistributedVirtualPort/),
[connectee visibility](https://developer.broadcom.com/xapis/virtual-infrastructure-json-api/latest/data-structures/DistributedVirtualSwitchPortConnectee/)
and [runtime status](https://developer.broadcom.com/xapis/virtual-infrastructure-json-api/latest/data-structures/DVPortStatus/).
The pinned [govmomi method](https://github.com/vmware/govmomi/blob/v0.49.0/object/distributed_virtual_switch.go)
and [connectee enum](https://github.com/vmware/govmomi/blob/v0.49.0/vim25/types/enum.go)
also define the selected call/type. Published documentation and synthetic TLS
fixtures do not establish installed 8.0.3.0 compatibility; qualify actual response
types, optional-field visibility, revision/cookie semantics and privilege scope.

## Campaign v7: bind the observed port occupant

Use `hosting-target-campaign/7` with the v6 assets and the attachment profile for
`portgroup_manifest`. Every VM NIC's full native backing must include its accepted
`connectionCookie`. The campaign retains v6's owned domain/segment binding and
additionally requires one unique observed port per NIC. Port key, switch UUID,
portgroup key and cookie must match the VM backing; connected VM MoID and NIC key
must match the owned VM; proxy host and runtime MAC must match VM runtime/config.
Extra port evidence is refused. All these bindings are checked before contact.

The same five-report sequence now uses the attachment reader for both portgroup
reports before and after traffic. Native attachment changes after the VM read
stop collection; every phase digest binds its five reports. Retain explicit
authority for the read-only POSTs and the current independently accepted private
expectations. A hold requires native-owner investigation and recollection under
current authority, not editing expectations to fit an unexplained result.

These bounded observations still are not atomic or continuous. A later port
reuse, mobility event or writer can invalidate them. They do not prove effective
DFW membership/exclusions, guest IP identity, native isolation, HA, recovery or
writer fencing. The profile does not release a held attempt or authorize power
control. Do not downgrade to v6/v5 after an attachment hold. Use the
[commissioning cases](site-commissioning.md) to qualify the installed behavior.

## Campaign v8: include complete owned-domain intent

[Campaign v8](target-qualification.md#campaign-v8-bind-full-domain-intent) retains
v7's port bindings and combines them with strict observations of all four owned
NSX domain objects. Original domain inputs additionally bind allocation, gateway,
transport zone, lifecycle stage, policy scope/order and requested service intent.
Its five reports per phase are replayed before guest evidence can be accepted.
Both domain-shape and logical-switch witnesses remain required; it does not
replace independent effective-policy, task coverage or fencing evidence.

## Held Terraform attempt review

Portgroup reports retain selected before/after `group_witness` values. Attachment
reports retain `attachment_witness` with both port reads and the bracketed
portgroup/switch reads. Offline review recomputes identities, differences,
stability and selected hashes; changing a summary and its outer digest cannot
hide a contradictory witness. Native descriptions, counters and diagnostic text
remain excluded. Recollect older reports that omit these witnesses.

The [held-attempt reviewer](terraform-recovery.md) now requires the attachment
profile alongside existing-VM activity evidence. It binds the planned NIC key,
MAC and sealed network MoID through the observed switch/portgroup to the exact
VM/NIC occupant, cookie, host and runtime MAC. Both observations must be fresh and
collected under verified fencing/quarantine. Uncertain/missing attachment evidence
holds; there is no fallback to a matching portgroup alone. The review supports
the current module's powered-on, connected single-vmxnet3 layout only and leaves
all ledger bytes held. Native NSX ownership/enforcement and complete operation
reconciliation remain independent requirements.
