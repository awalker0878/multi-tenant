# Scoped SSH certificate issuer

[Automation home](README.md) · [Identity and independent recovery](../../architecture/shared-services/3-identity-certificates-keys-and-independent-recovery.md) · [Worker installation](owner-installation.md) · [Worker revocation](owner-revocations.md)

`provisioner/execution/ssh_issuer.py` signs Ed25519 user certificates on an independently accepted
issuer host. Each profile owns one CA, one principal, an explicit IPv4 source
scope and one retained serial/revocation ledger. It invokes the accepted local
OpenSSH signer, then verifies the certificate signature, trusted CA, subject,
serial, identity, validity and every grant with the pinned cryptography runtime.
The subject's private key is never an issuer input. CA private material stays
outside source, worker artifacts and Terraform state.

This implements issuance and issuer-side subject denial. It does not select a
site's PKI product, establish issuer custody, provision a CA, qualify a hardware
signer, rotate trust roots or grant an unreviewed identity. The accepted policy
supplies the actual lifetime; the one-hour implementation ceiling follows the
bounded operation authority and is not a universal cryptoperiod.

## Accepted inputs

All input files are private, owner-only strict JSON. Unknown fields fail. The
`hosting-ssh-issuer/1` configuration has these exact fields:

| Fields | Required value |
| --- | --- |
| `format` | `hosting-ssh-issuer/1` |
| `source_commit`, `source` | Exact clean 40-character commit and absolute installed checkout |
| `machine_id`, `uid` | Actual issuer machine ID and executing account |
| `ssh_keygen`, `ssh_keygen_sha256` | Accepted absolute executable and exact bytes |
| `ca_private` | Object containing absolute `path` and `sha256`; private parent directory required |
| `ca_public` | Exact `ssh-ed25519` public key with no comment |
| `principal` | One accepted worker/service principal |
| `source_ranges` | Sorted unique canonical IPv4 CIDRs, at most 32; unrestricted source is unsupported |
| `maximum_validity_seconds` | Selected positive lifetime, at most 3,600 seconds |
| `serial_floor` | Independently accepted first available nonzero unsigned 64-bit serial |
| `data_directory` | Absolute private issuer ledger, separate from source and CA key |
| `policy_ref`, `recovery_ref` | Accepted scope/lifetime and independent custody records |

The host checks account, machine, clean source, source custody, binary bytes and
location, private CA bytes and the public identity derived by `ssh-keygen -y`.
This profile uses an already provisioned local unattended key. A passphrase or
interactive signer cannot trigger an unrecorded fallback; missing signing access
holds execution. A different signing technology needs its own accepted adapter.

A `hosting-ssh-issuer-request/1` record contains `format`, `config_sha256`,
`operation_id`, `action`, `subject` and `identity_ref`. The digest uses the same
canonical `readback_core.digest` representation as the other owner protocols.
`subject` is one exact Ed25519 public key, distinct from the CA. Enrollment and
role acceptance belong to `identity_ref`; the tool does not infer authorization
from possession of a public key.

For `action: issue`, also provide `valid_after` and `valid_before` as absolute
integer Unix seconds and `source_range` as a single CIDR within the accepted
profile. Issuance must be currently valid, entirely inside the current issuance
authority and no longer than the selected maximum. There is no relative-time
renewal. Renewal is a newly accepted request and consumes a new serial.

For `action: revoke`, omit the three issuance fields. The exact subject is
permanently denied further issuance in this ledger. Repeating the same operation
cannot change the subject or undo denial.

A `hosting-ssh-issuer-authority/1` record contains `format`, `request_sha256`,
`action`, `ledger_mode`, `valid_from`, `valid_until` and `change_ref`. Its window
must be current and at most one hour. `action` is `issue`, `observe` or `revoke`;
`observe` refers to an original issuance request and cannot sign a certificate.
`ledger_mode: new` explicitly permits initial ledger creation. Subsequent and
recovery operations use `retained`; missing history then holds. Observation
always requires retained custody. Changing this authority field does not change
the accepted issuer policy or the original request.

## Execute, recover and revoke

Validate private accepted inputs before requesting a native operation:

```bash
python -m provisioner.execution.ssh_issuer --source-root /opt/hosting-source --config /private/issuer.json --request /private/request.json
python -m provisioner.execution.ssh_issuer --source-root /opt/hosting-source --config /private/issuer.json --request /private/request.json \
  --authority /private/authority.json --execute
```

The first accepted ledger event fixes the policy. A local exclusive lock covers
issuance and denial together. `ISSUE_STARTED` durably consumes a serial before
files are created or the signer runs. `ssh-keygen` receives absolute validity,
one principal, `clear` extensions and the exact source-address critical option.
No forwarding, PTY, agent or user startup extension is granted. Endpoint policy
and the worker's fixed command continue to enforce their own limits.

Every observed certificate is cryptographically verified and synced before
`CERTIFICATE_OBSERVED` is journaled. The private receipt gives its path, digest,
serial and original validity. Successful repeats verify retained history and
bytes without signing. If the signer returned a certificate but its reply was
lost, a fresh `observe` authority verifies that same file and completes the
handoff. If no complete valid certificate survives, the reserved serial remains
unknown and cannot be used again. Independently authorize a new request only
after addressing the possible old credential; do not delete the old attempt.

Observation may read an expired or subsequently revoked certificate. Its
receipt retains the original absolute validity and reports `subject_revoked`;
it does not represent renewed authentication access. Earlier completed
certificates remain checked even when later operations succeed. Corrupt or
missing retained records hold further work.

Issuer revocation writes `SUBJECT_REVOKED` before publishing its receipt. Even a
lost receipt cannot permit later renewal. The receipt supplies the sorted union
of denied subject keys. Independently authorize and apply those keys with
`provisioner/execution/owner_revocations.py` for each relevant endpoint. Issuer denial alone does
not invalidate an already issued certificate at SSH servers. Endpoint denial
affects new authentication; neither operation terminates existing sessions or
fences their native tasks.

## Custody and evidence limits

The accepted CA must have one effective signing writer and a complete protected
serial history. An application lock cannot exclude a second copy of its private
key. Recreating or rolling back the whole ledger is not locally detectable;
independent recovery must preserve the policy, reserved serials, certificates
and denial history together. A retained CA cannot be initialized at an invented
serial floor. Keep issuance held when old custody is uncertain. Policy/source
replacement, key rotation and CA migration need separately accepted maintenance;
this tool does not rewrite the original policy or bypass an existing hold.

Local tests use actual OpenSSH signatures and exercise altered signatures,
wrong CA/subject/grants, consumed unknown serials, lost responses, concurrent
writers, revocation and historical observations. The worker SSH laboratory uses
the issuer's real certificate, exercises source-address rejection, denies renewal
at the issuer and then propagates the denial through the existing endpoint owner.
Its synthetic identities and backup engine do not establish installed issuer,
platform or independent recovery qualification.

Interface basis: [OpenSSH ssh-keygen](https://man.openbsd.org/ssh-keygen) and
[cryptography 46.0.4 SSH certificate verification](https://cryptography.io/en/46.0.4/hazmat/primitives/asymmetric/serialization/).
