# File-export backup and isolated recovery

`tools/restic_run.py` captures a data-owner-produced file export into an existing
restic repository and verifies restored file bytes in a new destination. Native
execution accepts only `rest:https://` repositories with explicit identity and
credentials. No initialization, deletion, pruning, forced unlocking, automatic
mutation retry or restore over existing data is exposed.

## Protection boundary

Provision one repository per workload protection boundary on a TLS rest-server
with append-only client access. Retention administration and repository/key
recovery belong to separate custodians. Demonstrate server-side delete rejection
and recovery after the workload/primary platform is unavailable. A client setting
cannot establish immutability. Retain the repository identity, password and TLS
trust outside the workload's failure domain; do not put these secrets in Git.

The initial implementation protects ordinary files/directories on one filesystem.
The source must be a quiesced or immutable export produced under the data owner's
consistency procedure. Symlinks, special files, nested mounts and empty exports
are rejected. Hashes before and after capture detect ordinary changes; this does
not implement a database transaction barrier or application-consistent VM backup.
Snapshot success remains `CAPTURED_REQUIRES_RESTORE_TEST`.

## Configuration and capture

Provide a private `hosting-restic-export/1` configuration with these exact fields:

| Field | Value |
| --- | --- |
| `scope` | Environment, site, platform, tenant and WSD keys |
| `member`, `machine_id` | Stable guest/export identity and independently observed source machine ID |
| `source` | Canonical absolute path to the owned file export |
| `repository`, `repository_id` | Scoped TLS REST URL and native 64-character repository ID |
| `restic_sha256` | Exact SHA-256 of the approved installed restic executable |
| `valid_until` | Delegated service entitlement expiry, no more than 31 days away; renew explicitly |
| `consistency_ref` | Owner's export consistency procedure/record |
| `max_seconds` | Bounded execution budget, 1–3,600 seconds for this reference profile |

Credentials are a separate private JSON document containing exactly `password`
(repository encryption password), `username` and `http_password` (scoped REST
credentials). They enter the child environment, not the command line or receipt.
Ambient proxy, SSH backend and restic override variables are not inherited.

```sh
python tools/restic_run.py backup --config /private/backup/config.json \
  --credentials /private/backup/credentials.json --restic /usr/bin/restic \
  --ca-bundle /private/backup/ca.pem --output-root /private/backup/runs --execute
```

Omit `--execute` for offline validation. The private output root must exist; each
invocation creates a new private run directory. The native repository ID and
binary hash are checked before capture. The exact file manifest is stored in the
encrypted snapshot alongside the export. Snapshot tags bind the manifest digest
and tenant/WSD/member. Preserve `receipt.json` and `manifest.json` in the independent
evidence store. The attempt record precedes capture; an interrupted capture may
leave a retained snapshot, and absence of a receipt never authorizes deletion.

## Restore

On a separately provisioned recovery host, run the same tool with action `restore`,
the original configuration, distinct restore credentials, `--receipt`, `--manifest`,
`--target` and `--restore-authority`. The destination must not exist. The current
machine ID must differ from the source. The authority is bound to the canonical
configuration/receipt digests, exact recovery `machine_id` and absolute `target`,
`isolation_ref`, `change_ref`, `valid_from` and `valid_until` (at most one hour).
It must come from the controlled change system; a reference is not proof that
native recovery routing and identity are isolated.

Restore checks native snapshot identity, tags, host and paths, runs restic's
restore verification, then compares every recovered file's size and SHA-256 with
the captured manifest. It records elapsed restore time and data age. Success is
`RESTORED_FILE_BYTES_VERIFIED_NOT_APPLICATION_ACCEPTED`. Application validation,
measured service RPO/RTO, network isolation, key/catalogue recovery and data-owner
acceptance remain necessary before exposing the recovered service.

`lab/run_restic_lab.py` executes real encrypted local capture and restore, changes
the source after capture, and tests wrong-key and foreign-scope rejection. Its
report explicitly excludes remote append-only enforcement and application
consistency. Hosted CI exercises the Ubuntu-packaged engine; an actual image
pins its own reviewed binary digest and records its version.

Sources: [restic backup](https://restic.readthedocs.io/en/stable/040_backup.html),
[repository backends](https://restic.readthedocs.io/en/stable/030_preparing_a_new_repo.html),
[restore](https://restic.readthedocs.io/en/stable/050_restore.html).
