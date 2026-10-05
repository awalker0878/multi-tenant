# Stateful dependency fixture recovery

Owner: SRE with Lifecycle and Assurance. Packages P01.02/P01.05/P01.06;
criteria G01.02/G01.05/G01.06. This runbook is for the disposable development fixture.
It supplies no operated authority, production credential, RPO/RTO or gate acceptance.

## Admission and installation

1. Use a clean checkout of the recorded full source commit on Linux/amd64 with Docker
   and Compose. Verify the committed stateful input lock, the client wheel lock and
   source archive hashes. The campaign rejects mismatches before installing services.
2. Invoke `python scripts/p01/run_stateful.py --source-revision <full-commit> --output <new-absolute-directory-outside-source>`.
   The directory must not exist. The campaign creates a private runtime parent and
   random synthetic passwords, a local CA and JWT signing key. Do not supply operated
   credentials, customer content or native endpoints.
3. The campaign builds clients from their hash-locked requirements and both S3 binaries
   from fixed public source. Inspect retained image IDs and Go module/build provenance.
   No ports are published on the host. Probe clients join only their dependency's
   internal network. Internal Temporal RPC services bind container loopback.
4. PostgreSQL bootstraps separate Temporal and visibility databases and users. A one-shot
   schema tool owns DDL; runtime users receive DML and cannot assume migrator roles.
   The migrator logins are disabled before the server starts. Local database readiness
   runs an actual SQL query as the PostgreSQL OS identity; the client probe separately
   verifies authenticated TLS, private runtime permissions and exact denial diagnostics.

## Recovery witnesses

- Broker: publish a persistent message with a broker confirmation, consume without an
  acknowledgement, stop and restart the dependency, then verify the same bytes and
  redelivery flag. Acknowledge and confirm the queue is empty.
- Workflow: start a synthetic waiting workflow with no activities or native effects.
  Record its workflow ID and run ID, stop the probe worker and Temporal/PostgreSQL,
  restart the dependencies and worker, verify it still waits, then signal and complete
  the same recorded execution. Do not substitute a newly started execution.
- Evidence: capture a specific retained S3 object version after a later version exists.
  Record bucket, key, version, byte length, SHA-256 and compliance retention. Verify the
  pinned version survives a store restart and differs from the latest object bytes.
  Restore those bytes into the independent empty second store. Preserve the source
  identity in object metadata and retain the returned new version ID. Verify equal
  bytes, equal-or-longer retention, administrator deletion denial and restart survival.

Negative probes must receive the expected authentication/authorization failure;
a generic exception is not an authorization pass. Dependency outages are classified
separately. Broker principal deletion and evidence user disablement must reject fresh
connections both before and after dependency restart. Unchanged broker bootstrap
definitions must not resurrect the deleted principal; the restarted evidence store
must accept administrator readiness while still rejecting its disabled runtime user.
Temporal signing-key withdrawal is tested after a server restart; this is not a
measurement of hot issuer revocation latency.

## Evidence and cleanup

Every subprocess has bounded execution and retained stdout/stderr hashes. Probe
results include their explicit checks. The report binds source files and input locks,
records image IDs, capture identity and restored version identity, and reports cleanup.
Keep the workflow, artifact, report and immutable source records together.

The runner collects logs, removes only its Compose project and volumes, checks for
remaining containers/networks/volumes and scans output for its generated credentials.
An accidental credential-bearing output is withheld and fails the run. Do not call a
failed or incomplete cleanup a pass. Failed disposable CI runners are discarded by
the hosted runner; investigate the retained failure before replaying.

Product transactional messaging, shared Console sessions/cache, external alert receipt,
production retention authority and dependency HA require their own work. The
[implementation record](../../implementation/p01-stateful-dependencies.md) owns the
measured results and their limitations.
