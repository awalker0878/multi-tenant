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
