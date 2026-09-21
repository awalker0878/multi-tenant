# Ubuntu guest hardening and service enrollment

The `ubuntu-24.04-services-v1` profile extends the existing hostname/time/kernel
baseline across Nutanix, VMware and OpenStack workloads. It owns the complete SSH
server configuration, scoped certificate principals and recovery public key,
recursive resolver selection, persistent journal bounds, collector TLS assets and
the log-forwarding action. Select it only where these files are assigned to this
role by the image and service owners.

`tools/guest_services.py` owns the controller-side contract for this profile. It
validates the closed `services` object — ownership assignment, resolver bounds,
account separation, certificate/key algorithms and asset hashes — before any
guest contact. The [guest inventory](native-guests.md) requires the complete
object and validates it; the [reviewed guest executor](guest-execution.md)
re-verifies the sealed asset hashes before running the profile. Validation is an
input check only: it issues no credential and asserts no host state.

The image must include OpenSSH server, systemd-resolved, chrony, rsyslog and its
GnuTLS module. Pre-provision non-root administrator and recovery accounts with
their separately approved privileges. The initial SSH session must already use
an Ed25519 user certificate trusted by the image; the inventory requires the
certificate algorithm before changing server authentication. The CA signing key
never enters the guest. Preserve independently managed OOB recovery access.

## Input

In the existing [guest access handoff](native-guests.md), set the target `profile`
and add `services` containing:

| Field | Required content |
| --- | --- |
| `ownership_ref` | Accepted assignment of the profile's guest files |
| `resolver_addresses` | One to eight approved IPv4 recursive resolvers; DNS UDP/TCP 53 is a separate scoped service path |
| `admin_users` | Existing non-root accounts, including the automation account |
| `user_ca_keys` | Exact Ed25519 public CA keys; overlapping old/new keys support controlled rotation |
| `revoked_user_keys` | Explicit Ed25519 user keys to revoke, including compromised certificate subject keys |
| `breakglass` | Separate existing `user` and independently held Ed25519 `public_key` |
| `log` | Collector IPv4 `address`, exact certificate `peer_name`, TCP `port`, and bounded `queue_mib` |
| `journal_mib` | Local journal capacity selected for this workload |
| `files` | `log_ca`, `log_certificate`, `log_key`, each with a private controller `path` and exact byte `sha256` |

Each ordinary user's certificate principal is
`<tenant_key>:<wsd_key>:<username>`. The role disables root/password/interactive
authentication, user authorized-key files, forwarding, tunnels and user startup
scripts. Only the distinct recovery account accepts its explicit raw public key.
The allowed-user list withdraws access for removed accounts; replace CA/key and
revocation inputs to rotate/revoke, and independently terminate existing sessions
when the incident policy requires immediate withdrawal. Reloading sshd alone does
not kill established sessions.

The controller verifies TLS asset hashes and parses the matching certificate/key
before contacting guests. Native copying suppresses secret diffs/output. Logs use
authenticated TLS, an exact peer name, a disk-assisted queue and persistent local
journals. A marker is emitted after reconnecting successfully with certificate
authentication. The collector owner must confirm that marker and tenant/source
attribution; sending it is not proof of receipt. Alert on collection loss and
queue capacity before operational activation.

Use the existing `configure_linux.yml` command. Changes are serial, validate SSH
and logging configuration before reload, then reconnect and check access. Failed
configuration leaves the operation stopped under native containment; it does not
relax the platform edge. Ansible check mode predicts changes without reconnecting
or emitting the marker. Native first-run/idempotence, certificate expiry/revocation,
collector loss/queue recovery and resolver failover remain target tests.

The [reviewed guest executor](guest-execution.md) snapshots and rebinds the exact
TLS/restic controller files into a private bundle and verifies them again before
running this profile. It binds check/configure mode and runtime, records attempts
before contact and holds uncertain outcomes. Original service files can no longer
change the sealed payload after preparation; this does not issue service
credentials or establish collector/protection acceptance.

`lab/run_guest_services_lab.py --require-engines` renders the actual templates and
checks effective ordinary/recovery SSH settings plus rsyslog syntax using real
installed daemons. It starts no daemon and changes no host configuration. This
profile is a bounded hardening implementation, not a claim of complete CIS or
Government of Canada control compliance. Workload-specific MAC policies, package
maintenance and application/data protection have separate owners and tests.

References: [OpenSSH server settings](https://man.openbsd.org/sshd_config),
[rsyslog TLS client](https://docs.rsyslog.com/doc/tutorials/tls_cert_client.html).
