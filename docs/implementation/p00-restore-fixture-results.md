# P00 database and attachment restore fixture

Prepared 2026-10-04. The [executable fixture](../../spikes/compatibility/restore/README.md) implements a real PostgreSQL database and attachment capture/restore experiment for P00.04. Locked replay **passed** in run `37234051654` at source `fcb9fe0ea9bde275b09dfc8c0547e89021edafc9`: 76 bounded commands met their expectations and all 138 checks passed, including four expected PostgreSQL rejections. Three complete database/attachment captures and both fixture recovery boundaries were exercised. The initial failed run remains retained. Installed VMware/OpenStack facts and all native RF experiments remain **NOT RUN**.

## Candidate and actual scope

The official `docker.io/library/postgres:18.6-bookworm` image is the selected disposable experiment candidate. Resolution records the real upstream index and Linux/amd64 child digests; replay consumes that measured immutable lock. Exact server/client tools, image configuration/layers, operating-system packages and runner Docker versions are recorded from execution. This selection does not ratify the product's operated PostgreSQL version, topology, support policy or production image.

The fixture uses a single isolated PostgreSQL container with three separate clean databases for source, target and post-write recovery. The initial deterministic dataset has two synthetic tenants, four permit records, four attachment files and a source-write marker. Separate database roles represent its writers. No production records, secret values, endpoint addresses or native access are used.

The image runs as its observed non-root PostgreSQL user with no network, no published ports and no TCP listener. Memory-backed data directories and the container are removed after the experiment; evidence retains complete synthetic bundle bytes in base64 text envelopes. Application reconstruction here means rebuilding this declared database schema and attachment fixture. It does not demonstrate rebuilding a Linux guest or the Permit Desk web application.

## Coverage and interpretation

| Observation executed | Passing observation in the retained run | Feasibility relationship and remaining work |
| --- | --- | --- |
| Complete fixture capture | Source schema/records, attachment content and mode, configuration, writer inventory, all archive bytes and manifest hashes retained | Supports the synthetic data portion of F01/F03 and RF01/RF03. Owners must still accept representativeness and enumerate actual application/guest/key state. |
| Database and file consistency boundary | Source writer login disabled and the session-termination query executed with no active fixture sessions; attempted login/write fails; synchronous attachment writer stops through snapshot/export/copy; source logical and file state remains equal | A real fixture mechanism, not independent native fencing or proof of concurrent file/database crash consistency. Actual writer inventory and exclusion remain RF03/RF07. |
| Clean target restore | Actual `pg_restore` into a newly created database, full record equality, exact attachment set/digests/sizes/modes and no orphan relationships | Supports bounded restore compatibility on the same measured PostgreSQL patch. Native deployment, service readiness and cross-version behavior remain untested. |
| Invalid bundle rejection | Corrupted archive, missing attachment, unexpected file and changed manifest reject with exact diagnostics before any restore database is created | Partial/corrupt artifacts cannot reach this runner's restore admission. Does not prove signatures, hostile-source trust or interrupted/lost-acknowledgement native operation handling. |
| Two-tenant relational control | Foreign-tenant permit association fails a real composite foreign-key constraint and leaves state unchanged | Demonstrates fixture relationship integrity. No application authentication, row-level authorization or network tenant-isolation claim. |
| Pre-target-write source return | Target fixture writer never enabled; source login re-enabled; new source write accepted and read back; later final capture includes that write | Exercises meaningful synthetic state for the RF08 boundary. Actual VMware fencing/traffic/service return requires the approved native tuple. |
| Post-target-write recovery | Known permit/attachment/marker accepted at target; source remains disabled and lacks that write; target captured and restored to a third clean database; known write and attachment retained; new recovery write accepted | Exercises meaningful synthetic state for RF09 using a still-readable target. No recovery promise for already-lost uncaptured target data or stale-source failback. |
| Cleanup and bounded operation | Command timeouts, resource limits, actual durations and byte counts, container/data removal reported | Supplies fixture measurements. Accepted outage/loss/retention targets and native capacity measurements remain external scope. |

## Evidence record

Execution status is taken from the retained `report.json`, not from this procedure. The report binds the source/workflow hashes and immutable image input, commands/log hashes, positive observations and exact negative diagnostics. Every actual captured bundle is retained as a JSON envelope containing the original binary archive and file bytes, with its external manifest digest. No failed execution is silently converted into success; preserve failed run evidence before fixing the runner and execute again at the corrected source revision.

Run `37233785398`, source `ae634e325aa1e88bbcd8b35bf8d790e9e7d04f2b`, measured PostgreSQL 18.6 and reached the initial archive transfer. `pg_dump` exited zero, but the following `docker cp` could not find `/tmp/capture-1.dump`; cleanup succeeded. The observed copy failure is retained without asserting an unproven cause. The corrected runner streams binary `pg_dump` stdout directly into the host bundle, captures stderr separately, and records the archive header, exact byte count and hash. Its bounded process handling and lossless stdout evidence also retain partial output if export fails. Host Python identity is now recorded alongside the Docker and database tool inventory.

