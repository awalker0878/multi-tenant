# Discovery fleet admission and on-call receipt owners

This increment implements the remaining selected Wave 2 service paths from
[the execution plan](../product/enterprise-workload-mobility-execution-plan.md).
It provides PostgreSQL coordination for cooperating discovery hosts, exact
installed service facts, and a real HTTPS alert receiver. It does not record a
commissioned deployment, native estate scale acceptance, or migration eligibility.

## Fleet admission

`hosting-discovery-collect batch-run --fleet-config FILE` uses the existing
signed campaign, native credential issuer, current credential witness, native
HTTPS transport, batch journal and original outbox. Every native GET enters the
new owner after campaign verification and before opening its socket. Current
credential authority is checked again before the actual GET. Fleet admission
does not grant collection or native write authority.

Migration `0028_discovery_fleet_budget.sql` owns fleet policy, finite limits,
worker enrollment, exact scope enrollment, original starts and observed closes.
One fleet row lock serializes all five admission dimensions in one transaction:

| Dimension | Shared identity |
|---|---|
| Total | One explicitly enrolled fleet |
| Organization | Organization ID |
| Tenant | Organization and tenant IDs |
| WSD | Organization, tenant, site and workload security domain IDs |
| Endpoint | Organization, site, platform family and endpoint IDs |

Different native scopes or tenants using the same endpoint consume the same
endpoint bucket. `bucket_ids(scope)` derives the five SHA-256 identities; SQL
independently derives and checks the same identities. Each bucket has a
concurrency ceiling, minimum interval between starts, and lifetime start ceiling.
SQL counts all original starts and every unclosed lease, including elapsed leases.
Local batch limits remain an additional ceiling.

A committed start precedes the native socket. Only that exact current worker,
service manifest, process instance, lease ID and request digest can record its
observed local close. The transport returns capacity after all its local socket
and buffer close calls succeed. A failed close, killed process, lost database
acknowledgement, elapsed deadline or disconnected worker leaves occupied capacity.
There is no expiry refund, lease replay, lifetime-start refund or deadline reset.
Inspect reports `READ_OUTCOME_UNKNOWN` or `EXPIRED_OUTCOME_UNKNOWN` accordingly.

The SECURITY DEFINER functions have a fixed search path, no PUBLIC execution,
and current exact SQL login/enrollment checks. All tables force RLS and expose
rows only to their table owner. Collectors cannot read cross-tenant counts or
modify tables. Functions return the caller's own admission receipts or at most
128 of its own lease outcomes. Unknown outcomes are retained; this display limit
does not remove them from SQL admission counts.

Commissioning uses a separate database owner. Create a finite fleet, all derived
limit rows, an enabled worker with its exact login role and externally reviewed
service manifest digest, and the exact organization/tenant/site/WSD/endpoint/
native-scope/environment/collector enrollment rows. Bind the commissioned policy
digest in the protected worker configuration. Missing dimensions or inconsistent
derived buckets refuse collection. Policy, limits, scopes and enrollment identity
are immutable; enrollment can be disabled. Recommissioning cannot infer that an
old fleet's outstanding sockets are excluded.

The worker SQL login must have no elevated role flags, other role membership,
database/schema CREATE, direct table/column privileges, or fence capability.
Grant schema usage and only these functions:

```sql
GRANT USAGE ON SCHEMA hosting_controlplane TO selected_fleet_worker;
GRANT EXECUTE ON FUNCTION
  hosting_controlplane.discovery_fleet_admit(text,text,text,text,text),
  hosting_controlplane.discovery_fleet_close(text,text,text,text,text,text),
  hosting_controlplane.discovery_fleet_inspect(text,text,text)
TO selected_fleet_worker;
```

The login uses SCRAM with required channel binding, verified TLS, one DNS host,
one pinned host address, an explicit CA digest, and a protected DSN file. Inherited
PG settings, arbitrary DSN options, role aliases and inline credential factories
are refused. Connection, statement and lock waits remain bounded by the original
native read deadline. The DSN is never printed or included in discovery evidence.

