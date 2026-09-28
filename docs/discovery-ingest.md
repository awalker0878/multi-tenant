# Authenticated discovery ingestion

`hosting-discovery-ingest` runs a separate collector-only mTLS service. The user
API cannot publish inventory. This process accepts independently signed campaigns
and collector results, checks a fresh independently signed native credential
witness, and retains original signed input before a database write can commit.
It grants no ownership, migration, platform mutation or production activation.

## Trust and deployment inputs

Provision these independently before starting the service:

1. A dedicated PostgreSQL login with forced tenant RLS and no superuser, bypass,
   role-management, database-creation, replication or other role membership.
   Grant `USAGE` on `hosting_controlplane`, `SELECT, INSERT` on
   `discovery_campaigns`, `discovery_generations`, `discovery_observations`,
   `discovery_absence_candidates` and `audit_events`, and `SELECT` on
   `environment_registrations`. Existing audit/RLS helper-function permissions
   must also match the persistence migration deployment instructions. Do not
   grant `UPDATE`, `DELETE`, `TRUNCATE`, `TRIGGER`, `REFERENCES`, unrelated table
   inserts, or schema/database creation. A site-worker login is forbidden.
2. A server certificate/private key, approved client CA bundle and current CRLs.
   Clients must carry the existing worker URI SAN shape
   `spiffe://<trust-domain>/org/<org>/tenant/<tenant>/site/<site>/worker/<collector>`.
   The collector subject, organization, tenant and site must match the signed
   campaign. A completed TLS handshake on this process's pinned context is
   required. Forwarded certificates and authorization headers are rejected.
3. A signed discovery trust policy enrolling separate campaign-issuer and
   collector Ed25519 signing keys, each bound to an exact environment and full
   native scope. Its offline authority key is pinned in configuration. Each
   collector enrollment names its independently witnessed credential reference.
4. A native IAM/RBAC witness document signed by a **different** pinned authority
   key. The independent witness producer must actually observe credential state,
   exact native scope and read-only privileges, retain that native observation,
   and publish its immutable observation reference and evidence digest. A
   collector's assertion that its credential is read-only is insufficient.
5. An existing service-owned evidence directory with mode `0700`, on durable
   storage. Its path and parents must not contain symlinks. Keep it outside the
   ordinary API's access. Restrict the TLS key to owner-only access.

The service verifies SQL privileges and fresh trust/witness documents before
binding a specific management IP. Configure a TLS-verified PostgreSQL DSN with
`sslmode=verify-full`, `connect_timeout=5` and an absolute `sslrootcert` path.
The DSN username must equal the configured ingest role.

All variables below use the `HOSTING_DISCOVERY_` prefix:

| Suffix | Required value |
| --- | --- |
| `POSTGRES_DSN`, `POSTGRES_ROLE` | Dedicated verified connection and exact login |
| `BIND_IP`, `BIND_PORT` | Specific IP; nonzero management port |
| `TLS_CERT`, `TLS_KEY`, `TLS_CA`, `TLS_CRL` | Absolute PEM file paths |
| `TRUST_DOMAIN` | Approved SPIFFE trust domain |
| `TRUST_POLICY_FILE` | Absolute signed discovery enrollment document path |
| `TRUST_ROOT_KEY`, `TRUST_MIN_REVISION` | Base64 raw 32-byte Ed25519 public key; independent revision floor |
| `CREDENTIAL_WITNESS_FILE` | Absolute independently signed native witness document path |
| `CREDENTIAL_WITNESS_ROOT_KEY`, `CREDENTIAL_WITNESS_MIN_REVISION` | Different base64 raw public key; independent revision floor |
| `EVIDENCE_ROOT` | Existing private durable directory |
| `MAX_CONNECTIONS` | Optional, default 16, range 1–64 |

Run `hosting-discovery-ingest` or
`python -m provisioner.controlplane.discovery.runtime`. No private Ed25519
authority, campaign-issuer or collector signing key is loaded by the listener.

## Signed policy publication

`DiscoveryTrustPolicy.as_dict()` defines the exact enrollment document. Sign
`trust_policy_signing_bytes(policy)` with the offline discovery authority, then
atomically publish:

```python
document = {
    "policy": policy.as_dict(),
    "signature": base64.b64encode(
        offline_authority.sign(trust_policy_signing_bytes(policy))
    ).decode("ascii"),
}
```

