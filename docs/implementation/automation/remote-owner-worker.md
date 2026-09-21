# Remote edge and backup execution

The `remote_owner` delivery stage dispatches an exact, privately staged job to
its accepted owner machine over certificate SSH. `tools/owner_worker.py` is the
forced command on that host. It invokes the existing edge or restic executor
and returns its fixed receipt/manifest artifacts. Native credentials and source
exports stay on the owner host. The worker accepts no arbitrary command,
upload, executable argument list, recursive remote job or shell session.

`tools/remote_owner.py` is the coordinator side of that transport: it validates
the target and job and dispatches over certificate SSH using only a fixed forced
command and the staged job digest.

This is the selected reference transport for edge-host and backup-host work.
The coordinator and each worker have separate durable delivery journals. An
unknown SSH outcome holds the coordinator stage. Resume sends `observe`, which
can recover an already completed owner receipt but cannot start a new operation.
If a worker still runs, its local lock prevents another execution. Loss of SSH
is not evidence that its process stopped. Retain the owner ledger and use native
reconciliation for unknown outcomes. A local lock is not distributed fencing.

## Fixed endpoint installation

The [worker installer](owner-installation.md) now installs this dedicated profile,
validates the actual daemon configuration, preserves selected ledger custody and
enables its separate systemd service. It supports exact interrupted-install
resume without overwriting changed files or restarting native jobs.
The [subject revocation owner](owner-revocations.md) can subsequently deny selected
certificate subjects through the independent identity-management path while
preserving all previous revocations and existing native-job records.

Use a dedicated managed SSH endpoint with a pinned host key and an independently
recoverable approved source checkout at the same commit as the coordinator.
Source, interpreter, CA/principal policy and forced-command configuration remain
under platform-owner control. The worker account needs its selected owner's
privileges: export/read access for backup, isolated destination write access for
restore, or accepted nftables execution privilege for edge work. Do not grant
the coordinator ordinary shell access to obtain those privileges.

Configure the dedicated endpoint with certificate-only authentication, an exact
accepted principal and a fixed command using actual installation paths:

```text
PasswordAuthentication no
KbdInteractiveAuthentication no
AuthorizedKeysFile none
TrustedUserCAKeys /etc/hosting-owner/user-ca.pub
AuthorizedPrincipalsFile /etc/hosting-owner/principals
PubkeyAcceptedAlgorithms ssh-ed25519-cert-v01@openssh.com
PermitTTY no
PermitUserRC no
PermitUserEnvironment no
AllowAgentForwarding no
AllowTcpForwarding no
AllowStreamLocalForwarding no
PermitTunnel no
X11Forwarding no
ForceCommand /opt/hosting-python/bin/python -I /opt/hosting-source/tools/owner_worker.py --spool /var/lib/hosting-owner/spool --ledger /var/lib/hosting-owner/ledger
```

Restrict the accepted account and listening address in that dedicated service.
Validate the complete configuration with `sshd -t` before installing/reloading
it. Do not overwrite unrelated management SSH configuration. The worker checks
`SSH_ORIGINAL_COMMAND` equals `hosting-owner/1`, even though sshd has replaced
the requested command. The [OpenSSH server](https://man.openbsd.org/sshd_config)
and [client](https://man.openbsd.org/ssh_config) manuals define these controls.

Spool and ledger are real, private `0700` directories outside the source
checkout, owned by the worker account. Stage job files and referenced inputs as
`0600` files owned by that account through the service owner's existing private
configuration channel. The SSH dispatch endpoint cannot stage or edit jobs.
Protect and recover the ledger independently; do not give a replacement worker
an empty ledger while its predecessor may still run.

## Job and coordinator binding

Stage `<job_id>.json` in the owner spool. The same descriptor, containing paths
and digests but no credential bytes, is a coordinator `job` file.

| Field | Meaning |
| --- | --- |
| `format` | `hosting-owner-job/1` |
| `job_id` | Stable lowercase identity, 2–64 letters/digits/hyphens |
| `machine_id` | Actual 32-hex owner machine ID |
| `source_commit` | Exact clean source commit shared with the coordinator |
| `scope` | The five delivery scope fields |
| `generation` | Increasing worker generation for the WSD; each subsequent job gets a new generation |
| `kind` | `edge_policy`, `edge_containment` or `restic` |
| `parameters`, `files` | Adapter parameters and private file bindings, resolved on the worker |
| `delivery` | Exact coordinator `plan_sha256`, `step_id` and predecessor `dependencies` digests |
| `valid_from`, `valid_until` | Actual dispatch window, at most one hour |
| `dispatch_ref` | Owner's accepted job/dispatch record |

The worker performs the adapter's usual scope, binary, machine, namespace,
credential and native authority checks. A staged job does not override them.
Jobs for one WSD serialize through a shared worker ledger. Renaming a job or
raising its generation cannot bypass an uncertain predecessor.

The sole exception to forward workflow ordering is `edge_containment`, which
uses separately delegated incident authority and the same native edge ledger.
It can withdraw while the forward graph is held. Its parameters are `nft` and
`nft_sha256`, and its files are `spec` and `authority`. Every invocation performs
fresh native containment observation; historical cached receipts cannot mask a
reopened policy. `observe` cannot initiate a withdrawal. Unknown earlier writes
remain in the native history and prevent later reactivation.

The coordinator packet has parameters `ssh` and `ssh_sha256`, and files `job`,
`target`, `ssh_key`, `ssh_certificate`. The target is `hosting-owner-target/1`
with exact `address` (IP literal), `port`, `user`, `host_key` (one Ed25519 public
key), `machine_id`, `valid_from`, `valid_until` and `max_seconds` (10–3600).
SSH disables agents, proxies, forwarding, multiplexing, mutable user
configuration and automatic host-key updates. Temporary key/certificate copies
are removed after transport. The sealed original credential files remain under
their owner’s retention and renewal policy.

Completed responses bind job digest, machine, source and artifact bytes/digests.
The coordinator retains `remote-result.json` and the permitted native artifacts.
Backup manifests retain their original owner-host paths for snapshot checking;
do not rewrite them. Restore can consume privately transferred exact receipt
and manifest copies on an independently identified worker, with separate authority.

If SSH access expires during recovery, publish
`<step_id>.recovery-authority.json` in the coordinator inbox. This is
`hosting-owner-recovery-access/1` with the original `job_sha256`, `access_ref`
and `files` bindings for `target`, `ssh_key` and `ssh_certificate`. The renewed
target may change only `valid_from` and `valid_until`; address, account, host key,
machine ID, port and duration bound must remain identical. Original expired key
files can be removed. The coordinator retains the renewal record and sends only
`observe`. New credentials cannot change the staged job or redispatch its write.

## Evidence and limits

Integration tests exercise worker journals, capture handoffs, unknown outcomes
and a lost coordinator response without redispatch. The real disposable sshd in
`lab/run_owner_worker_lab.py` exercises certificate authentication and the actual
forced worker: receipt return, read-only observation, wrong-machine denial,
changed host-key denial and arbitrary-command rejection. Its backup executable
is synthetic; the separate restic laboratory exercises the real backup engine.

The worker protocol itself does not install a live endpoint, provision native credentials, remotely
attest a machine or qualify the underlying edge/backup service. The
[incident hook](incident-containment.md) can dispatch a predelegated remote
withdrawal when selected verification fails. It is not a continuous incident
scheduler or host failover mechanism. Kernel lease expiry still limits exposure
after controller loss. The [edge startup guard](edge-startup.md) establishes
denial before managed network attachment; installed boot/HA acceptance and
independent recovery remain separate.
