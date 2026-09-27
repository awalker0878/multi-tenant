# Temporal deployment and admission gate

## Runtime boundary

`AdmittedMigrationJob` is the active B09 workflow. Admission requires the four
current B07 approvals. Its first Activity rechecks the live plan, workload,
approval quorum and revocation epoch through PostgreSQL. The result is a gate
observation only. The projector records `HELD` even if the gate passed because
no qualified native provisioning or migration graph is deployed. The separate
`MigrationApprovalGate` exercises a durable operator wait and timer; it is not
used by the fully approved job path and has no platform mutation capability.

The outbox dispatcher's `TemporalWorkflowStarter` starts `AdmittedMigrationJob`
under the immutable job ID, with `REJECT_DUPLICATE`, a bound memo and pinned run
ID verification. A missing/foreign run or lost history holds for review. The
first-start retention window stored in PostgreSQL must be shorter than the
namespace's guaranteed history retention. Never use a bare task queue or a
workflow ID alone as proof of tenant authorization. `PostgresApprovalVerifier`
uses the runtime database role with enforced RLS and no direct native credentials.

## Disposable persistence and recovery gate

`deploy/temporal/compose.integration.yml` runs self-hosted Temporal Server
`1.29.1` with PostgreSQL `17.6`, a project-local bridge, persistent test
database volume and a loopback-only Frontend. `auto-setup` initializes schema
for this **disposable test only**. The UI and database ports are not published.
It has no egress isolation, TLS, mTLS, authorization, backup or high availability and must never
be used for workloads or production credentials.

With Python 3.12+ and `pip install -e '.[controlplane]'` in a disposable lab:

```sh
export TEMPORAL_TEST_DB_PASSWORD='replace-with-disposable-ci-secret'
docker compose -f deploy/temporal/compose.integration.yml up -d
python -m tests.provisioning.workflow.temporal_recovery_gate prepare --state /tmp/temporal-recovery.json
docker compose -f deploy/temporal/compose.integration.yml restart temporal
python -m tests.provisioning.workflow.temporal_recovery_gate recover --state /tmp/temporal-recovery.json
docker compose -f deploy/temporal/compose.integration.yml down -v
```

The first process starts a job without a worker. The server restarts while
PostgreSQL stays up. A second process rejects a duplicate start unless the
exact retained run binding matches, starts a new worker, receives the queued
task, checks one approval Activity, reads the pinned result and replays history.
The SDK local tests also cover a waiting approval Signal, timer expiry, scope
rejection and worker replacement. These checks do not exercise PostgreSQL
restore, actual versioned worker deployments or an offline image mirror.

## On-prem operational profile

The intended deployment is the official self-hosted Temporal Helm chart, with
a separately operated PostgreSQL default store and visibility store in the
same approved jurisdiction. A candidate chart/server tuple is chart `1.6.0`,
server `1.32.0`, Python SDK `1.33.0`; the integration fixture above exercises
server `1.29.1`, so validate the chosen tuple in an isolated environment before
adoption. Pin mirrored image digests and chart archive checksums for each
release. `deploy/temporal/values.onprem.example.yaml` is a renderable candidate
with private Frontend, external PostgreSQL stores, existing secrets and mTLS;
it requires site-specific DNS, certificate SANs, database trust roots and
namespace authorization before installation. The operator owns schema
migrations and rollback order. No embedded
auto-setup container or development server belongs in the on-prem deployment.

Required environment variables for the installed runtime:

| Variable | Purpose |
| --- | --- |
| `HOSTING_WORKFLOW_POSTGRES_DSN` | Non-superuser, non-BYPASSRLS product database connection; a read-only Activity role in the worker process, a tenant-scoped job writer role in dispatcher/projector processes |
| `HOSTING_TEMPORAL_ADDRESS`, `HOSTING_TEMPORAL_NAMESPACE`, `HOSTING_TEMPORAL_TASK_QUEUE` | Private Frontend address and a scoped namespace/queue |
| `HOSTING_TEMPORAL_CA`, `HOSTING_TEMPORAL_CLIENT_CERT`, `HOSTING_TEMPORAL_CLIENT_KEY`, `HOSTING_TEMPORAL_SERVER_NAME` | Verified mTLS for every production RPC |
| `HOSTING_TEMPORAL_START_RETENTION_SECONDS` | Outbox uncertainty window, strictly less than guaranteed namespace retention |
| `HOSTING_TEMPORAL_INSECURE_LOOPBACK_TEST=1` | Test-only exception; rejects all non-loopback addresses |

Start the installed runtime as separate supervised processes with distinct
database credentials. Provision one dispatcher/projector per authorized tenant
context. The worker's read-only role needs `SELECT` on scoped jobs, plans,
approvals and `EXECUTE` on the narrowly scoped `lock_job_scope` and
`lock_authority_scope` functions; the definer functions lock rows under FORCE
RLS without giving the worker arbitrary `UPDATE` rights. Grant the worker only
its Temporal task-queue access:

```sh
python -m provisioner.controlplane.workflow.runtime worker
python -m provisioner.controlplane.workflow.runtime dispatch --organization-id org-a --tenant-id tenant-a --dispatcher-id dispatch-a
python -m provisioner.controlplane.workflow.runtime project --organization-id org-a --tenant-id tenant-a
```

The network policy must allow the Frontend only from authorized API/dispatcher
and worker nodes, the server components only to their persistence stores, and
no unrestricted Internet egress. Configure internode and Frontend mTLS with
trusted certificate authorities, server name verification, client identity and
namespace-level authorization. Disable unauthenticated Web UI exposure. Use
an approved internal registry/mirror, verify images and dependencies, and test
installation with repository access blocked. Temporal history, visibility,
logs and backups remain inside the enclave. Back up both Temporal stores and
the product database with consistent recovery procedures; protect all copies
with retention, access control and encryption.

Before enabling native activities: demonstrate network partition, restore to
fresh persistence, worker version upgrade/rollback with stored histories,
restricted-network supply, task queue authorization, mTLS rotation, schema
upgrade, retention expiration, and independent run/intent reconciliation.
Approval expiry after a gate pass still requires fresh authority immediately
before any native effect. Until those gates and the Waves 2–4 platform drivers
exist, no workload provisioning or migration is enabled.

Sources: [Temporal self-hosted deployment](https://docs.temporal.io/self-hosted-guide/deployment),
[Temporal security](https://docs.temporal.io/self-hosted-guide/security),
[Temporal Helm chart](https://github.com/temporalio/helm-charts),
[Python SDK API](https://python.temporal.io/temporalio.client.Client.html).
