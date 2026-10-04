# Controlled HA and observation restore drills

The installed owners execute a reviewed control-database switchover or an
isolated archive restore. They do not issue HA acceptance or restart native
writers. Commissioned PostgreSQL/Patroni, retained Temporal histories,
independent evidence custody and separate operating reviewers are required.
The repository and loopback tests provide no site HA certificate.

## Writer interlock and role separation

Migration `0032_operating_instance_interlock.sql` creates an `UNCOMMISSIONED`
instance. Mutation grants and native intent claims require `ACTIVE`, a current
review window, the actual database OID and PostgreSQL system identifier.
`DISCOVER_READ` remains possible through its existing authenticated read owner;
it cannot select a mutation command. Session read-only defaults do not replace
this interlock.

The runtime receives `EXECUTE` on
`hosting_controlplane.lock_operating_instance()` and no interlock DML. The
schema owner must be able to execute `pg_catalog.pg_control_system()` so its
definer functions can compare actual cluster identity. Separate operating and
restore custodians also need that one observation permission. Keep runtime,
schema, operating, backup, restore and independent checkpoint identities
separate. The backup/observer role has cross-tenant `SELECT`, `NOSUPERUSER` and
`BYPASSRLS`, with no business-table DML. The operating custodian has the same
read access plus only interlock `UPDATE`; it gets no native credentials.

The active runtime checks original, fresh retained observer and handover
signatures in every command transaction. Dedicated observer and handover Vault
paths are selected by `HOSTING_NATIVE_OBSERVER_VAULT_TRUST_JSON` and
`HOSTING_OPERATING_HANDOVER_VAULT_TRUST_JSON`; they must differ from checkpoint,
minimum operating acceptance, pilot and release keys. Native scope conversion
also requires the separate B48 `conversion.handover.require_write_admission`.
Neither handover can waive the other, clear unknown native work or advance an
epoch belonging to the other owner.

The nine minimum B44–B46 prerequisites also require their original bytes, not
only references in an operating review. Each is a separately observer-signed
`hosting-selected-operating-prerequisite/1` bound to the selected scope, code,
exact observation window and ID. It points to the original
`hosting-independent-selected-operating-observation/1` measurements in the same
retained workspace. The admission gate fetches both artifacts and verifies
their digests, scope and current observer signature. Missing original facts
hold every new effect and continuation. Named local observation can inspect
those holds without receiving a native credential.

The scheduled monitor projects `OPERATING_INSTANCE_HELD` immediately for a
missing, drained, observation-only, review-due or wrong-database instance. Its
signal includes the actual retained generation and this runbook; the monitor
does not activate the instance or assert useful service readiness.

## Exact switchover selection

Prepare one protected `SwitchoverSpec` JSON record with the exact installed
commit/artifact, original instance/generation, Patroni scope and explicit leader
and candidate. Bind both verified HTTPS origins by SHA-256, and bind the source
observer, candidate observer and separate drain DSN selections using
`database_selection_digest`. That helper omits passwords from its digest input;
host, address, database, user and TLS selection remain exact. Include the complete
fixed writer unit set and finite RPO/observation-RTO budgets.

`deploy/operations/hosting-control-application-worker.service`,
`hosting-control-dispatch@.service` and `hosting-control-projector@.service` are
installable templates for the fixed unit names. Each deployed instance needs
its own protected environment file and commissioned service identity. Installing
a template is not commissioning a service. The stop owner accepts only these
unit families and a root-owned, digest-reviewed systemctl binary. It exposes no
start command, shell, arbitrary executable or unit override.

The operating owner retains a signed
`hosting-controlled-ha-drill-authority/1` `RECOVERY_DECISION`, subject to the
exact specification digest. It binds the tenant, two permitted steps, change
reference, at-most-two-hour window and original independent exclusion proof.
The two steps are `DRAIN_CONTROL_WRITERS` and `CONTROL_DB_SWITCHOVER`.
The observer's separate
`hosting-independent-old-primary-exclusion/1` proof binds the same specification,
writer-set digest, old-primary identity, restart containment, delayed-request
containment and actual original observation bytes. An inactive service alone
cannot establish persistent exclusion.

Configure the drill custodian through the protected operating environment:

| Selection | Environment inputs |
| --- | --- |
| Exact installed bytes | `HOSTING_APPLICATION_RUNTIME_CONFIG`, `HOSTING_APPLICATION_SOURCE_ROOT`; actual accepted wheel, installed tree and current interpreter are rehashed |
| Operating decision | `HOSTING_DRILL_ORGANIZATION_ID`, `HOSTING_DRILL_TENANT_ID`, `HOSTING_DRILL_DECISION_EVENT_KEY`, `HOSTING_DRILL_DECISION_SHA256` |
| Fixed Patroni endpoints | `HOSTING_PATRONI_LEADER_ORIGIN`, `HOSTING_PATRONI_CANDIDATE_ORIGIN`, `HOSTING_PATRONI_CA_FILE`, `HOSTING_PATRONI_CLIENT_CERT_FILE`, `HOSTING_PATRONI_CLIENT_KEY_FILE` |
| PostgreSQL observers/drain | `HOSTING_DRILL_SOURCE_OBSERVER_DSN`, `HOSTING_DRILL_CANDIDATE_OBSERVER_DSN`, `HOSTING_DRILL_CUSTODIAN_DSN` |
| Reviewed service binary | `HOSTING_SYSTEMCTL_PATH`, `HOSTING_SYSTEMCTL_SHA256` |
| Read-only Temporal custody | `HOSTING_DRILL_TEMPORAL_TARGET`, `HOSTING_DRILL_TEMPORAL_NAMESPACE`, `HOSTING_DRILL_TEMPORAL_TASK_QUEUE`, `HOSTING_DRILL_TEMPORAL_CA_FILE`, `HOSTING_DRILL_TEMPORAL_CERT_FILE`, `HOSTING_DRILL_TEMPORAL_KEY_FILE`, `HOSTING_DRILL_TEMPORAL_SERVER_NAME` |

