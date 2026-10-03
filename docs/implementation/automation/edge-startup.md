# Edge denial at startup

`provisioner/execution/edge_boot.py` establishes the complete accepted set of owned edge deny
tables before the selected network manager starts. It restores no allows or
activation leases. All selected tables are checked and replaced in one nftables
transaction, then inspected for permanent interface drops. Native owner journals
and unresolved attempts remain unchanged.

This boot configuration owner has standing authority only to close its accepted
boundaries. Live bootstrap/activation still requires the ordinary writer,
current authority and a higher accepted generation. The startup tool does not
configure interfaces, routes, forwarding sysctls, host-input policy or another
owner's firewall table. It does not qualify a reboot or failover.

## Accepted configuration

The private `hosting-edge-boot/1` record contains:

| Field | Binding |
| --- | --- |
| `source_commit` | Exact installed clean source commit |
| `machine_id`, `network_namespace_inode` | Accepted native host and namespace |
| `nft`, `nft_sha256` | Absolute approved executable and its byte digest |
| `ledger` | Same private native edge ledger used by live policy and incident operations |
| `specs` | Complete list of `{path, sha256}` bindings to private `hosting-nft-edge/1` boundary specifications |
| `boundary_acceptance_ref` | Accepted complete boundary ownership |
| `boot_ordering_ref` | Accepted startup/attachment and independent recovery design |

Every boundary must have an empty `flows` array and the same machine, namespace
and binary. Duplicate scopes and overlapping owned domain interfaces are refused;
shared service-side interfaces are allowed. The command takes every native scope
lock before changing any table. Busy writers, foreign tables, changed policy,
source drift and failed native checks prevent success.

```sh
python -m provisioner.execution.edge_boot apply --source-root /opt/hosting-source --config /etc/hosting-edge/boot.json \
  --output-root /var/lib/hosting-edge/boot --execute
```

The private output parent and native ledger must already exist. Each invocation
retains a private candidate, immutable attempt and native logs, plus a receipt
when denial is observed. It never clears an old native hold. A changed namespace
requires owner reconciliation and configuration review; IDs are not rebound.

## Startup dependency rendering

Render the unit and manager drop-in using actual installed paths:

```sh
python -m provisioner.execution.edge_boot render-service \
  --python /opt/hosting-python/bin/python --source /opt/hosting-source \
  --config /etc/hosting-edge/boot.json --output-root /var/lib/hosting-edge/boot \
  --ledger /var/lib/hosting-owner/ledger/owners/edge_policy \
  --manager systemd-networkd.service --output /private/edge-boot-unit
```

`NetworkManager.service` is the other supported manager. Install the generated
`hosting-edge-boot.service` under `/etc/systemd/system/`. Install
`network-manager.conf` as
`/etc/systemd/system/<selected-manager>.d/hosting-edge-boot.conf`. The drop-in
uses both `Requires` and `After`; a failed guard must prevent the manager from
starting. Ordering alone does not establish that failure dependency. Validate
the complete installed unit set with `systemd-analyze verify`, run
`systemctl daemon-reload` and enable `hosting-edge-boot.service` during the
accepted installation/maintenance procedure. Do not casually restart live
network management to install a boot policy.

Use a root-controlled standalone checkout and an interpreter with the matching
application wheel installed outside home directories. The generated service uses
`-I -B -m provisioner.execution.edge_boot` and selects that checkout explicitly. The service makes the filesystem read-only except its output
parent and explicit native ledger. Those paths must match its configuration and
remain independently recoverable. Source, configuration, binary and ledger
must be locally available before attachment; network mounts cannot supply them.
Stopping the service does not remove deny tables.

