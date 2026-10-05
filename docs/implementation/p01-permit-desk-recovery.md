# P01 Permit Desk application and configuration recovery

P01.02/P01.06 now have an executable [complete workload fixture](../../deploy/fixtures/permit-desk/README.md)
and [recovery campaign](../../scripts/p01/run_permit_desk.py). Owner: SRE/qualification
engineering. Requirements R02/R29/R30/R31; criteria G01.02/G01.06. The fixture is a
qualification subject, not a new product service or a replacement for the accepted
Laravel/Python control-plane architecture.

**Measured PASS:** [run 37249201881](https://github.com/awalker0878/multi-tenant/actions/runs/37249201881)
executed source `2c562dd70214b162c21269017062b243161d1141`. All 79 campaign checks and 88 bounded command
outcomes passed; all three owned installations were removed. Seven focused local
admission/integrity tests and the 65-test installer suite also pass. The canonical
register records this bounded E2 result as EV-P01-013; G01 remains unreviewed.

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

## Retained observations

[The verified retrieval record](https://github.com/awalker0878/multi-tenant/blob/27282f61d80bdcbddfbdc5094038a39706151833/verification/p01/permit-desk/run-37249201881/retrieval.json) binds the complete
report, raw command outputs and both original database/file capture envelopes to the
exact source. Examination verified 176 command-log hashes, 36 source bindings against
immutable Git tree entries, and six expected PostgreSQL denial diagnostics. Report
SHA-256: `54b5ed09463b15769662f65188ad1dd709bc45f51f4c75715e015701de71f94c`.

| Measured boundary | Observation |
| --- | --- |
| Initial application | Four permits and four attachments created and read through authenticated HTTPS across two tenants |
| Access and database denials | Anonymous/invalid identity, foreign list/attachment, reader write, forged tenant and duplicate request denied; all rows unchanged; runtime DDL/owner and backup write denied for the intended reason |
| Capture consistency | Sole application stopped, database runtime login disabled, no runtime sessions; fresh runtime login rejected; complete logical/file state unchanged across capture |
| Invalid capture admission | Corrupt database archive, missing attachment, unsafe configuration, unfenced writer, wrong image and stale external digest all rejected before destination allocation |
| [Initial capture](https://github.com/awalker0878/multi-tenant/blob/27282f61d80bdcbddfbdc5094038a39706151833/verification/p01/permit-desk/run-37249201881/source-bundle.json) | Four permits/attachments; 6,677-byte PostgreSQL archive; fresh target restoration with full state/configuration equality |
| Target application | New credentials accepted, old source credential and foreign tenant denied; `known_target_write` accepted and attachment read back |
| Failed configuration recovery | Unsupported configuration version actually exits nonzero; captured configuration and exact image restart service while complete state remains equal |
| Database outage/restart | Application requests return unavailable, liveness stays available, restart preserves the accepted target write and complete dataset |
| [Post-write capture](https://github.com/awalker0878/multi-tenant/blob/27282f61d80bdcbddfbdc5094038a39706151833/verification/p01/permit-desk/run-37249201881/target-bundle.json) | Five permits/attachments; 6,770-byte archive; fresh third installation preserves the target write and accepts `known_recovery_write`; original source remains stale and login-disabled |
| Cleanup | Three unique Compose projects and their database/attachment volumes removed; private credentials deleted |

The observed initial restore/start interval was 5.518 seconds and the configuration
rollback/start interval was 1.007 seconds. These tiny-fixture measurements exclude
production planning, transfer, full outage and operational review; they set no RTO/RPO.
The [fixture inventory](../../deploy/fixtures/permit-desk/README.md) includes the exact
configuration, credential references, schema, deterministic seed and writer boundary.

## Remaining scope

This increment uses disposable Compose installations and the same PostgreSQL patch.
It does not supply guest/native deployment, cross-version restore, unavailable-target
data recovery, external alert acknowledgement, Kubernetes fixture restore, object
storage restoration, signed promotion or operating acceptance. The separately
retained P00 pre-write/source-return and post-write recovery results keep their
original scope; this application campaign cannot silently extend those native claims.
