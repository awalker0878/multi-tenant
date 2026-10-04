# Site worker identity and credential custody

The worker listener uses `MutualTlsWorkerVerifier.context` directly. Its
enterprise CA chain, current chain CRLs, server certificate/key and SPIFFE
trust domain are required at startup. Worker certificates are issued by the
organization's PKI with client authentication usage and one URI SAN:

`spiffe://workers.example/org/<org>/tenant/<tenant>/site/<site>/worker/<worker>`

Pass the accepted `ssl.SSLSocket` to `verify()`. An HTTP header, proxy supplied
certificate, raw DER, or serialized `VerifiedWorkerIdentity` is not a trusted
input. Put this listener in a site management zone and terminate worker TLS
here. `reload_trust()` replaces the context; swap the listener to the returned
context. Existing sessions from the prior context fail verification. Keep the
CRL bundle refreshed from the enterprise PKI and treat refresh failure as an
operational hold. Independently revoke an enrollment in PostgreSQL immediately
when a worker is compromised; the SQL lock checks revocation on every grant
and credential issue, including already established TLS sessions.

`PostgresWorkerEnrollment` accepts only a verified mTLS peer and a distinct
`EnrollmentAuthorizer` backed by the enterprise administrative approval
service. The authorizer returns a bounded `EnrollmentDecision` with a verified
actor and ticket reference, which the enrollment transaction writes to the
append-only tenant audit stream. Deploy it with a separate enrollment writer
credential. Its initial
`WorkerCapability` entries bind tenant, site, security domain, endpoint,
native scope, platform family, operation kind, and an opaque `vault:<role>`
reference. Certificate rotation retains the subject and capabilities, revokes
old certificate versions atomically and inserts the new version. Revoked
subjects cannot be revived. To change capability, revoke the worker and enroll
a newly approved subject. Never give an agent the enrollment database role.

The enrollment writer needs `USAGE` on the schema, `SELECT, INSERT, UPDATE` on
`worker_enrollments` and `worker_certificate_versions`, `INSERT` on
`worker_capabilities` and `audit_events`, and `USAGE` on the audit identity
sequence. It has no grant or job table DML. The runtime
grant role continues to call the `lock_worker_scope` security definer under
its normal tenant transaction and native operation lease. It cannot enroll or
rotate certificates.

`VaultDynamicCredentialIssuer` maps each opaque reference to one reviewed
dynamic `.../creds/<role>` endpoint and exact `PlanScope` and operation kind.
It uses a private Vault Agent token sink file and a pinned HTTPS CA bundle,
optionally with a Vault client certificate. Configure the Vault policy to
permit reads only at the named role paths and require response wrapping.
Configure each Vault dynamic role/backend to generate *operation limited*
platform credentials, with its own enforced lease no longer than the worker
grant. The issuer only returns a one-use wrapping token, checks its origin and
TTL, and rejects an unwrapped secret response. Wrapping token TTL and the
underlying native credential lease are separate: a short wrap alone does not
make a static platform password safe. `CredentialBroker.acquire()` invokes
this issuer only inside grant/approval/lease checks. No response token or
platform credential belongs in plans, URLs, logs, evidence or workflow history.

The Vault dynamic backend and platform role must be qualified separately for
VMware, AHV, and OpenStack. Some native APIs cannot issue a per-operation
credential with the required privilege and lifetime; that route remains held
until an enterprise Vault plugin or native short-lived identity meets this
contract. Revoke an already issued platform credential through Vault or the
platform when containing an incident. Native intent recording and
reconciliation remain mandatory before side effects; TLS and Vault alone do
not fence an already accepted platform operation.

## Worker listener

`create_site_worker_server()` is the composition root for a dedicated
management IP. It takes a PostgreSQL runtime connection factory, the pinned
`MutualTlsWorkerVerifier`, a real `VaultDynamicCredentialIssuer`, and an
explicit set of site read scopes. It wires `NativeLeaseAuthority` into
`PostgresWorkerGrants` and then into `CredentialBroker`. Run its returned
server with `serve_forever()` behind a site firewall. The listener itself
terminates worker TLS. It accepts only the actual verified TLS peer socket,
derives tenant and worker from the certificate, rejects forwarded identity
headers, and returns a one-use Vault wrapping token in a `Cache-Control:
no-store` JSON response. URLs and standard request logs contain no token.

The sole route is `POST /v1/worker/credentials`, with an exact JSON body of
`grantId`, `jobId`, `stepId`, `operationId`, `operationKind`, `scope`, `leaseKey`,
and `leaseEpoch`. The scope uses the same seven fields as the enterprise plan
(`organizationId`, `tenantId`, `locationId`, `securityDomainId`, `endpointId`,
`nativeScopeId`, `platformFamily`). Only `DISCOVER_READ` is admitted. The
workflow must already have a started job, current approvals, a B11 operation
lease registered against an existing B06 native owner, and a B10 read grant.
All are checked by PostgreSQL under locks before Vault is called. Broad
unenrolled inventory discovery is outside this route.

