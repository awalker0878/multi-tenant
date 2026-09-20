# Collecting target-bound qualification evidence

`tools/qualify_target.py` runs the existing exact-ID native observers before and
after a bounded guest traffic campaign. It uses real HTTPS and certificate SSH.
It neither changes native configuration nor marks a platform/site qualified.
Use its evidence in the [native reference campaign](../native-reference/campaign.md)
and the independent acceptance process. It cannot replace HA, capacity,
delegated-administrator, same-subnet bypass, storage or whole-application recovery
tests that the campaign requires.

## Private inputs

Use owner-only files in an operator directory outside this checkout. The plan
format is `hosting-target-campaign/1`, with these exact fields:

| Field | Value |
| --- | --- |
| `scope` | `environment_key`, `site_key`, `platform`, `tenant_key`, `wsd_key` |
| `source_commit` | Full commit of the clean checkout that will run the campaign |
| `origin` | One canonical HTTPS origin for Neutron, NSX Local Manager or Prism |
| `assets` | The seven content-bound assets below |
| `cases` | 1–32 exact IPv4 HTTPS health/denial cases |

Each asset is an object with absolute `path` and SHA-256 of its exact file bytes
in `sha256`. Do not commit actual values, credentials or evidence.

| Asset | Content |
| --- | --- |
| `inventory` | Private inventory produced by [guest_inventory.py](native-guests.md); scope and native workload IDs are rebuilt and checked |
| `native_manifest` | Current exact resource IDs and expectations for the selected [native observer](../../NATIVE_READBACK.md) |
| `native_credentials` | Neutron: JSON `token`; NSX/Prism: JSON `username`, `password`; scoped read-only credentials |
| `native_ca` | PEM CA bundle for the native API |
| `ssh_key` | Unencrypted short-lived Ed25519 private operator key in protected custody |
| `ssh_certificate` | Matching user certificate accepted by the guest CA/principal policy |
| `probe_ca` | PEM CA bundle for the approved health endpoints |

For the OpenStack bootstrap/activation/recovery campaign use
`hosting-target-campaign/2`. It retains these fields and adds three bound assets:
`workload_manifest`, `workload_token` (plain token bytes), and `workload_ca`.
The [OpenStack workload manifest](openstack-readback.md) must cover every server,
boot volume and data volume in the bound guest outputs. Nova and Cinder attachment
expectations must agree with those outputs, and each boot volume's image ID must
be included in Glance observations. The manifest's project must match Neutron;
its site/tenant/WSD scope must match the campaign. Volumes created without an
image may omit `volume_image_metadata`; bootable volumes require image lineage.

Version 2 performs both network and workload readback before and after traffic.
Each collector has its own 120-second maximum and checks remaining authority.
Private `native-before-workloads.json` and `native-after-workloads.json` record
the workload results. The campaign's native hashes bind both collector results.
Version 1 remains available for the existing network-only campaigns; its scope
does not include Nova/Cinder/Glance placement or storage qualification.

For Nutanix use `hosting-target-campaign/3`. It adds only `workload_manifest` to
the seven base assets and reuses the exact Prism origin, credentials and CA.
The [AHV snapshot manifest](nutanix-vm-readback.md) must cover every VM ID in the
bound guest outputs. It must share the network manifest's operation, portable
tenant/WSD, engineering and target binding references, and actual native tenant
UUID. Every NIC must be connected to an enumerated native subnet; each guest's
accepted address must occur on its VM. Powered-off expectations are rejected for
this traffic campaign. Actual host, category, project, disk and ETag expectations
still require independent acceptance; Terraform outputs do not establish them.

Version 3 performs the network/task readback and AHV snapshot readback before and
after traffic, with a separate 120-second budget for each child and joint result
hashes. A network task result does not prove VM task completion. The AHV report
explicitly lacks that claim. Flow policy/precedence, same-host isolation, image
initialization, HA and retained-data recovery remain separate native obligations.

For the owned Nutanix service policy use `hosting-target-campaign/4`. It extends
version 3 with two more bound assets: `flow_manifest` for the
[Flow snapshot reader](nutanix-flow-readback.md), and `domain_outputs` from the
successful domains execution receipt. All three observers use the same Prism
origin, credentials, CA, operation and accepted scope. The Flow manifest must
enumerate every owned domain policy exactly once, with the output category and
VPC IDs. Each observed VM must belong to exactly one of those domain categories,
and all its NIC subnets must belong to that policy's observed VPC. These checks
prevent substituting a matching policy that does not cover the tested workload.

Version 4 collects network/task, AHV and Flow reports both before and after
traffic. The combined digest binds all three reports; each child keeps its own
120-second budget. It still does not establish precedence against policies
outside the owned set, effective enforcement, complete category membership across
the site, Flow task completion or HA/recovery. Preserve independent native policy
and counter evidence alongside the controlled guest probes. Do not downgrade to
an earlier campaign version to bypass a failed policy observation.

