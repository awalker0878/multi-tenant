# Install the dedicated owner endpoint

`tools/owner_install.py` installs the [remote worker](remote-owner-worker.md) as a
separate systemd-managed SSH endpoint on an accepted Ubuntu 24.04 host. It writes
only its dedicated configuration/unit, a standard OpenSSH runtime-directory
declaration and selected private worker directories. It never edits management
SSH configuration, runs a staged native job or resets a native owner ledger.

This is an initial-installation and exact-resume procedure. The separate
[subject revocation owner](owner-revocations.md) performs monotonic deny-only
maintenance and its journal is preserved by repeat installation. Source upgrades,
account changes, listener moves, CA/host-key rotation and endpoint removal use a
separately accepted maintenance operation; modifying an installation input does
not cause this tool to overwrite or restart a running worker.

## Host and custody prerequisites

Use the independent accepted management/console path. Preinstall the supported
OpenSSH server, systemd, Git, [Python execution runtime](runtime-bootstrap.md) and required owner executables from
the approved artifact source. The source checkout must be at the exact accepted
commit and must be root-owned, without symlinks or group/other write permission.
Its ancestors and executable locations must also remain root-controlled. The
tool checks the current full checkout and refuses changed/untracked source.
It does not download software or grant trust to an arbitrary repository.

Select an existing accepted account by name, UID, GID and supported shell.
For backup, use the account with only the accepted export/recovery permissions.
Privileged edge work may select the explicitly accepted root account. The
coordinator still receives only the forced worker protocol. Account creation,
OS group/ACL assignment, CA signing, host-key generation, secret custody and
source/runtime installation remain the independent bootstrap owner's duties.

