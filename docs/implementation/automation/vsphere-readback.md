# vSphere VM snapshot readback

`tools/vsphere_observe.py` uses the Virtual Infrastructure JSON API with the
explicit `8.0.3.0` release schema. It reads only the `config`, `runtime` and
`resourcePool` properties of enumerated `VirtualMachine` managed object IDs.
It does not discover VMs, log in, mutate configuration or control power.

Use the common [native readback envelope](../../NATIVE_READBACK.md), platform
`vmware`, profile `vsphere-vi-json-8.0.3.0-vm-snapshot`, and no `task`. Each resource
contains `kind: vm`, `moid` and `expected`. The expected object contains the three
property responses, restricted to the fields enforced by `validate()`. Accept
the mapping from managed object ID to BIOS `uuid` (the Terraform VM ID) and
vCenter `instanceUuid` independently. A VM name or portable tenant label is
insufficient proof of ownership.

The snapshot includes the accepted config `changeVersion`, CPU/memory, full
hardware device inventory, host, resource pool, power and explicit stable runtime
flags. This profile supports vmxnet3 NICs on opaque NSX or distributed-port
backings and persistent flat-v2 disks with UUID, datastore and slot identities.
All native fields of every device are compared, including backing and connection
flags. Unsupported devices or disk chains require engineering review. Other
configuration fields, including guest initialization material, are outside this
profile and are not journaled. The complete controller/device list must come
from accepted native evidence, never synthesized to match a fixture.

Validate without network contact:

```sh
python3 tools/vsphere_observe.py /private/site/vsphere-manifest.json
```

For an authorized read, inject the site's short-lived read-only session through
`VCENTER_SESSION` and provide `--read-authorized-target`, `--expected-origin`,
`--ca-file`, and a new private `--output`. The session must be issued through the
VI `SessionManager` login mechanism; a vAPI session is not assumed interchangeable.
The GET transport verifies TLS, refuses redirects and bounds response/polling
work. A missing property, unsupported shape, changed identity/revision or drift
holds the observation. Missing Boolean fields are not defaulted to false.

Each sample reads all three properties twice and requires matching selected
snapshots; two stable rounds are required. This detects observed concurrent
changes but is not an atomic snapshot or a native writer fence. A configuration
match cannot determine task completion, resolve an uncertain Terraform apply,
authorize retry, prove NSX membership/enforcement, or establish HA/recovery.

Interfaces: Broadcom's [VM config](https://developer.broadcom.com/xapis/virtual-infrastructure-json-api/latest/sdk/vim25/release/VirtualMachine/moId/config/get/),
[runtime](https://developer.broadcom.com/xapis/virtual-infrastructure-json-api/latest/sdk/vim25/release/VirtualMachine/moId/runtime/get/)
and [session authentication](https://developer.broadcom.com/xapis/virtual-infrastructure-json-api/latest/api-security-schema/)
documentation, with field availability checked against the
[govmomi 0.49.0 types](https://github.com/vmware/govmomi/blob/v0.49.0/vim25/types/types.go)
pinned by vSphere provider 2.12.0. These references and repository HTTPS fixtures
do not qualify an installed vCenter/ESXi/NSX tuple.
