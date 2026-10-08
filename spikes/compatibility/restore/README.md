# Permit Desk capture and restore experiment

This P00.04 experiment uses a real disposable PostgreSQL server and real attachment files to test the proposed `application_rebuild_restore` consistency and recovery boundaries. It is a synthetic data fixture, not the Permit Desk web application or a VMware/OpenStack integration. Locked replay passed on 2026-10-04 in run `37234051654` at source `fcb9fe0ea9bde275b09dfc8c0547e89021edafc9`: 76 commands met their expectations, all 138 checks passed and three complete captures were retained. Four commands intentionally returned their required PostgreSQL rejection. See the [results, immutable evidence and scope](../../../docs/implementation/p00-restore-fixture-results.md).

Run on a disposable Linux/amd64 host with Python 3, Docker and Docker Buildx. The only connected download is the declared official PostgreSQL candidate image. The server runs with its observed non-root PostgreSQL UID, no network, no published ports, no TCP listener, a read-only root filesystem and disposable memory-backed data directories. It uses local trust authentication only inside that isolated container; no credential or native endpoint input exists.

```sh
python3 spikes/compatibility/restore/run.py \
  --workspace "$PWD" --output /tmp/p00-restore-replay --mode replay
```

The committed [input lock](inputs.lock.json) records the measured registry index and Linux/amd64 child digests resolved in run `37233785398`. The corrected passing run consumed that lock. Use the normal locked replay above with an unused output directory. When explicitly evaluating a changed candidate, resolve it into another unused output directory, then review and commit its measured `evidence/inputs.lock.json` before adopting that lock:

```sh
python3 spikes/compatibility/restore/run.py \
  --workspace "$PWD" --output /tmp/p00-restore-resolve --mode resolve
```

`--lock /absolute/path/to/inputs.lock.json` selects another explicit measured lock. Replay rejects changed candidate bytes, platform, registry/repository or mutable image references; it does not silently re-resolve a tag. Archive tool and server versions must match the declared PostgreSQL patch. The image is a fixture candidate, not an accepted operated database baseline.

## Executed procedure

The runner creates a UTF-8/C-locale source database, two synthetic tenants, four permits, four attachment files and a source write marker. Composite database constraints bind every attachment to a permit in the same tenant. The source, target and recovery database writers have separate non-superuser roles; fixture setup/export/restore uses the explicitly identified PostgreSQL administrator.

It disables the source writer's login, terminates that role's sessions and confirms an actual connection/write attempt fails with the specific PostgreSQL diagnostic. The synchronous attachment writer stops between snapshot, `pg_dump --format=custom`, and attachment copy. That boundary is explicit because a PostgreSQL snapshot alone does not coordinate external files.

Every capture records database export, canonical logical snapshot, attachment bytes/digests/sizes/modes, synthetic configuration, state inventory and all fixture writers. A manifest digest is retained outside the bundle. Before creating a target database or running `pg_restore`, the runner verifies that digest, exact file membership and each artifact digest/size. It deliberately corrupts the database archive, removes an attachment, adds an unexpected file and changes the manifest. Each case must produce its precise rejection and leave the rejected target database absent.

The valid bundle restores into a clean database using `pg_restore --single-transaction --exit-on-error`. It checks every logical record, attachment digest/size/mode and database relationship. A cross-tenant attachment reference must fail its composite foreign-key constraint; this tests relational integrity, not application authorization. The target writer remains disabled during validation.

Two distinct recovery boundaries then execute:

1. Before any target writer enablement, re-enable the source fixture writer, accept a new source write and independently read it back. Quiesce again, take a new complete capture and rebuild the target from that current state.
2. Enable the target fixture writer, commit a known new permit, attachment and marker, then quiesce. Confirm the retained source lacks this accepted target write and remains disabled. Capture the target's current state, restore to a third clean database, verify the known write and attachment, then accept/read back a new recovery write.

The selected post-write technique is clean-database forward recovery from the still-readable target. It does not prove recovery if that target or its uncaptured data has already been lost, nor reverse migration to the stale source.

## Evidence and limits

`evidence/report.json` records host Python identity, source/workflow hashes, GitHub revision/run identity when present, timings, exact commands, SQL, exit codes, specific negative expectations, logical observations, runtime inventory, write boundaries and cleanup. Raw logs retain their original bytes. Binary `pg_dump` stdout streams directly into the host bundle with stderr recorded separately; each archive also has standalone base64 evidence, byte count and SHA-256. The first run failed when `docker cp` could not find an archive after `pg_dump` exited zero. Its [failed report](../results/restore/run-37233785398/report.json) is retained separately without asserting a proven cause; the streaming correction passed all restore and recovery observations. Each `*-bundle.json` is a text evidence envelope containing the complete binary PostgreSQL archive and other bundle files encoded as base64, with their original manifest/digests. Decode only into a new isolated directory and verify the manifest before restoration. The original working directories are not required to recover the captured bytes.

The synthetic seed and logical comparisons are deterministic. PostgreSQL custom archives contain run metadata, so separate captures are not expected to have identical archive bytes. Their actual hashes are recorded individually. Command timing and small fixture byte counts describe this run only; they are not accepted outage, bandwidth or production capacity measurements.

No native platform API, VM rebuild, guest hardening, web service, external identity, traffic switching, business job, independent fence, signed artifact authority, shared-service integration, app authorization, encryption/key restoration, cross-version upgrade, physical/PITR recovery, lost acknowledgement or concurrent database/file writer crash is exercised. Attachment mode is checked; native filesystem owners, ACLs, extended attributes and key lineage are outside this candidate. Administrative access can bypass fixture writer gates. These limits remain explicit in P00 and the later Q07 work.

Primary references checked 2026-10-04: [official image](https://hub.docker.com/_/postgres), [PostgreSQL 18 pg_dump](https://www.postgresql.org/docs/18/app-pgdump.html), [PostgreSQL 18 pg_restore](https://www.postgresql.org/docs/18/app-pgrestore.html). Only the fixture's single database is exported; database-cluster roles are deliberately recreated as scoped disposable roles, not claimed to be included by `pg_dump`.
