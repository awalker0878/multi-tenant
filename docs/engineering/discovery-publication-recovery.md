# Signed discovery publication and restart recovery

Reviewed 29 September 2026. This implements portions of B10/B13/B14–B16/B22 in
the [existing B01–B50 execution plan](../product/enterprise-workload-mobility-execution-plan.md).
It describes actual package-owned collection/signing, local custody and mTLS sender
code, not another inventory writer, a new roadmap or an installed-site acceptance.

## Owners and composition

`provisioner/controlplane/discovery/publication.py` owns `DiscoverySubmission`,
`PrivateFileDiscoveryResultSigner`, `PrivateDiscoveryOutbox`, `collect_submission`
and `stage_submission`. `publication_https.py` owns `DiscoveryPublishTarget`,
`DiscoveryHttpsPublisher`, `DiscoveryPublishReceipt` and the unknown-delivery error.
They reuse the existing ingest wire contract, signed authority checks and filesystem
artifact implementation. Neither selects a platform or wraps another vendor client.

A trusted site composes an already-admitted campaign, its original issuer signature,
matching collector key, live verifier, actual native adapter collect method, private
tenant outbox and pinned ingest target. No endpoint, private path, verifier or native
credential is selected by an unauthenticated request. The separate
[installed collector command](discovery-collector-runtime.md) now supplies protected
configuration and explicit stage/publish actions over these owners. A deployed fleet
scheduler and credential/key custody are separate; native adapters remain read-only.

The supported sequence is `stage_submission(...)`, then one explicit
`DiscoveryHttpsPublisher(...).publish(submission)` attempt. Staging verifies current
campaign authority and either resumes the original campaign-bound submission or
collects, signs, retains and re-verifies a new one. Staging alone is not publication.
No automatic retry, deletion, campaign issuance or native write is performed.

## Original signature and wire custody

The signer loads a protected Ed25519 PKCS8 collector key; it does not generate keys,
re-sign campaign authority, or use the native API credential as a signing key.
Enrollment and independent native read-only witnesses are verified before signing
and after creation. Unknown facts, partial completeness and the original capture
time survive assembly. Object/fact sets are canonicalized; ordered device arrays
inside facts are preserved. An oversized aggregate is held before transmission.

`DiscoverySubmission` retains the original issuer signature, collector signature,
result digest and canonical ASCII request bytes. The existing ingest limit is
1 MiB. Deserialization refuses noncanonical/ambiguous JSON, extra keys, changed
digests and mismatched identities. Verification reparses actual bytes and checks
current signed authority; an object or file merely looking complete is insufficient.

The private outbox stores content-addressed payloads using the existing create-only
artifact writer. Payload fsync precedes publication of a separate create-only campaign
reference. The reference key hashes the campaign ID inside a hashed organization/
tenant namespace. Changing environment, endpoint or authorization under the same
campaign ID conflicts rather than selecting another index entry. User identifiers
are not used as filesystem path segments.

The bounded canonical reference contains exactly `format`, `environmentId`,
`authorizationDigest` and `requestDigest`; format is
`hosting-discovery-outbox-campaign/1`. `for_campaign(campaign, environment_id)`
resolves it back to the original signed bytes and verifies both identities. Only a
missing reference returns no result. A corrupt/noncanonical reference, missing
referenced payload, wrong tenant/scope, public file, symlink or FIFO holds recovery;
none is interpreted as permission to regenerate missing evidence.

Independent local instances may retain the same original concurrently. Different
submissions race to one create-only reference; the losing submission is held and
cannot replace the winner. The publisher's existing pre-POST retention call enforces
this boundary even when a caller bypasses the staging helper. This is local custody,
not fleet-wide exactly-once execution or a replacement for server campaign conflicts.

## mTLS delivery and acknowledgements

The publisher posts only to the existing `/v1/discovery/campaigns` and
`/v1/discovery/results` routes. It sends the original campaign registration first,
then the retained result body. The ingest repository remains the sole inventory
publication writer, with its existing tenant RLS, immutable originals, duplicate
request handling and changed-campaign/result conflicts.