Any mutation kind receives `NATIVE_ROUTE_NOT_QUALIFIED` before credential
issuance. The listener exposes no B11 `claim_once`, native API action or
unreviewed intent endpoint. Qualified platform adapters must later bind the
canonical native request, operation intent and independent reconciliation
before enabling a mutation route. Until then the worker listener can only
hand off a tightly scoped read credential.

## Installed site service

Run `hosting-site-worker` under a dedicated service account in the site
management zone. A database administrator creates the NOLOGIN
`hosting_site_worker_roles` group before migration 0016, then creates a unique
LOGIN member for each organization, tenant and site. The migration owner binds
that login to exactly one scope in the immutable `site_worker_role_bindings`
table. Do not reuse one site login across sites. Its credential has **read-only**
grants: `SELECT` on `operation_jobs`, `worker_grants`, `enterprise_records`,
`audit_events`, `plan_approvals`, and `native_containment_holds`; `EXECUTE` on
`lock_job_scope`, `lock_authority_scope`, `lock_worker_scope`, and
`lock_native_worker_scope` (migrations 0014 and 0017), plus the 0016 binding
check. Restrictive RLS and the lock functions use `session_user` to enforce
the immutable scope even if a caller changes the tenant GUC or runs `SET ROLE`.
The listener checks the binding at startup, including absence of table write
and database/schema create grants.
Deploy on a PostgreSQL minor patched for CVE-2024-10976 (17.1 or newer in
the 17 series; CI uses 17.11). Before enabling each production login, test
its exact organization, tenant and site tuple against a live grant, a foreign
tenant and an unrelated site in the same tenant. The unrelated rows must stay
invisible even when the login sets a different `app.tenant_id`; the matching
read grant must remain usable. Recheck after changing role membership or
PostgreSQL versions. See the PostgreSQL security notice:
<https://www.postgresql.org/support/security/CVE-2024-10976/>.
The lock functions serialize authorization with revocation and owner changes
without giving the listener UPDATE on native ownership. Run migrations and
enrollment with different credentials outside this process.

The trusted runtime role also needs `EXECUTE` on `lock_native_worker_scope`
for B11 intent checks and `lock_native_credential_grant(text,text,text)`
(migration 0036) for original credential issuance/closure. Grant `SELECT, INSERT`
on the native credential custody tables without `UPDATE` or `DELETE` on those
tables or `worker_grants`. The scoped function requires authenticated tenant
settings and `READ COMMITTED`; the site listener receives no custody-lock grant.
It must remain a separate login. Configure all required
variables before starting the site service:

| Setting | Meaning |
|---|---|
| `HOSTING_SITE_POSTGRES_DSN`, `HOSTING_SITE_POSTGRES_ROLE` | Dedicated role and PostgreSQL URI with `sslmode=verify-full`, `connect_timeout=5`, and absolute `sslrootcert` path; URI user must match the role. |
| `HOSTING_SITE_ID`, `HOSTING_SITE_BIND_IP`, `HOSTING_SITE_BIND_PORT` | Exact site and management address; port 1–65535. Firewall access to enrolled workers. |
| `HOSTING_SITE_TLS_CERT`, `HOSTING_SITE_TLS_KEY`, `HOSTING_SITE_TLS_CA`, `HOSTING_SITE_TLS_CRL`, `HOSTING_SITE_TRUST_DOMAIN` | Listener certificate/key, approved worker CA and current CRLs, and worker SPIFFE domain. |
| `HOSTING_SITE_VAULT_URL`, `HOSTING_SITE_VAULT_CA`, `HOSTING_SITE_VAULT_TOKEN_FILE` | HTTPS Vault address, pinned CA, and private Vault Agent token file. |
| `HOSTING_SITE_VAULT_NAMESPACE`, `HOSTING_SITE_VAULT_CLIENT_CERT`, `HOSTING_SITE_VAULT_CLIENT_KEY` | Optional namespace and paired Vault client certificate/key. |
| `HOSTING_SITE_READ_ROUTES_JSON` | Nonempty exact read-route array. Duplicate fields, overlapping scopes, mutation kinds and unreviewed Vault references are rejected. |

Each route contains `scope` (the seven canonical plan scope fields),
`reference`, `apiPath`, and `maxCredentialTtlSeconds`. For example, a reviewed
route can map `vault:site-read` to `platform/creds/site-read` for one exact
`organizationId`, `tenantId`, `locationId`, `securityDomainId`, `endpointId`,
`nativeScopeId`, and `platformFamily`. The Vault role must independently
enforce that same read-only scope and no longer than the configured lease;
the service cannot infer those native privileges from the role name. Do not
place tokens or platform secrets in route JSON. Stop the service if CRL
refresh fails, and reload the verifier context after approved PKI rotation.
