# Revoke worker certificate subjects

`tools/owner_revocations.py` implements the identity owner's deny-only maintenance
operation for an [installed worker endpoint](owner-installation.md). It adds
explicit Ed25519 subject keys to the daemon's revocation list. The operation does
not change the CA, account, principal, host key, listener, source or native jobs,
and it cannot remove a revocation. Use the independently accepted root management
path, not the worker's restricted dispatch protocol.

Revocation denies subsequent authentication with the selected subject keys. It
does not terminate authenticated sessions, cancel a native task or establish
native writer exclusion. Maintain the independent recovery access recorded in
the authority; continue reconciling existing jobs through their actual owners.

## Exact inputs and execution

Keep the original `hosting-owner-install/1` configuration. Its source, account,
machine and executable checks still apply. The original staged private host-key
file can have been removed: this operation verifies the installed key's bytes
against the accepted digest without retrieving or copying signing material.

The `hosting-owner-revocation/1` request has exactly:

| Field | Meaning |
| --- | --- |
| `format` | `hosting-owner-revocation/1` |
| `config_sha256` | `provisioner.execution.readback_core.digest` of the original installation configuration |
| `operation_id` | Stable operation identifier retained on retry |
| `keys` | One to 256 distinct, sorted `ssh-ed25519 <base64>` subject public keys, without comments |
| `identity_ref` | Identity/incident owner's accepted subject-revocation decision |

The separate `hosting-owner-revocation-authority/1` record contains exactly
`format`, `request_sha256`, `valid_from`, `valid_until`, `change_ref` and
`recovery_access_ref`. The hash uses the same canonical JSON digest. The current
window lasts at most one hour. A renewed authority can change its window and
references while still binding the same immutable request; it cannot substitute
different subjects under a previously used operation ID.

```sh
sudo /opt/hosting-python/bin/python -I \
  /opt/hosting-source/tools/owner_revocations.py \
  --config /private/operator/owner-install.json \
  --request /private/operator/revoke-worker-subject.json \
  --authority /private/operator/revoke-worker-authority.json --execute
```

Without `--execute`, only the private input contract is validated. Live execution
verifies the current host and original installation intent, then checks all
static endpoint files and the installed host key. Foreign CA/principal/unit
changes remain a hold; revocation is not implicit adoption or endpoint repair.

## Durable denial and interrupted recovery

The operation shares the installer's `/var/lib/hosting-owner-install/writer.lock`.
Before publishing a new list it appends `REVOCATION_REQUIRED`, with the exact
request and current authority, to the private hash-linked journal in
`/var/lib/hosting-owner-install/revocations`. Replay checks sequence, chronology,
scope, original authority time and operation identity.

The effective policy is the union of the initial installation list and every
accepted journaled request, including an interrupted publication. A repeated
request does not append another event. A different subject set under the same
operation ID is rejected. The implementation caps the accumulated set at 16,384
keys; larger identity transitions require a separately accepted procedure.

The list is written to a new file, flushed, and atomically replaces only
`/etc/hosting-owner/revoked-keys`. Its ownership, mode and expected prior bytes
are checked before publication and the exact result is read back. This follows
the [OpenSSH RevokedKeys requirement](https://man.openbsd.org/sshd_config#RevokedKeys)
to keep the file consistent for concurrent authentication attempts. No daemon
restart or reload is needed.

If publication or its reply is interrupted, keep the journal and invoke the same
request with current authority. A recognized older list can be replaced by the
strongest recorded denial. An unknown list, extra independent revocations,
missing/unreadable file or altered ownership stays held; the tool never erases
unrecognized identity controls. Initial installation/resume also consults this
journal, so repeating the original installer cannot restore a revoked subject.

The receipt reports `SUBJECTS_REVOKED_FOR_NEW_AUTHENTICATION`, exact input/policy
digests and observation time. `existing_sessions_terminated`, `native_fencing`
and `production_activation` are false. Protect installation and revocation
history together in independent custody: local hash chaining cannot detect loss
of an entire final history segment plus a correspondingly rolled-back policy.
All configuration writers must honor the same ownership/lock boundary; it does
not fence an independent root administrator.

## Verification

Tests cover monotonic updates, exact repeated requests, lost replies, interruption
after durable intent, renewed authority, changed subjects, unknown stronger
policy, missing files, changed static trust, corrupt records and a competing
installation lock. Repeating the original installer preserves revoked subjects.
The real SSH lab seeds a disposable installed-profile handoff, runs this actual
revocation owner/atomic publisher, then verifies that the previously working
certificate is denied without restarting sshd. Its host-installation handoff is
synthetic; it does not claim installed-site identity, bootstrap or native fencing
acceptance.
