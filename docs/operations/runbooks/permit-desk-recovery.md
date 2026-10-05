# Rebuild and restore the synthetic Permit Desk fixture

Owner: SRE/qualification engineering. Applies only to the P01.02/P01.06 disposable
[workload fixture](../../../deploy/fixtures/permit-desk/README.md), with no native
platform permissions. The [implementation record](../../implementation/p01-permit-desk-recovery.md)
separates execution evidence from this procedure. This is not the complete control-plane
recovery runbook or an accepted production RTO/RPO.

1. Start with an exact clean source revision, the committed image/dependency locks,
   Docker Engine/Compose, OpenSSL and a new evidence directory outside the checkout.
   Execute the documented campaign; it records the source and builds the fixture's
   private application image. Do not reuse unknown images or an existing project.
2. The source fixture enumerates all state and writers. Stop its sole HTTPS writer,
   revoke the runtime database login, terminate/check sessions, and prove fresh login
   denial. A mere successful dump does not establish this boundary.
3. Capture the database archive, complete attachment inventory/bytes, logical records,
   configuration and artifact identity while the writer is stopped. Retain the external
   capture digest. Require equal logical/file state before and after capture. An orphan
   file or missing/damaged attachment fails the capture; reconcile before proceeding.
4. Validate all captured identities and bytes before creating the restore installation.
   Recreate isolated identities with fresh credentials, an empty database and empty file
   volume. Restore via the authenticated migrator with one transaction/error stopping,
   then restore the exact files and restricted grants. Compare all rows, timestamps,
   ownership relationships, file digests/lengths/modes and nonsecret configuration.
5. Start the same immutable application image with the restored configuration. Test
   authenticated reads, old-credential/foreign-tenant denial, and a new permitted write
   with attachment readback. Keep the original source stopped and its login disabled.
6. A configuration rollout that fails boot may return to the captured configuration
   and exact image only after checking unchanged data. The campaign measures this case
   with an unsupported configuration version; it does not prove database-schema or
   arbitrary application-version rollback compatibility.
7. Once the target has accepted writes, never treat the older source as current. This
   campaign captures the still-readable quiesced target and restores it into a third
   clean installation, verifying the known target write before accepting another write.
   Uncaptured writes on an already-lost target remain outside the observation.
8. Inspect the report, captures, command output and cleanup outcome. Keep credentials,
   private CA keys and runtime directories out of evidence. Remove only each generated
   project and its volumes. Cleanup failure fails the campaign and retains the private
   path for remediation; never claim a pass from a partial run.

Remaining P01.06 work includes protected evidence-store restore, actual external alert
receipt/acknowledgement, wider deployment failure cases and operational review. The
fixture's successful restore cannot pass G01 or qualify a VMware/OpenStack route.