The accepted startup design must exclude workload forwarding in the initramfs,
another network manager or any unmanaged attachment before this guard runs.
Retain independent console/OOB recovery: guard failure can block in-band
management with the network manager. Confirm kernel defaults and every writer
of forwarding settings. The tool avoids toggling `ip_forward` because
[the kernel documents that changing it resets other IPv4 parameters](https://docs.kernel.org/networking/ip-sysctl.html).
The [systemd network ordering guidance](https://systemd.io/NETWORK_ONLINE/)
defines the pre-network synchronization target used by the service.

## Verification boundary

Tests cover atomic multi-scope denial, no ready receipt after native failure,
preserved unknown history, refused allow intent and the hard manager dependency.
The packet laboratory removes only its disposable owned table, runs the actual
startup writer, verifies both denied paths with a healthy endpoint control and
checks that native journal bytes did not change. This simulates volatile policy
loss. It does not reboot a host or prove initramfs ordering, OOB recovery, HA,
same-subnet isolation or the installed manager's complete behavior. Those remain
actual commissioning and acceptance exercises.

## Resumable installer

`provisioner/execution/edge_install.py` installs this profile on an accepted Ubuntu 24.04
systemd host during console/OOB maintenance. The selected network manager must
already be inactive and dead. The installer never starts, stops or restarts that
manager. It checks the actual host/system namespace, exact clean root-controlled
source, binaries, native manager unit and every preexisting manager drop-in.

The private `hosting-edge-install/1` configuration has these exact fields:

| Fields | Binding |
| --- | --- |
| `format` | `hosting-edge-install/1` |
| `source` | Absolute accepted installed checkout |
| `python`, `systemctl`, `systemd_analyze` | Absolute accepted host executables |
| Each executable's `_sha256` field | Exact executable bytes |
| `manager` | `systemd-networkd.service` or `NetworkManager.service` |
| `manager_unit` | Exact native unit `{path, sha256}` |
| `manager_dropins` | Sorted explicit existing `{path, sha256}` bindings, at most 32 |
| `boot` | Complete accepted `hosting-edge-boot/1` configuration above |
| `custody_ref` | Accepted local startup files and independent recovery custody |

Machine, namespace, source commit, nft executable and ledger bindings come from
`boot`. The native ledger must already exist and remains separately owned.
Source, interpreter, nft and ledger cannot depend on home, temporary or runtime
paths. The accepted installation design must also exclude network-mounted boot
dependencies; path spelling alone cannot prove storage availability.

The private `hosting-edge-install-authority/1` record contains `format`,
`config_sha256`, `valid_from`, `valid_until`, `change_ref`,
`maintenance_ref` and `recovery_access_ref`. Its exact configuration digest
and current window, at most one hour, bind the offline installation procedure.

```sh
python -m provisioner.execution.edge_install --source-root /opt/hosting-source --config /private/edge-install.json
python -m provisioner.execution.edge_install --source-root /opt/hosting-source --config /private/edge-install.json \
  --authority /private/edge-install-authority.json --execute
```

The immutable intent lives in `/var/lib/hosting-edge-boot-install`. The
installer copies accepted deny boundaries and its rewritten private boot
configuration into `/etc/hosting-edge-boot`; only file locations change.
The unit writes boot observations to `/var/lib/hosting-edge-boot`. Source
boundary files remain necessary for exact interrupted-install recovery; the
installed startup service uses the durable copies.

The installer publishes the guard unit and exact manager dependency, runs native
`systemd-analyze verify`, reloads unit metadata and checks the actual loaded
fragment, overrides and hard dependency. It enables and starts only the guard,
then independently observes permanent native denial under the shared edge
locks. An active oneshot service alone cannot satisfy installation. A successful
receipt still requires actual startup/attachment qualification.

Repeated installation verifies existing bytes and custody. Changed files,
unknown units/overrides, a running manager, missing native ledger or unconfirmed
denial hold the operation. Resume does not remove files, clear native holds,
restore allows or restart an active guard to hide later policy changes.
Installation file locks do not fence other root/network operators; the accepted
maintenance procedure must exclude those writers and preserve console access.
Starting networking afterward remains the separately accepted commissioning step.

Installer regressions cover stopped-manager enforcement, unknown native units,
changed files, concurrent installers, interrupted reload/start and actual systemd
unit parsing. They do not operate a live manager or establish host reboot/HA
qualification.