Run only after these actual selections and original proofs exist:

```bash
python -m provisioner.controlplane.operations.drills switchover --specification /etc/hosting/operations/approved-ha-drill.json --directory /var/lib/hosting-operations/drill-unique-attempt
```

Use the sealed installation's Python executable for these commands. The fixed
installation owner reads the protected runtime configuration and verifies the
accepted application wheel, source closure, installed file modes and current
interpreter before each drain or native command. An environment commit or
artifact digest cannot substitute for those installed bytes. Restore and
instance handover commands use the same protected configuration and source root.

The runner verifies healthy roles/leader locks, common system identity and
timeline before draining the actual instance row and stopping services. It
captures retained business state and original accepted Temporal run/memo/history
heads. It writes an fsynced attempt before its one explicit-candidate
`POST /switchover`. It then reads both named nodes, the new timeline/history and
the recovered database/history prefix. Returned member URLs are never followed.
HTTP 202 is an accepted request, not completed recovery.

If the response is lost, the original attempt remains
`SWITCHOVER_UNKNOWN_RECONCILE_NO_REPLAY`; inspect the two commissioned endpoints
under read authority and retain independent resolution. Existing attempt
directories cannot be reused. A second fresh directory cannot restore the old
`ACTIVE` generation or authorize another promotion. The runner never calls
Patroni forced failover, reset/reinitialize, arbitrary configuration, Temporal
start/reset or writer restart.

Observation readiness uses the actual monotonic elapsed clock. Retained
high-water loss uses actual source/recovered audit event times, with the exact
captured inventory and original Temporal prefixes compared. A missing clock is
unmeasured. Full service RPO/RTO stays null until actual useful service probes,
independent high-water reconciliation and owner acceptance exist. An idle
standby's last replay timestamp is not treated as zero RPO.

## Restore and handover

Backup and restore require reviewed absolute PostgreSQL binaries:
`HOSTING_PG_DUMP_PATH`/`HOSTING_PG_DUMP_SHA256` and
`HOSTING_PG_RESTORE_PATH`/`HOSTING_PG_RESTORE_SHA256`. Only root-owned, unwritable
installed pg_dump/pg_restore paths are accepted. The child environment is cleared
to fixed locale/PATH and the exact libpq password, which never enters arguments.
There is no unreviewed PATH fallback.

Prepare an empty database named `hosting_observation_restore_<unique>` with
CONNECT revoked from other identities and a separate NOSUPERUSER/NOBYPASSRLS
restore owner. Select `HOSTING_RESTORE_DSN` with verify-full TLS and pin
`HOSTING_RESTORE_MANIFEST_SHA256` from independent retained custody before SQL
execution. Run:

```bash
python -m provisioner.controlplane.operations.drills restore --archive /var/lib/hosting-control-backup/exact-archive --directory /var/lib/hosting-operations/restore-unique-attempt
```

The restore compares every original table/hash/count, migration digest, RLS flag
and sequence, including the archived instance row. It then rotates only the
restored control-instance identity and marks `OBSERVATION_ONLY`, clearing active
acceptance. Runtime ACLs are not restored. Native ownership epochs remain the
B48 owner's responsibility. Overriding a session read-only default cannot
authorize a mutation grant or claim while the interlock is held.

Inspect the new instance with
`python -m provisioner.controlplane.operations.instance inspect` under
`HOSTING_OPERATING_CUSTODIAN_DSN`. The independent observer retains original
proofs for every `HANDOVER_CHECKS` item: control DB state, original Temporal runs,
independent high-water, old-primary exclusion, native epoch reconciliation,
restored-writer negatives and useful service recovery. Each signed check points
to its exact retained observed bytes with a nonempty `measurements` object;
binding metadata alone cannot supply the underlying facts. The signed report binds the new instance,
proposed next generation, actual OID/system identifier, installed bytes and
`state_digest`. This digest covers business state; evidence/audit high-water has
its own original proof because a signature cannot include its future evidence
row. A different operating owner signs the exact report digest and review window.

```bash
python -m provisioner.controlplane.operations.instance accept-handover --report-event-key exact-observer-report --report-sha256 ACTUAL_REPORT_SHA256 --handover-event-key exact-operating-handover --handover-sha256 ACTUAL_HANDOVER_SHA256
```

This path rehashes current drained business state in a serializable transaction
and refuses unresolved intents, containment, unknown original starts, missing
original bytes, stale proofs and changed identities. It does not restart a
service. Actual writer startup remains an operating change after both instance
and scoped conversion handovers, credential reenrollment and current action
qualification. Local tests and signed run-sheet templates cannot accept any of
these gates.

## API basis

The fixed implementation uses the documented [Patroni REST
API](https://patroni.readthedocs.io/en/latest/rest_api.html), PostgreSQL
[recovery functions](https://www.postgresql.org/docs/16/functions-admin.html),
[control-file identity](https://www.postgresql.org/docs/16/functions-info.html)
and the Temporal Python SDK's pinned-run
[history reader](https://python.temporal.io/temporalio.client.WorkflowHandle.html).
Forced failover is a separately authorized future procedure, not this healthy
switchover drill.
