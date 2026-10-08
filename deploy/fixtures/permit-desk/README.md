# Permit Desk synthetic application fixture

P01.02/P01.06, requirements R02/R29/R30/R31; owner: SRE/qualification engineering.
This is the representative workload being restored, not another hosting product
microservice. Its source and independent build context are
[`scripts/p01/permit_desk/`](../../../scripts/p01/permit_desk/). It imports no
control-plane service, historical implementation or disposable P00 spike.

The fixture is a small HTTPS JSON application with PostgreSQL records and a separate
attachment volume. It uses the already measured CPython 3.12.14/PostgreSQL 18.6
candidate image manifests and owns its three-package, hash-checked Python closure.
The campaign builds the application once, checks its source/image labels, and uses
that exact local image configuration ID in each new installation. It records actual
runtime versions and database-tool identities. This does not publish or sign an image.

## Complete reproducible inventory

| Item | Fixture definition |
| --- | --- |
| Application | Single HTTP writer, Linux/amd64, UID/GID 10001, read-only container root, dropped capabilities; no native adapters/endpoints |
| Tenants | `t_demo`, `t_other`; one writer each, plus a `t_demo` reader |
| Initial data | Each tenant receives `permit_one` and `permit_two` through HTTPS; title `Synthetic <permit_id>`; attachment UTF-8 bytes `Synthetic attachment for <tenant>/<permit_id>` followed by LF |
| Schema | Version 1; complete `app.fixture_schema`, `app.tenants`, `app.permits`, `app.attachments`; composite tenant/permit relationship and exact attachment key, digest, length |
| Configuration | [config.json](config.json), including exact principal-to-tenant/role mapping, private database endpoint and `native_writes: false` |
| Secret references | Runtime, migrator and backup database passwords; writer/reader tokens; disposable CA and server keys. Values are created outside source/evidence, never captured; each restored installation receives new credentials |
| Application state | Every schema/row, generated creation timestamp, attachment byte/size/mode, and nonsecret configuration; the runtime has no separate sessions, cache, queues, workers or external writers |
| Storage ownership | Private PostgreSQL volume plus attachment volume populated with UID/GID 10001 and mode 0700 from the immutable application image; files mode 0640 |
| Consistency group | Application database and attachment volume. Stop the sole application writer, disable its database login, terminate/check its sessions, reject a new login, then capture both stores and verify unchanged state |
| Recovery markers | `known_target_write` is accepted/read after initial restore; a second complete target capture restores into another new installation; `known_recovery_write` is accepted/read there |

Only loopback HTTPS is published. PostgreSQL has no published port and accepts TLS
connections only for the fixture's own runtime, migrator and backup roles. The runtime
has no schema-administration privileges or backup/migrator secret mounts. The backup
role is read-only. These are disposable fixture identities, not product OIDC or
enterprise secret custody. Network topology declarations alone do not establish a
full policy-denial campaign.

`GET /api/tenants/<tenant>/permits`, the corresponding permit and `/attachment`
resources, and `POST` to the collection use synthetic bearer credentials. The server
maps each token to its configured tenant/role; clients cannot assert that authority
in request data. Creation accepts only `permit_id`, `title`, `attachment_base64`.
An ordinary request cannot activate native operations. The implementation is single
writer; it is not a production web server or a concurrent crash-consistency protocol.
An ambiguous database commit preserves attachment bytes for reconciliation; incomplete
or orphaned state cannot pass capture admission.

## Execution and evidence

From a clean source checkout with Docker Engine/Compose and OpenSSL:

```sh
python3 -m unittest discover -s scripts/p01 -p test_permit_desk.py -v
python3 scripts/p01/run_permit_desk.py \
  --workspace /absolute/path/to/checkout \
  --source-revision FULL_40_CHARACTER_COMMIT \
  --output /absolute/path/to/absent-evidence-directory
```

The [CI campaign](../../../.github/workflows/p01-permit-desk-recovery.yml) uses the
same command. Source changes and workflow execution are separate from a passing
result; current observations belong in the [implementation record](../../../docs/implementation/p01-permit-desk-recovery.md).

The report retains source hashes, actual commands and raw output hashes, nonsecret
Compose inventories, exact image identity and both complete base64 capture envelopes.
The capture digest is retained outside its envelope in `report.json`. Admission checks
that digest, image/source/configuration identities, writer boundary, archive bytes,
complete file inventory, metadata and database/file relationships **before** creating
a restore destination. Independently rehashing a changed manifest does not bypass
these checks. This verifies integrity against the retained expected bytes; it does
not establish a backup signature or authorize restoration of untrusted archives.

Normal completion and handled failures collect bounded logs and remove only owned
Compose projects, volumes and private credentials. A cleanup failure fails the
campaign and preserves its private runtime path for remediation. Do not publish
that private directory. Backups contain synthetic data only, but the collector's
raw command output is not a general log-redaction system; inspect artifacts before
retaining them in the repository.