The pinned target binds HTTPS origin, literal connection IP, exact CA/CRL/certificate
hashes and collector TLS identity. Client certificate/key matching, expiry, exact
SPIFFE organization/tenant/site/collector URI and certificate usage are checked.
TLS verifies the server name and revocation chain. Verified TLS files are privately
snapshotted before loading. Proxy and key-log environment variables, redirects,
cookies, plaintext reconnects and native-API POSTs are not used. Both HTTP phases
have bounded framing/JSON, acknowledgement size and total/socket deadlines.

The response must match the expected campaign/environment/result identity and
completeness, with a valid positive generation and `executionAuthorized: false`.
A task receipt or a successful TLS connection cannot replace that acknowledgement.
Current campaign/result authority is rechecked throughout delivery. Buffered readers
and sockets are closed on success and holds.

| Outcome | Required behavior |
|---|---|
| Storage, signature or connection fails before a request attempt | Hold; do not send a new request from that attempt. Original custody may still exist and is not proof of server commitment. |
| Any failure after an HTTP request may have been sent | Raise `DiscoveryPublicationUnknown` with the original request digest and `CAMPAIGN` or `RESULT` phase. Do not claim success, assume noncommitment or automatically retry. |
| Explicit authorized retry after a lost acknowledgement | Find the original by campaign, recheck live authority, and use a new publisher instance with the same retained bytes. Do not recollect, re-sign or move captured-at time. |
| Expired/revoked campaign or missing original evidence | Hold even if a server may already have committed. A separately authorized reconciliation process must resolve history; a new campaign cannot relabel old evidence. |
| Two collectors with independent outboxes submit competing results | The central repository still rejects the conflicting campaign result. Local reference protection does not weaken this server-side gate. |

## Crash, retention and upgrade boundaries

A crash after payload storage but before reference creation may leave an orphaned
payload. The new publisher cannot send until the reference is durable, so that
incomplete retention is not acknowledged staging. Orphans are preserved for review;
there is no automatic cleanup, directory scan or inference of native authority.

Outboxes created before the campaign-reference format require explicit reconciliation
by original request digest before this staging path is used for old campaigns. A
missing new-format reference cannot prove an old sender never attempted publication.
Do not rescan or mint a replacement signature to resolve an old unknown delivery.
Drain or hold pre-upgrade attempts and retain original bytes for reviewed replay.

Deleting a local reference or rolling back its entire filesystem is not independently
detectable here. Deployments still need protected persistent authority revision floors,
independent evidence retention/backup, restart/DR reconciliation and disk-capacity
controls. Concurrent first-time reads are not serialized by the reference; B22 must
supply campaign scheduling and endpoint budgets. Never present atomic local file
creation as WORM storage, an HA ledger or enterprise exactly-once processing.

## Verification and remaining wave work

Local tests cover actual signing, original-byte round trips, conflicts, corruption,
permissions, storage failures, concurrent instances, revocation and clock regression.
Real loopback mTLS tests lose campaign and result acknowledgements after the server
has processed the request, restart from the campaign identity and verify exact-byte
retry without native reads or signing. Dedicated PostgreSQL tests retain one inventory
generation after retry and exercise both local and independent-outbox server conflicts.
Installed-package checks require both actual owners without legacy import fallback.

Collector IDs, discovery wire formats, normalizer 2, profile resolution 3 and policy
capsule/realization 2 are unchanged. The new local reference is not a compatibility
wrapper, a native capability claim or an approval conversion. Newly collected facts
still require new digest-bound assessment reviews; partial inventory stays partial.

B10/B13/B14–B16/B22 remain partial. Installed command composition is implemented; signer custody,
credential issuance/renewal/revocation, Vault publication, durable anti-rollback and
independent retention, visibility/privilege-loss reconciliation, missing image/hardware
facts, B17 owner/dependency persistence, scheduling and estate qualification remain
open. Later provisioning, transfer, fencing, cutover and recovery are separate work.
No installed vendor, production guest or production dataset was contacted by these tests.
