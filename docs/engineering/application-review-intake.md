# Custodian intake of a signed application-owner decision

Reviewed 1 October 2026; B17/B20 continuation from
`4123efd543832bb9cff3087227f87165d90305d5` under the
[existing execution plan](../product/enterprise-workload-mobility-execution-plan.md).
The installed `hosting-application-review-ingest` command connects the already
signed owner artifact to the existing assessment repository and emits a local
receipt after commit. It is not an owner signer, HTTP upload service, background
queue, enrollment issuer, native operation or migration approval.

## Separate owner, custodian and reader

The owner uses [prepare/inspect/sign](application-owner-signing.md) on a separately
administered workstation. The resulting canonical `evidence`/`signatures` artifact
is transferred through an approved channel to the intake custodian. The custodian
must independently obtain its SHA-256 identity, corresponding to the signer's
`outputDigest`, not merely hash arbitrary received content and assume it was approved.
Automated owner-to-custodian transfer, enterprise identity onboarding and delivery
acknowledgement back to the owner remain integration obligations.

The new command consumes only APPLICATION_REVIEW evidence with one owner signature.
It checks the full submission digest, canonical bytes, closed fields and configured
environment/seven-field scope. The existing trust store verifies the owner signature,
enrollment, validity, revocation and protected policy revision floor before the command
reads a database password or opens a database connection. An INSTALLATION, ROUTE or
CONTROL envelope cannot be submitted through this command.

```sh
hosting-application-review-ingest \
  --config /srv/review-intake/config.json \
  --submission-file /srv/review-intake/received/signed.json \
  --submission-digest "$REVIEW_SUBMISSION_DIGEST" \
  --receipt /srv/review-intake/receipts/review-001.json
```

Paths and IDs are illustrative. Use the installed `controlplane` extra, the protected
custodian account, and independently supplied configuration. Inputs/output parents must
already exist with private permissions. Receipt names must be new. There are no scope,
DSN, role, password, signing-key or transport-weakening command-line switches.

## Protected configuration

The JSON object has exactly these top-level keys. Unknown fields are rejected:

| Field | Contract |
|---|---|
| `format` | `hosting-application-review-ingest/1`. |
| `environmentId` | One admitted environment ID; not derived from the incoming artifact. |
| `scope` | Exact `organizationId`, `tenantId`, `locationId`, `securityDomainId`, `endpointId`, `nativeScopeId`, `platformFamily`. |
| `database` | Exactly `host`, `hostaddr`, `port`, `name`, `role`, `passwordFile`, `caFile`, `crlFile`. |
| `trust` | Exactly `policyFile`, `rootKey`, `minimumRevision`, using the existing root-signed assessment enrollment policy. |

`host` is one certificate-verified DNS name; `hostaddr` is one canonical literal IP,
not a list, URL or unspecified/multicast address. The port is an integer from 1 to
65535. Database name and role use lowercase unquoted PostgreSQL-style identifiers.
The password file holds 1–4,096 printable non-whitespace ASCII bytes, with no newline.
CA and CRL files are explicit and bounded. The root public key is Base64 raw Ed25519,
not the owner's private key. The policy floor is a positive signed-64-bit integer.

All paths use the shared `review_files` owner: exact absolute POSIX paths, no symlink
ancestors/final files, private final directories and private single-link regular
inputs. Root-owned sticky intermediate directories remain allowed. The signer uses
this same implementation; its former local file helpers are deleted, not forwarded.
Input bounds are 70 KiB for the signed submission, 64 KiB for configuration, 1 MiB
for each policy/CA/CRL file and 4 KiB for the password. Duplicate/non-finite JSON and
changed input bytes are refused. This is not protection against a compromised
custodian/root account or proof that externally provisioned policy is the newest one.

## Authenticated database transport and existing writer

The production connector requires libpq 17 or newer and explicitly supplies the one
host/address/database/login. It selects TLS `verify-full`, the supplied CA/CRL,
TLS 1.2 minimum, SCRAM-SHA-256 with required channel binding, and a five-second
connection timeout. GSS-encrypted fallback and implicit TLS client certificates are
disabled; passwords are not taken from a passfile. Ambient `PG*` environment variables
and inherited TLS key logging are rejected, not silently applied or removed. No older
client, weaker TLS, alternative host or authentication fallback is attempted.

The actual current and session SQL users must both equal the configured dedicated
login. Superuser, RLS bypass, role/database creation, replication, other role membership,
site-worker status and database/schema creation privileges are rejected. Table and
column mutation checks reject UPDATE/DELETE/TRUNCATE/TRIGGER/REFERENCES and unrelated
INSERT privileges. Required existing SELECT access covers assessment inputs, environment
registrations, draft revisions, discovery generations and observations; required INSERT
access covers only assessment inputs and audit events. All six relevant tables must
retain enabled, forced tenant RLS. This is a startup/session guard, not an exhaustive
review of SECURITY DEFINER functions, filesystem privileges or a compromised DBA.

