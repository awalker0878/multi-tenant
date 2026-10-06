# Inventory discovery operations

Owner: Inventory operator and independent native site authority. This procedure
starts read-only collection; it grants no native write, ownership or reservation.
G04 still requires E3 evidence from the actual OpenStack and VMware installations.

## Independent inputs

Provide `INVENTORY_SITE_POLICIES_FILE` as an absolute read-only JSON mount in both
the service and the authorized worker. Its root is `{"version":1,"policies":[]}`.
Each approved policy includes these required fields:

| Fields | Meaning |
| --- | --- |
| `policy_id`, `tenant`, `site`, `owner`, `worker`, `epoch` | UUID4 identities. Owner must be a current federated Inventory administrator for the site. A new native identity/scope requires a new enrollment and epoch. |
| `worker_fingerprint` | SHA-256 of the separately issued worker workload token. Do not put the token in this manifest. |
| `platform`, `native_scope`, `authority` | `openstack`, `vmware` or `ahv`; approved project/datacenter; shared physical API budget identity. Policies on one origin share authority and rate/concurrency limits. |
| `installed` | Object with `product`, `api`, `backend`, `features`, `entitlements`, `configuration_reference`; explicit declarations, not a capability qualification. |
| `streams` | Required stream objects below; never a browser-supplied destination. |
| `freshness_seconds`, `requests_per_minute` | 60–3600 seconds, 1–600 requests per minute across the authority. |
| `concurrency`, `tenant_concurrency`, `max_pages` | 1–16 leases per authority, 1–4 per tenant across its policies, 1–100 pages per scan. Tenant limits must agree. |
| `expires_at`, `coverage_reference` | Unix expiry and independent evidence reference for the exact read identity and scope. Null coverage keeps results partial. |

Each stream requires `kind`, `base_url`, `addresses`, `ca_file`, `credential_file`
and `api_version`. The last two file references and CA are absolute mounted paths.
Addresses are independently approved literal IPs; hostname certificate verification
uses the HTTPS origin. DNS changes and redirects cannot expand that destination.
Changing policy bytes fences existing enrollment until an approved renewal.

| Platform | Required streams | Native API limits |
| --- | --- | --- |
| OpenStack | `server`, `network`, `volume` | Nova 2.1 `/servers/detail`; Neutron 2.0 `/networks`; Cinder 3.0 `/volumes/detail` with a project-scoped base path. Project IDs must match. `X-Auth-Token` comes from each stream's mounted secret. |
| VMware | `server`, `network`, `datastore` | `vcenter-api` and `/api/vcenter/{vm,network,datastore}` filtered to the approved datacenter. Mounted `vmware-api-session-id`. More than 100 objects in one list is an explicit partial result. |
| AHV | none | Profile dimensions and enrollment only; collector unavailable. |

Native tokens are supplied/rotated outside the collector. It never creates a login
session or requests a higher privilege. A permissions audit must establish list
visibility; a successful response alone cannot prove completeness. Do not attach
an old coverage reference to a different credential or installation. All eleven
capability dimensions remain UNASSESSED until a separate qualification provides
evidence. vCenter list records lack incarnation evidence and hold matching.

## Start and schedule

Apply `services/inventory/migrations/*.sql` in order as `inventory_owner`, through
the controlled migrator. The runtime role cannot migrate or rewrite immutable
page, receipt, audit, observation or event rows. Supply verified PostgreSQL TLS
and mounted DB credentials using the service README configuration.

The API needs `INVENTORY_CONSOLE_CREDENTIAL_FILE`, a distinct
`INVENTORY_GOVERNANCE_CREDENTIAL_FILE`, `GOVERNANCE_URL`, `GOVERNANCE_CA_FILE` and
the policy file. Governance requires `INVENTORY_GOVERNANCE_CREDENTIAL_FILE` and
the additive `012_inventory_delegation.sql` migration. Console uses
`INVENTORY_URL`, `INVENTORY_CA_FILE`, `CONSOLE_INVENTORY_CREDENTIAL_FILE` and its
existing independent Governance credential. No credential belongs in a URL.

Start `inventory-serve --host 0.0.0.0 --port 8080` behind verified service TLS.
Create a worker `INVENTORY_CONTROL_PLANE_FILE` containing `base_url`, approved
`addresses`, `ca_file` and `credential_file` for its Inventory workload credential.
Set the worker's policy file. Run `inventory-worker-collect --pages 1` on an
operated cadence (for example once per second). It exits when no lease is eligible;
the scheduler persists rate/backoff state. A supervisor may restart the command,
but must not invent new discovery requests when retrying a page.

From the tenant's Observed inventory workspace, open the approved site UUID,
enroll its policy and request discovery. Roles: administrators enroll/renew/revoke;
operators discover/match; authors match; readers/reviewers view. Policy owner and
current Governance access are checked independently on every dispatch/result.
Renewal and revocation use endpoint revisions and fence active jobs.

One endpoint may have one active scan; a tenant may queue 20; the service queues
at most 1000. A native page contains at most 100 records and 2 MiB, with 10-second
transport and 30-second lease bounds. Retries/disconnections stop after three
failures, and scans stop after one hour. The shared scheduler alternates eligible
tenants before returning to the same tenant. Returned pagination links are ignored.

## Failure and recovery

- Retry a command whose acknowledgement was lost with exactly its original key,
  body and endpoint revision. The Console preserves those fields on uncertainty.
- Stop or revoke an unsafe enrollment. Rotate the independent policy/credentials,
  approve renewal and request a new scan. Never edit observation history.
- Treat forbidden, incomplete, oversized, stale or unverified coverage as partial.
  A partial generation cannot replace the last complete one or prove absence.
- Resource disappearance needs two complete absent generations. Reused IDs,
  missing incarnation evidence, stale observations and conflicting application
  proposals hold matching. Proposals grant neither ownership nor capacity.
- Restart a worker without deleting jobs: persisted cursor and sequence resume;
  expired leases fence late results. Native calls are GET only.

## Confirmed fact delivery

Provision `deploy/dependencies/stateful/inventory-facts.json` through the broker
authority with separate Inventory producer and Planning consumer credentials.
Configure `INVENTORY_BROKER_HOST`, `INVENTORY_BROKER_PORT`,
`INVENTORY_BROKER_CA_FILE`, `INVENTORY_BROKER_PASSWORD_FILE`; run
`inventory-publish --limit 100` repeatedly. AMQPS, mandatory routing and publisher
confirms are required. The Planning consumer is P05 work; it must deduplicate
`event_id` and handle original ordered fact sequences. An uncertain publish keeps
the original event pending. Actor revocation does not erase a committed fact.

## G04 receiving evidence

Retain exact installed product/API versions, backend/feature/entitlement identity,
approved endpoint/tenant scope, restricted credential identity, permission audit,
test timestamps, source revision and independent before/after native observations.
Exercise read-only success, partial privilege, pagination/limits, revocation,
staleness, restart, throttle/fairness and independent proof of no native changes.
Redact credentials. Record the named site owner and independent receiving reviewer.
Synthetic HTTP, database, broker and browser campaigns are E2; they cannot supply
this E3 installation evidence or close G04.

Reference API contracts: [Nova pagination](https://docs.openstack.org/api-guide/compute/paginated_collections.html),
[vCenter VM list](https://developer.broadcom.com/xapis/vsphere-automation-api/latest/api/vcenter/vm/get/),
[vCenter network list](https://developer.broadcom.com/xapis/vsphere-automation-api/latest/api/vcenter/network/get/).