The [passing replay report](../../spikes/compatibility/results/restore/run-37234051654/report.json) binds source `fcb9fe0ea9bde275b09dfc8c0547e89021edafc9` to [GitHub run 37234051654](https://github.com/awalker0878/multi-tenant/actions/runs/37234051654). It ran from `2026-10-04T20:56:48.135355Z` to `2026-10-04T20:57:07.088924Z`. Of 76 commands, 72 returned success and four returned their required rejection exit/diagnostic; all 138 explicit checks passed. Three input-lock mutations and four invalid bundle variants were rejected. Each invalid bundle left the rejected target database absent. The observed interval describes this tiny fixture, not an accepted application outage or capacity target.

The [retrieval record](../../spikes/compatibility/results/restore/run-37234051654/retrieval.json) records verified source bindings, raw logs and capture envelopes. Report SHA-256: `96be5bc02a704b0a1fe739a4f4db93b09ec40396d7776f2139c8c322beef0f8b`. GitHub artifact ZIP SHA-256: `8cbcff75bfb899ba0465356e9126a56189c028e55fa7e043ed0ecfb7f2ed6368`. All 11 source/workflow bindings, command-log hashes, streamed archive bytes and complete base64 bundle envelopes were verified on retrieval. The [first run report](../../spikes/compatibility/results/restore/run-37233785398/report.json) remains separate and failed; the later pass does not rewrite that outcome.

### Measured image and runtime

| Identity | Measured value |
| --- | --- |
| Candidate | `docker.io/library/postgres:18.6-bookworm`, `linux/amd64` |
| Upstream index digest | `sha256:3725f4e2499eef5134592b3b4ab79a543ed7f8e533b05b5b637af926630f6650` |
| Replayed child manifest | `sha256:9e73daeb439141c2b11eea2463f5f1a3b269fd90d897b41cddb7cb440f21aa5d` |
| Image configuration digest | `sha256:8d76d8de17e883d3995f76252e260bc6b7761e9c23edbf3356b0676d37c49ddb` |
| Input lock SHA-256 | `122ba9014bb072c4304d7dc7764d17e4ecd0e29df8c9ef8cea5cdccc457fcda9` |
| Server / psql / pg_dump / pg_restore | PostgreSQL `18.6`, Debian package `18.6-1.pgdg12+2`; server version number `180006` |
| Container operating system / user | Debian GNU/Linux 12 Bookworm; PostgreSQL UID/GID `999:999` |
| Host tools | Python `3.12.3`; Docker client/server `28.0.4`; Buildx `0.37.1` |

The [committed input lock](../../spikes/compatibility/restore/inputs.lock.json) was resolved during the first run and consumed by the corrected replay without tag resolution. The retained [runtime log](../../spikes/compatibility/results/restore/run-37234051654/010-server-runtime.log), [OS package inventory](../../spikes/compatibility/results/restore/run-37234051654/011-os-packages.log) and image/container inspection logs establish the observed environment. The runner verified no network, published ports or PostgreSQL TCP listener; the root filesystem was read-only, with 1 CPU, 768 MiB memory and bounded disposable data mounts. Cleanup removed the container and its disposable data.

### Preserved state and recovery observations

The initial capture contained two tenants, four permits, four attachments and `last_source_write`. All corresponding target records, attachment bytes/sizes/modes and relationships matched exactly. The prohibited cross-tenant attachment reference failed its specific foreign-key diagnostic and left the logical dataset unchanged. This is database relationship integrity, not application authorization.

Before target writer enablement, the source writer was reopened and committed `source_return_write`, then disabled again. The final source capture included that accepted write and restored into a fresh target database. The target writer was then enabled and committed `known_target_permit`, `known_target_attachment` and `known_target_write`. Source login remained disabled and readback confirmed the retained source lacked that target marker.

After target quiescence, its complete state restored into a third clean database. The known permit, attachment, marker and relationships survived; the recovered writer then committed `recovery_write`, which was independently read back. The post-write strategy relies on a readable target for capture. It does not demonstrate recovery after loss of uncaptured target data or authorize restarting a stale source.

| Complete evidence envelope | Captured state | Artifact bytes, excluding manifest |
| --- | --- | ---: |
| [Initial capture](../../spikes/compatibility/results/restore/run-37234051654/initial-capture-bundle.json) | Initial source dataset and first source marker | 10,804 |
| [Final capture](../../spikes/compatibility/results/restore/run-37234051654/final-capture-bundle.json) | Source dataset plus accepted source-return marker | 10,982 |
| [Post-write capture](../../spikes/compatibility/results/restore/run-37234051654/post-write-capture-bundle.json) | Five permits/attachments and three markers, including the known target write | 11,800 |

Each envelope preserves its original binary custom archive, synthetic configuration, writer inventory, logical snapshot, attachment files and manifest. Digests identify each actual capture; separately captured archives need not be byte-identical because PostgreSQL archive metadata includes run-specific values.

## P00 consequence

The passing run supplies E2 real-dependency fixture evidence and completes this bounded synthetic data/recovery experiment. It cannot close G00.04, approve ADR-014, fill an installed platform tuple, identify accountable reviewers or manufacture lab authority. The [initial-route procedure](../qualification/feasibility/initial-route.md), [route review](p00-route-and-operations-review.md) and [decision/input review](p00-decision-and-input-review.md) retain the exact native and accountable-input obligations. Native F02/F04–F07 and the actual RF experiment results remain separately recorded.

The preferred proposal remains `application_rebuild_restore`. The experiment makes its state-preservation requirements executable while preserving current context, service and code-control direction. Historical implementation remains reference material only.

## Primary-source basis

The [official PostgreSQL image documentation](https://hub.docker.com/_/postgres) lists the candidate tag. [PostgreSQL 18 pg_dump](https://www.postgresql.org/docs/18/app-pgdump.html) defines a single-database logical export, including its consistent database snapshot and exclusion of cluster-wide roles. The fixture therefore recreates scoped roles explicitly and coordinates attachment files separately. [PostgreSQL 18 pg_restore](https://www.postgresql.org/docs/18/app-pgrestore.html) documents archive restoration and the transaction/error controls used here. Sources checked 2026-10-04; actual image identity and behavior still come from the captured registry and runtime observations.
