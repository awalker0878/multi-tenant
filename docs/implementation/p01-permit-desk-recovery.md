# P01 Permit Desk application and configuration recovery

P01.02/P01.06 now have an executable [complete workload fixture](../../deploy/fixtures/permit-desk/README.md)
and [recovery campaign](../../scripts/p01/run_permit_desk.py). Owner: SRE/qualification
engineering. Requirements R02/R29/R30/R31; criteria G01.02/G01.06. The fixture is a
qualification subject, not a new product service or a replacement for the accepted
Laravel/Python control-plane architecture.

Implementation is ready for real dependency execution. Seven local admission,
file-integrity, unsafe-configuration and manifest-isolation tests pass. Those tests
do not count as a measured PostgreSQL/container restore. Preserve actual CI results
and source bindings below after execution; G01 remains unreviewed.

## Implemented campaign

1. Build a separately owned, locked application image and install a new private
   PostgreSQL/application pair. Seed four permits/attachments across two tenants
   through real authenticated HTTPS.
2. Observe anonymous/invalid identity, foreign-tenant access, reader mutation,
   forged authority and duplicate-write denials. Verify database DDL/owner-role and
   backup-write denials, and compare complete state before and after the requests.
3. Stop the sole application writer; disable/check the database writer and its
   sessions. Capture a real custom-format `pg_dump`, every attachment, full logical
   rows, configuration and artifact identity. Preserve the bytes and digest.
4. Reject six defective capture variants before any restore installation exists.
   Restore the accepted capture with actual `pg_restore` into a fresh database and
   empty attachment volume, using new credentials and the same exact application
   image. Compare every logical row/file and configuration before starting service.
5. Read the restored application, reject the old credential and a foreign tenant,
   then accept/read a known new target write. Inject an invalid application
   configuration, observe process exit, restore captured configuration and verify
   complete data equality. Stop/restart PostgreSQL and check meaningful unavailable
   application responses while process liveness remains available.
6. Capture the quiesced target, confirm the original source is stale and fenced,
   restore the second capture into another fresh installation, read the target
   marker/attachment, and accept/read a new recovery write. Remove owned resources.

The [runbook](../operations/runbooks/permit-desk-recovery.md) defines the operational
sequence and receiving checkpoints. Timings are fixture observations only; no
accepted production outage, loss, backup retention or capacity target is inferred.

## Remaining scope

This increment uses disposable Compose installations and the same PostgreSQL patch.
It does not supply guest/native deployment, cross-version restore, unavailable-target
data recovery, external alert acknowledgement, Kubernetes fixture restore, object
storage restoration, signed promotion or operating acceptance. The separately
retained P00 pre-write/source-return and post-write recovery results keep their
original scope; this application campaign cannot silently extend those native claims.