No grants or migrations are applied by this command. Do not give API/operator or owner
workstation identities the custodian database credential. Existing audit sequence and
trigger dependencies must remain configured through the established deployment process.
The selected connection imposes ten-second statement and five-second lock timeouts;
these are not a hard whole-process or filesystem deadline.

`AssessmentInputRepository.ingest` remains the sole evidence writer. It verifies the
actual retained immutable draft, source currency, owner/editor separation, evidence
stream, original signature and live trust under the existing source/evidence locks.
The wrapper rechecks frozen configuration/submission/password/CA/CRL bytes and current
signed policy before connection, after login checks, and inside the same transaction
immediately before commit. It does not turn exported checksums or receipt JSON into
native ownership, independent dependencies or accepted migration authority.

## Receipt and uncertain outcomes

Only a successful return from the committed repository context can produce
`hosting-application-review-receipt/1` with `RECORDED_ASSESSMENT_ONLY`. The receipt
contains exact scope, application/draft identity, evidence and submission digests,
decision and local `acknowledgedAt`. This is a local unsigned ingestion receipt,
not an owner signature, current review status, database persisted-at timestamp,
delivery proof to a remote owner or proof of a newly inserted rather than retried row.
The existing API [review read](application-owner-review.md) remains the authority for
newly evaluated review status; immutable drafts still remain UNREVIEWED.

Receipt publication is create-only, private and fsynced through the shared file owner.
No existing final name is overwritten. Receipt expiry is not substituted for signed
evidence expiry: a receipt can document a confirmed commit even if the owner evidence
expires immediately afterward. It never refreshes that decision. The three dependency,
ownership and execution flags remain false.

| Exit / result | Meaning |
|---|---|
| 0 / `RECORDED_ASSESSMENT_ONLY` | Committed ingestion was acknowledged and the local receipt was published. |
| 2 / `REVIEW_INTAKE_HELD` | The evidence-ingest operation was not entered. Database login/preflight reads may have occurred. |
| 3 / `REVIEW_INTAKE_UNKNOWN` | Ingestion was entered but the complete acknowledgement/receipt path failed. `recorded: true` means commit was confirmed before a later failure; false means commit is not confirmed, not proof of rollback. |
| 130 / `REVIEW_INTAKE_INTERRUPTED` | Preserve the reported attempt/recorded flags and any receipt; interruption does not establish rollback. |

Errors omit raw paths, SQL, driver messages, content and credentials and conservatively
report `outputMayExist: true`. No automatic retry, deletion, new evidence revision or
compensating write occurs. Inspect the exact server review and original artifact first.
An explicitly chosen same-artifact retry with a new receipt path uses existing repository
idempotency while its evidence is still current. Expired/revoked/superseded evidence can
remain unretryable; resolve retained custody through the established operator process,
not a locally minted replacement decision. Receipt files are not a durable delivery queue.

## Verification and remaining work

Tests cover real ephemeral owner signatures, strict scope/artifact checks, SQL login
responses, transport parameters, input rotation, precommit revocation, commit loss,
postcommit receipt failure, expiry, private files and no automatic retries. Transaction
doubles test wrapper behavior, not PostgreSQL. Six separate integration cases use the
actual repository/login guard, isolated SQL roles, real owner prepare/sign, authenticated
API review, exact retry, superseded drafts, commit-ack loss and a column-only grant.
Those integration tests replace only the network connector with disposable CI DSNs;
they do not qualify the production TLS/SCRAM/CRL deployment. Missing roles are explicit
skips. Installed-package validation resolves the actual command outside the checkout.

This completes installed custodian file intake, not a public upload or full enterprise
delivery service. B17/B20 retain owner-to-custodian transfer, actual owner/key onboarding,
independently verified dependencies, production transport/custody qualification and
administrator acceptance. B05, remaining Wave 2 and Waves 3–6 remain open. No installed
vendor system or production dataset was contacted during development.

## Primary references

Consulted 1 October 2026. [PostgreSQL 17 TLS](https://www.postgresql.org/docs/17/libpq-ssl.html),
[connection options](https://www.postgresql.org/docs/17/libpq-connect.html) and
[environment defaults](https://www.postgresql.org/docs/17/libpq-envars.html) define the
selected transport contract. [Psycopg transactions](https://www.psycopg.org/psycopg3/docs/basic/transactions.html)
describe commit/rollback at connection-context exit;
[parameter binding](https://www.psycopg.org/psycopg3/docs/basic/params.html) distinguishes
placeholders from literal percent characters. These sources establish API semantics,
not qualification of the installed database or the repository's pinned dependency set.
