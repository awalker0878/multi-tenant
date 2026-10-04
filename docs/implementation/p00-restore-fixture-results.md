# P00 database and attachment restore fixture

Prepared 2026-10-04. The [executable fixture](../../spikes/compatibility/restore/README.md) implements a real PostgreSQL database and attachment capture/restore experiment for P00.04. The first remote execution failed at archive copy after real PostgreSQL startup, schema/seed and the source writer denial succeeded. The correction streams the archive directly to the host with separate diagnostic logging; successful restoration is not claimed until a corrected run passes. Installed VMware/OpenStack facts and all native RF experiments remain **NOT RUN**.

## Candidate and actual scope

The official `docker.io/library/postgres:18.6-bookworm` image is the selected disposable experiment candidate. Resolution records the real upstream index and Linux/amd64 child digests; replay consumes that measured immutable lock. Exact server/client tools, image configuration/layers, operating-system packages and runner Docker versions are recorded from execution. This selection does not ratify the product's operated PostgreSQL version, topology, support policy or production image.

The fixture uses a single isolated PostgreSQL container with three separate clean databases for source, target and post-write recovery. The initial deterministic dataset has two synthetic tenants, four permit records, four attachment files and a source-write marker. Separate database roles represent its writers. No production records, secret values, endpoint addresses or native access are used.

The image runs as its observed non-root PostgreSQL user with no network, no published ports and no TCP listener. Memory-backed data directories and the container are removed after the experiment; evidence retains complete synthetic bundle bytes in base64 text envelopes. Application reconstruction here means rebuilding this declared database schema and attachment fixture. It does not demonstrate rebuilding a Linux guest or the Permit Desk web application.

## Coverage and interpretation

| Observation implemented | Actual proof required from the retained run | Feasibility relationship and remaining work |
| --- | --- | --- |
| Complete fixture capture | Source schema/records, attachment content and mode, configuration, writer inventory, all archive bytes and manifest hashes retained | Supports the synthetic data portion of F01/F03 and RF01/RF03. Owners must still accept representativeness and enumerate actual application/guest/key state. |
| Database and file consistency boundary | Source writer login disabled and its sessions terminated; attempted login/write fails; synchronous attachment writer stops through snapshot/export/copy; source logical and file state remains equal | A real fixture mechanism, not independent native fencing or proof of concurrent file/database crash consistency. Actual writer inventory and exclusion remain RF03/RF07. |
| Clean target restore | Actual `pg_restore` into a newly created database, full record equality, exact attachment set/digests/sizes/modes and no orphan relationships | Supports bounded restore compatibility on the same measured PostgreSQL patch. Native deployment, service readiness and cross-version behavior remain untested. |
| Invalid bundle rejection | Corrupted archive, missing attachment, unexpected file and changed manifest reject with exact diagnostics before any restore database is created | Partial/corrupt artifacts cannot reach this runner's restore admission. Does not prove signatures, hostile-source trust or interrupted/lost-acknowledgement native operation handling. |
| Two-tenant relational control | Foreign-tenant permit association fails a real composite foreign-key constraint and leaves state unchanged | Demonstrates fixture relationship integrity. No application authentication, row-level authorization or network tenant-isolation claim. |
| Pre-target-write source return | Target fixture writer never enabled; source login re-enabled; new source write accepted and read back; later final capture includes that write | Exercises meaningful synthetic state for the RF08 boundary. Actual VMware fencing/traffic/service return requires the approved native tuple. |
| Post-target-write recovery | Known permit/attachment/marker accepted at target; source remains disabled and lacks that write; target captured and restored to a third clean database; known write and attachment retained; new recovery write accepted | Exercises meaningful synthetic state for RF09 using a still-readable target. No recovery promise for already-lost uncaptured target data or stale-source failback. |
| Cleanup and bounded operation | Command timeouts, resource limits, actual durations and byte counts, container/data removal reported | Supplies fixture measurements. Accepted outage/loss/retention targets and native capacity measurements remain external scope. |

## Evidence record

Execution status is taken from the retained `report.json`, not from this procedure. The report binds the source/workflow hashes and immutable image input, commands/log hashes, positive observations and exact negative diagnostics. Every actual captured bundle is retained as a JSON envelope containing the original binary archive and file bytes, with its external manifest digest. No failed execution is silently converted into success; preserve failed run evidence before fixing the runner and execute again at the corrected source revision.

Run `37233785398`, source `ae634e325aa1e88bbcd8b35bf8d790e9e7d04f2b`, measured PostgreSQL 18.6 and reached the initial archive transfer. `pg_dump` exited zero, but the following `docker cp` could not find `/tmp/capture-1.dump`; cleanup succeeded. The observed copy failure is retained without asserting an unproven cause. The corrected runner streams binary `pg_dump` stdout directly into the host bundle, captures stderr separately, and records the archive header, exact byte count and hash. Its bounded process handling and lossless stdout evidence also retain partial output if export fails. Host Python identity is now recorded alongside the Docker and database tool inventory.

Corrected resolve/replay revisions, artifact digests, evidence IDs and outcomes are recorded from actual CI artifacts when available. The initial failure does not establish a restore or recovery pass.

## P00 consequence

Successful execution can add E2 real-dependency fixture evidence and reduce the untested synthetic data/recovery work. It cannot close G00.04, approve ADR-014, fill an installed platform tuple, identify accountable reviewers or manufacture lab authority. The [initial-route procedure](../qualification/feasibility/initial-route.md), [route review](p00-route-and-operations-review.md) and [decision/input review](p00-decision-and-input-review.md) retain the exact native and accountable-input obligations. Native F02/F04–F07 and the actual RF experiment results remain separately recorded.

The preferred proposal remains `application_rebuild_restore`. The experiment makes its state-preservation requirements executable while preserving current context, service and code-control direction. Historical implementation remains reference material only.

## Primary-source basis

The [official PostgreSQL image documentation](https://hub.docker.com/_/postgres) lists the candidate tag. [PostgreSQL 18 pg_dump](https://www.postgresql.org/docs/18/app-pgdump.html) defines a single-database logical export, including its consistent database snapshot and exclusion of cluster-wide roles. The fixture therefore recreates scoped roles explicitly and coordinates attachment files separately. [PostgreSQL 18 pg_restore](https://www.postgresql.org/docs/18/app-pgrestore.html) documents archive restoration and the transaction/error controls used here. Sources checked 2026-10-04; actual image identity and behavior still come from the captured registry and runtime observations.