The supplied private host key is unencrypted, owner-only and matches the exact
accepted Ed25519 public key. Its custody must permit unattended sshd startup.
The user CA uses a different Ed25519 key. The installer never receives the CA
private key. Certificates must contain the one selected worker principal; the
service does not accept password authentication, ordinary public keys, an
interactive shell, forwarding, user RC files or user-supplied environment.
These settings follow the [OpenSSH server configuration](https://man.openbsd.org/sshd_config).

Choose `ledger_mode: new` only for an independently established new owner with
no previous writer/ledger. The selected directory must be absent before the
first installation intent. `retained` requires the accepted directory, spool
and ledger to exist with their exact account ownership and `0700` permissions;
missing retained state is a hold. Recover it from custody before installing.
This distinction never establishes fencing of another host or an unknown task.

## Private configuration

The exact `hosting-owner-install/1` object has these fields:

| Field | Required value |
| --- | --- |
| `format` | `hosting-owner-install/1` |
| `source_commit`, `machine_id` | Accepted clean Git commit and actual `/etc/machine-id` |
| `account`, `uid`, `gid` | Exact existing worker account identity |
| `listen_address`, `port` | One canonical IPv4 address and dedicated port, integer 1024–65535 |
| `principal` | One simple SSH certificate principal |
| `source` | Absolute root-owned checkout path; must equal the executing checkout |
| `python`, `sshd`, `systemctl`, `ssh_keygen` | Absolute installed executable paths |
| `python_sha256`, `sshd_sha256`, `systemctl_sha256`, `ssh_keygen_sha256` | Exact executable byte digests |
| `host_private` | `{ "path": "/private/host-key", "sha256": "<exact-byte-digest>" }` |
| `host_public`, `user_ca` | Separate exact `ssh-ed25519 <base64>` public keys, without comments |
| `revoked_user_keys` | Explicit list of zero to 1024 distinct Ed25519 subject public keys revoked from certificate access |
| `data_directory` | A dedicated `/var/lib/hosting-owner-<name>` directory, excluding the installer state directory |
| `ledger_mode` | `new` or `retained` |
| `custody_ref` | Independently accepted worker/ledger custody record |

Use an actual supported interpreter and source/runtime paths available during
boot. The fixed service applies `ProtectSystem=full` and `ProtectHome=read-only`;
select writable backup restore destinations outside those protected locations.
It retains the host network namespace for the existing edge ownership checks.

The separate `hosting-owner-install-authority/1` object contains exactly
`format`, `config_sha256` (`provisioner.execution.readback_core.digest(config)`), `valid_from`,
`valid_until`, `change_ref` and `recovery_access_ref`. Its current window lasts
at most one hour. This private record binds the accepted installation and
independent recovery path; the installer does not authenticate or issue that
external authority.

```sh
python /opt/hosting-source/tools/owner_install.py \
  --config /private/operator/owner-install.json

sudo /opt/hosting-python/bin/python -I \
  /opt/hosting-source/tools/owner_install.py \
  --config /private/operator/owner-install.json \
  --authority /private/operator/owner-install-authority.json --execute
```

The first command only validates the input schema. Execution verifies the actual
machine, OS/systemd, account, clean source, executable digests and private/public
host-key match before preparing the endpoint. The operator files must be owned
by the executing root operator with private permissions.

## Durable installation and startup

The installer serializes through `/var/lib/hosting-owner-install/writer.lock`
and publishes an immutable `intent.json` before installing endpoint files.
The intent binds the complete configuration and generated file digests. It
retains a candidate, validates it with the actual `sshd -t`, then publishes:

| Destination | Contents |
| --- | --- |
| `/etc/hosting-owner/sshd_config` | Exact certificate/forced-command profile, `0600` |
| `/etc/hosting-owner/host-key` | Accepted private host key, `0600` |
| `/etc/hosting-owner/user-ca.pub`, `/etc/hosting-owner/principals` | Root-controlled authentication selection, `0644` |
| `/etc/hosting-owner/revoked-keys` | Explicit certificate-subject revocation list, `0644` |
| `/etc/systemd/system/hosting-owner.service` | Dedicated worker service |
| `/etc/tmpfiles.d/hosting-owner.conf` | Create `/run/sshd` with the standard root-owned `0755` privilege-separation directory at boot |
| `<data_directory>/spool`, `<data_directory>/ledger` | Exact private worker-owned directories, preserving retained contents |

Files are published atomically and never replaced by a repeat invocation.
Existing bytes/modes/owners must equal the original plan, with the revocation
list extended only by the retained identity-owner journal. Symlinks, foreign
endpoint files, altered native unit selection and systemd drop-ins are refused.
The installer validates the final daemon configuration, reloads systemd metadata,
checks the actual loaded unit path, then enables/starts only `hosting-owner.service`.
It checks active/enabled status and retains a timestamped private receipt.

The service waits for the accepted network-online ordering and runtime-directory
setup. It has no automatic restart or reload action. `KillMode=process` means a
service stop targets the SSH listener and does not purport to cancel/fence native
jobs already dispatched through child sessions. Before deliberately stopping or
changing it, reconcile active jobs through their native owners. Do not assume
that stopping SSH removes native effects.

The forced SSH environment trusts only the selected root-controlled checkout
through an exact Git `safe.directory` setting, allowing a restricted non-root
worker to verify that source. It does not trust arbitrary directories. No
client-supplied Git/environment overlay is accepted.

After an interruption, preserve the installation directory, source, keys and
owner state. Invoke the same configuration with current authority. The installer
can finish exact missing files and repeat idempotent systemd enable/start; it
never stops/restarts a healthy endpoint, changes the source selection or clears
native holds. An altered configuration or existing file requires maintenance
reconciliation instead of a new installation name or removed intent.

## Acceptance and verification

`WORKER_INSTALLED_REQUIRES_ENDPOINT_ACCEPTANCE` establishes installed files and
the observed unit state. It does not prove SSH reachability, CA issuance/revocation,
firewall policy, reboot recovery or native service qualification. Pin the returned
host public key in the coordinator target and run the accepted endpoint campaign
before staging live work. Workload ownership, job authorizations and native ledger
checks still run on every worker invocation.

Filesystem/host-command tests cover first installation, exact repeat, an
interrupted start, retained unknown operations, changed files/configuration,
missing custody, conflicting unit drop-ins and preservation of management SSH.
The disposable SSH lab uses this exact generated daemon profile, validates it
with native `sshd -t/-T`, parses the systemd unit, and exercises real certificate
SSH and forced-worker restrictions. It does not install a live endpoint or
reboot an accepted owner host.

The native SSH lab also replaces only its disposable revocation list and proves
that the revoked subject cannot authenticate a new connection, without restarting
the daemon. Revocation does not end an existing SSH session or fence a native job.
Use the [revocation owner](owner-revocations.md) for accepted live subject-key
denial and interrupted publication recovery. The initial installer never erases
unknown policy or silently removes a journaled revocation during repeat installation.