Serialize this document as JSON in the independent signing workflow. The signing
key stays off the listener. Policy validity is at most 24 hours. Every call
reopens the protected regular file, verifies its signature and time, and rejects
revision rollback or changed content at the same revision. No stale fallback
exists. Remove an enrollment, set its `revoked_at`, or rotate it through a newly
signed increasing revision. The authority must use different keys for campaign
issuance and result signing.

The witness follows the same outer `policy`/`signature` structure using
`NativeCredentialWitnessPolicy.as_dict()` and
`credential_witness_signing_bytes(policy)`. Each witness contains:

- Exact credential reference, collector, environment and native scope.
- Independent native observation reference and SHA-256 policy/evidence digest.
- Observation time and actual credential expiration time.
- Explicit read-only state and optional revocation time.

Witness documents are valid for at most five minutes, and individual observations
must be less than five minutes old. Actual credential expiration is separate from
witness freshness and must cover the campaign. Missing, stale, future-dated,
revoked or write-capable observations deny admission. Publish updates immediately
when native roles or credentials change; the service sees them on the next call.
The bounded witness window is an observation freshness guarantee, not a direct
native IAM query on every HTTP request.

Revision high-water marks are also maintained in memory. Advance each independent
configured revision floor when deploying policy updates so restarts and restores
cannot accept an earlier still-valid signed policy. Retain the original signed
policies and referenced IAM observations in the independent witness/authority
system. On POSIX, SIGHUP reloads TLS CA/CRL/server material; old TLS contexts cease
to authenticate requests. Policy and witness files need no signal.

## Collector request contract

All calls require the actual enrolled collector mTLS peer, one
`Content-Type: application/json`, one `Content-Length`, and at most 1 MiB of UTF-8
JSON. Chunked/compressed requests, duplicate fields, nonfinite numbers and
unexpected document fields are rejected. Handshakes and requests share bounded
connection slots and a ten-second socket timeout.

`POST /v1/discovery/campaigns` accepts exactly:

```json
{
  "environmentId": "environment-01",
  "campaign": {},
  "campaignSignature": {"keyId": "issuer-key-01", "signature": "base64 signature"}
}
```

Populate `campaign` using `campaign_document(campaign)` from `discovery.ingest`.
The independent issuer signs `campaign_signing_bytes(campaign, environment_id)`.
The campaign binds approval reference, collector, full scope, allowed kinds,
time window and collection budgets. Registration also requires the environment's
existing immutable selector registration to match exactly.

`POST /v1/discovery/results` includes those same three fields plus:

```json
{
  "result": {},
  "resultSignature": {"keyId": "collector-key-01", "signature": "base64 signature"}
}
```

Populate `result` with `result_document(result)`. The collector signs
`result_signing_bytes(campaign, result, environment_id)`. The original signed
campaign is required again so live issuer authority can be revalidated. The
campaign must already be registered. The signed result binds its campaign,
environment, full native scope, captured time, completeness, object identities,
facts, errors and missing privileges. Build results with
`assemble_discovery_result` to enforce page-chain and per-page budgets; the
published aggregate alone is not proof of individual native page operations.

The repository uses the database clock to recheck campaign/result signatures,
live enrollment and the independent credential witness. Before inserting a
campaign or result it retains the **original request bytes**, including original
signatures, in a content-addressed create-only blob. A separate fsynced admission
record binds those bytes to the computed verification proof, actual mTLS peer
certificate digest and trusted check time. The database verification reference
names that admission record. Evidence failures abort the database operation.
A failed database transaction can leave an orphan admission record, which is
safe to retain and is not evidence that publication succeeded.

Responses expose only computed registration/publication status and immutable
digests/generation. The request cannot set verification or success flags.
Persistence controls retries and unique campaign/result publication. Error
responses omit database details, credentials and internal file paths.

## Verification and remaining qualification

Unit tests exercise real Ed25519 signatures and negative scope, time, revocation,
rollback and custody cases. Local TLS tests perform real mutual handshakes and
CRL validation with ephemeral certificates, use the concrete trust/witness
authorities, and verify original evidence before a fake repository records a
write. Runtime tests check configuration and SQL-role rejection paths.

These tests do not prove native platform privileges, production PKI operations,
PostgreSQL deployment privileges, independent evidence retention, or route
qualification. A protected local evidence directory alone is neither WORM nor
an independently anchored recovery guarantee. Native qualification must validate
the actual IAM/RBAC observation producer, collector credential restrictions,
database writer isolation, revocation publication latency, evidence export and
restore rollback floors on the deployed site before enabling a production route.