`hosting-discovery-fleet inspect --config FILE` displays only the configured
worker's original outcomes. `hosting-discovery-fleet reconcile-fenced --config
RECEIVER --receipt PROOF` uses a separately enrolled receiver login with only
`discovery_fleet_fenced_close(text,text,text,text)` execution. Its protected
configuration pins the independent Ed25519 fence key and its actual service
manifest. SQL also pins that receiver's service digest and key digest.

The original signed proof must identify the exact old lease, worker, process,
service and request; independently observe both process exclusion and socket
closure; and be current. The receiver verifies the signature before SQL retains
the complete original envelope. Identical proof replay is idempotent; a different
close identity cannot replace the original. The command receives real host and
network fence evidence. It does not create a fence or substitute absence for
observed exclusion. No collector receives the independent receiver's capability.

## Installed service and store facts

`hosting-discovery-fleet service-facts --service-id SUBJECT --store NAME=PATH
--output FILE` captures the actual machine identity digest, UID, resolved Python
binary/digest/version, imported installed distribution/root/version/content
digest, and retained store paths/device/inode/owner/mode. It creates a protected
review artifact once; it issues no enrollment.

The package digest includes its recorded files, actual bytecode and distribution
metadata. Unrecorded source, unsafe paths, source imports that differ from the
installed distribution, and changed manifests refuse admission. A separately
commissioned owner pins the actual manifest digest. The runtime rechecks host,
package, interpreter and selected retained store identities before effects.
Native campaigns still require their independent original issuer/witness.

Create private service-owned stores before capture. A fleet collector must enroll
`outbox` and, for durable batch execution, `batch-journal`. The monitor must enroll
`monitor-config` and use its exact configured SSO service subject. The alert
receiver must enroll `alert-inbox`. Capture with the installed interpreter and
service UID that will run the unit; disable bytecode writes before capture and
operation. Package/interpreter replacement or store relocation requires review
and fresh enrollment, rather than silently reusing an old manifest.

The deployment examples preserve explicit operating modes:

| Example | Operating owner |
|---|---|
| `hosting-discovery-collect@.service` | Existing one-host POSIX endpoint budget |
| `hosting-discovery-fleet-collect@.service` and timer | Enrolled multi-host PostgreSQL fleet budget |
| `hosting-discovery-monitor@.service` and timer | Existing isolated monitor SQL role and current SERVICE IAM |
| `hosting-discovery-alert-owner@.service` | Separate HTTPS alert receiver and retained inbox |

Both collector modes keep original-only outbox publication. Selecting both budget
owners is refused. No configuration silently upgrades a single-host budget into
fleet coordination. Example JSON files contain placeholders and are intentionally
uncommissioned until real identity, PKI, enrollment and owner settings are supplied.

## Alert delivery, ownership and acknowledgement

The installed `hosting-discovery-alert-owner --config FILE` server binds the
selected IP/port with its actual TLS certificate. It authenticates real OIDC JWTs
and rechecks the existing current PostgreSQL role directory. Configure
`HOSTING_OIDC_ISSUER`, `HOSTING_OIDC_JWKS_URI`, the distinct
`HOSTING_ALERT_OWNER_AUDIENCE`, and a protected verified-TLS
`HOSTING_DIRECTORY_DSN`. No factory or request claim constructs an identity.

An independent Ed25519 authority signs a finite, current
`hosting-discovery-alert-ownership/1` policy. Each exact environment/native scope
selects one monitor SERVICE subject and one on-call HUMAN subject. Policy revision,
assignment ID, owner, validity and scope are signed. That authority key must differ
from the receiver's receipt-signing key. Keep scoped policies small enough for the
8 KiB signed receipt bound. The receiver retains original policies in its enrolled
inbox and rejects revision rollback or same-revision equivocation after restart.

The receiver exposes three bounded routes:

| Request | Current authority and retained result |
|---|---|
| `POST /v1/discovery/alerts` | Assigned SERVICE, exact `DISCOVERY_MONITOR` scope, original idempotency key; fsynced original alert intent |
| `GET /v1/discovery/alerts/{alertId}/receipt` | Same current monitor; fresh signed receipt for that original intent |
| `POST /v1/discovery/alerts/{alertId}/acknowledge` | Assigned HUMAN, current session and exact tenant; fsynced original acknowledgement |

Acknowledgement JSON contains exactly `alertId`, `alertDigest` and
`checkRecordDigest`. The caller cannot select a substitute intent, actor or role.
The receiver uses one bounded private inbox transaction, immutable originals,
socket/header/body deadlines and a connection ceiling. Duplicate delivery returns
the original accepted time. Lost responses do not create another acceptance or
acknowledgement. A new on-call assignment cannot relabel an old acknowledgement.

`hosting-discovery-alert-owner-receipt/2` carries the full independent signed
ownership policy, its digest, assignment ID, on-call subject and delivering
monitor. The monitor verifies both signatures and exact current ownership before
recording accepted/acknowledged state in the existing alert delivery ledger.
Production monitor composition now requires the actual service manifest and
independent ownership key/revision floor. Retained v1 receipts remain v1 and
cannot satisfy that commissioned v2 owner path. Notification receipts do not
authorize collection, workload mutation, cutover or release qualification.

## Additional selected API observations

Current collection requires fresh authorization for these new collector IDs;
old signed campaign IDs cannot select their stronger profiles. Historical
observations retain their original IDs and values. The normalizer revision is
`hosting-assessment-normalizer/3`; omitted new facts remain UNKNOWN, including
when an older raw generation is normalized today.

| Profile | Newly retained facts from the selected authenticated API |
|---|---|
| `vcenter-rest-vm-info-8.0.3.0-visible-only-3` | SCSI/SATA/NVMe controller native IDs, buses and returned models/PCI slots; returned SCSI bus sharing; configured boot device sequence; hardware version, instant-clone freeze and CPU/memory hot-add flags |
| `nutanix-ahv-v4.0-hardware-3` | CPU threads and NUMA nodes; CPU passthrough, hard pinning, CPU hot-add, memory overcommit and agent VM flags; returned machine type, BIOS UUID and generation UUID |
| `openstack-project-https-5` | Returned server lock, VM/task/power state and availability zone at the existing selected Nova microversion |

[Broadcom's selected VM information API](https://developer.broadcom.com/xapis/vsphere-automation-api/latest/api/vcenter/vm/vm/get/)
defines the controller maps and configured boot device sequence. An explicitly
empty sequence represents the server's default boot choice; it does not identify
a physical boot disk. Missing controller fields or boot selectors are not inferred.

[The Nutanix v4.0 VM model](https://developers.nutanix.com/api/v1/sdk/namespaces/main/vmm/versions/v4.0/languages/python/ntnx_vmm_py_client.models.vmm.v4.ahv.config.Vm.html)
defines the additional configuration flags and UUID fields. CPU passthrough is
distinct from device passthrough. These observations do not establish architecture,
disk encryption, shared-disk absence or migration method support.

[The Nova compute API](https://docs.openstack.org/api-ref/compute/) defines the
selected detailed server states and notes that down-cell responses can omit
fields. Absent fields remain UNKNOWN. A returned lock/power/task state is inventory
evidence, not persistent writer exclusion or a source fencing receipt.

Generation, native identity, retained raw/result digest, signed campaign/profile
binding and original native issuer/witness remain the attribution chain. A value
is KNOWN only when the authenticated retained response contains a valid typed
value. Encryption, TPM, passthrough, boot and sharing distinctions stay separate.

## Validation and remaining external evidence

Local tests cover actual signed native TLS GETs through fleet permits, transport
close failure, committed/lost SQL-protocol receipts, exact stores/package bytes,
real JWT/signature/HTTPS alert delivery, revoked identities, current on-call human
acknowledgements, durable ownership rollback refusal and immutable inbox originals.
Isolated PostgreSQL tests exercise actual cross-tenant admission, all five limit
dimensions, concurrent hosts, forced RLS/privileges, expired unknown leases,
immutable close receipts, rates, lifetime ceilings and receiver role separation.
SQL-protocol fixtures and loopback TLS are software evidence only.

External commissioning still requires installed service manifests on actual
hosts, current native issuers/enrollments, PostgreSQL login/CA/policy owners,
independent fence authority, real OIDC/JWKS/role-directory service enrollment,
receiver TLS and receipt keys, independent on-call assignment authority and an
observed on-call acknowledgement. Database HA/failover and backup/restore,
multi-host interruption campaigns, live endpoint budgets, retained-state recovery
and the required large-estate campaigns remain separate evidence gates. No local
fixture certifies native fleet size, complete hidden inventory, VMware-to-OpenStack
migration, database/live VM movement or release acceptance.
