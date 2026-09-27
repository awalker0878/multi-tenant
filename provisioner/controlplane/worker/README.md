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