For VMware use `hosting-target-campaign/5`. Add `workload_manifest`,
`workload_session` (plain short-lived VI session bytes) and `workload_ca` to the
seven base assets. The plan's `origin` and base credentials/CA remain bound to
NSX. The [vSphere manifest](vsphere-readback.md) carries its separately accepted
vCenter origin; its bytes and CA/session asset bytes are bound by the campaign
authority. Credentials are injected only into their own collector process.

The vSphere manifest must cover exactly the BIOS UUIDs in the owned workload
outputs, share NSX's operation, portable tenant/WSD and engineering/target
references, and expect powered-on VMs with connected NICs. VM snapshot, exact-task
and bounded task-tree/history profiles, including the template-clone variant,
are supported; choosing a snapshot does
not claim task completion. The history profile additionally creates, reads and
destroys session-local filtered collectors through fixed POST methods. Accept
that capability and the observer's task visibility in the campaign authority.
The runner collects NSX and vSphere evidence before and after probes
and binds both report hashes. Task failure or VM drift holds the campaign.
Clone source identities/revisions and destination result mappings must be
accepted with the task trail; this does not infer state adoption or image provenance.

The scope reference must independently establish the managed-object/UUID and
NSX-segment/vCenter-network associations. This version observes each configured
NIC backing but does not discover or prove that cross-system association, effective
DFW group membership, guest address configuration or policy precedence. Keep the
accepted native network mapping and enforcement evidence with the campaign.

The runner reconstructs SSH settings from the bound guest records, uses pinned
host keys, and requires certificate authentication. It ignores inventory command
overrides and ambient SSH configuration, proxies, agents and user key discovery.
The approved private key is copied into the private run directory for the child
client, with its certificate at the adjacent `ssh_key-cert.pub` path for
[OpenSSH's identity pairing](https://man.openbsd.org/ssh_config#IdentityFile),
and removed on normal completion/failure. After a forced controller stop,
protect and reconcile that directory, including any remaining key copy.

Each case has exactly these fields (the digest is illustrative):

```json
{
  "id": "same-service-health",
  "guest": "guest-a",
  "destination": "192.0.2.130",
  "port": 443,
  "server_name": "service.example.test",
  "path": "/health",
  "body_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "expect": "allow",
  "healthy_control": null
}
```

An expected denial uses `expect: deny` and names an allow case in
`healthy_control`. That control must use a different guest but the same
destination, port, certificate name, path and body digest. The runner verifies
the control immediately before and after the denial. Failed controls or routing,
SSH, identity and TLS errors are inconclusive, not passing isolation evidence.
A successful TCP connection fails an expected denial, even if TLS later fails.
Refusal/timeout with both healthy controls is bounded path-denial evidence; it
does not identify the enforcing device. Correlate native counters/logs independently.

The fixed remote script checks `/etc/machine-id`, binds to the guest's accepted
SSH IPv4 address, and performs one connection. An allow must verify TLS identity,
HTTP 200 and the exact body digest (at most 1 MiB). No redirects, query parameters,
arbitrary remote commands, endpoint discovery or address ranges are supported.
The chosen health path must be a read-only operation owned by the service. Guests
need Python 3 and an accepted address usable for both SSH and the tested path;
multi-interface source selection needs a separately adopted profile.

## Authority and execution

Supply a `hosting-target-campaign-authority/1` object with `plan_sha256` (exact
plan bytes), `source_commit`, `ssh_sha256` (actual executable bytes),
`valid_from`, `valid_until`, `change_ref`, `target_binding_ref` and `isolation_ref`.
The window must be current and at most one hour. References identify separately
issued records; JSON is not authentication of the issuing authority. The target
binding must independently establish that native manifest resources and guest
IDs belong to the exact site/tenant/WSD. Do not infer ownership from a label.

```sh
python tools/qualify_target.py /private/operator/campaign.json
python tools/qualify_target.py /private/operator/campaign.json --execute \
  --authority /private/operator/campaign-authority.json \
  --ssh /usr/bin/ssh --output /private/operator/new-campaign
```

Without `--execute`, only the plan schema is checked and no target is contacted.
Execution validates source, assets and authority before contact. Native reads
are bounded to 120 seconds per collector; each SSH command to 20 seconds and its
remote probe to 10 seconds. The next phase is refused unless enough authority
remains for its entire timeout. Access expiry is checked before every guest call.

The private journal starts as `HOLD_INCOMPLETE`. Missing/failed native readback,
interruption or incomplete observations cannot produce acceptance. Failed traffic
stops the campaign and returns a hold. Complete matching observations return
`COLLECTED_REQUIRES_INDEPENDENT_ACCEPTANCE`, retaining the scope, source, exact
input digest, before/after readback hashes and per-probe timestamps. No accepted
qualification index is updated and no connectivity is opened by this tool.

Maintain the separate [edge lease/withdrawal](edge-activation.md) during the
campaign; on failed readiness, execute the already-authorized withdrawal.
This read-only collector cannot issue its own mutation authority or silently
renew an expiring policy. For recovery campaigns, pair these health checks with
the [restic file restore](restic-recovery.md) and application-owner acceptance.
Neither file hashes nor a health endpoint alone establish database consistency.
