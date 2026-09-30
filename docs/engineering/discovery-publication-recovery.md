# Signed discovery publication and restart recovery

Reviewed 30 September 2026. This implements portions of B10/B13/B14–B16/B22 in
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
claims its first collection before collecting, signing, retaining and re-verifying
a new one. Staging alone is not publication.
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

## Shared-outbox first-capture exclusion — B22 continuation

Before invoking a new collector, `stage_submission` now creates a private durable
`hosting-discovery-collection-intent/1` record beside the campaign reference. The
same hashed organization/tenant/campaign identity selects it, regardless of changed
environment or authorization. The record binds the environment, campaign digest,
issuer-signature digest, unique attempt and UTC claim time. It contains neither
native credentials nor an execution grant. The unchanged `_atomic_new` primitive
writes and fsyncs the record, links without replacing an existing destination, and
fsyncs its directory before collection may begin.

This closes a reproduced race: two callers could previously both enter native
collection before their signed results competed at reference creation. Now only
one caller sharing that outbox can acquire the first-capture intent. The loser
holds without invoking the collector; it does not wait or automatically retry.
Live signed campaign and credential-witness checks still run after acquisition.
The claim is checked before the collector callback and before retaining its signed
result. A changed or unreadable claim prevents new local result publication.

| Local state | Staging behavior |
|---|---|
| Original signed submission and exact campaign reference exist | Reverify and return the original, without another claim, native read or signature. Existing pre-intent originals retain this same behavior. |
| No original and no collection intent | Verify current authority, acquire the durable intent, then collect/sign/retain through the existing owners. |
| Intent exists but no complete original reference exists | Hold for reconciliation; it may describe in-flight work, an interrupted read, or failed signing/storage. |
| Corrupt intent, conflicting identity, unsafe file or storage failure | Hold without replacement or native collection. |

The intent is never deleted after success or failure and has no expiry or PID-based
takeover. A terminated process, cancelled command or elapsed schedule window does
not prove the previous native operation stopped. Even a failure before any read
can conservatively leave a held intent. The installed `stage` command returns its
existing HELD result; `batch-stage` records the held task and reconciliation flag.
No new public command or authority flag is added.

An incomplete intent must be reviewed with original outbox content, existing
campaign/result records and native observations. There is no new automated intent
reset, orphan promotion or adjudication service. Do not delete an intent or change
outbox roots to make a retry run. An independently verified original can use the
existing retained-byte recovery path, subject to current authority; a timestamp
or file name alone cannot establish such an original.

This protection applies to cooperating updated processes sharing one protected
local outbox. It does not coordinate separate roots, separate filesystems or arbitrary
callers of lower-level `collect_submission`. It is not a distributed endpoint rate
limit, a fleet dispatch database, a native fence or exactly-once processing. Batch
read-rate/concurrency reporting remains `THIS_PROCESS_ONLY`. Qualify filesystem
semantics before deployment; network-filesystem and multi-host behavior are not
established by these local tests. Deleting or rolling back custody can erase the
protection, so independent retention and recovery remain necessary.

During upgrade, drain or hold older collectors before permitting new first captures:
older code does not participate in intent acquisition. Preserve completed signed
originals and all unresolved artifacts; do not silently reinterpret an absent claim
as proof that old software never collected. The existing pre-reference recovery
requirements below remain in force.

The [Python 3.13 operating-system interface](https://docs.python.org/3.13/library/os.html)
documents `os.link` and flushing with `os.fsync`; that API reference is not evidence
that any particular storage deployment honors the required persistence guarantees.

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
controls. Updated staging serializes first capture through the separate local intent,
not the completed reference. B22 still must supply durable fleet scheduling and
globally coordinated endpoint budgets. Never present atomic local file
creation as WORM storage, an HA ledger or enterprise exactly-once processing.

## Verification and remaining wave work

Local tests cover actual signing, original-byte round trips, conflicts, corruption,
permissions, storage failures, concurrent instances, revocation and clock regression.
Real loopback mTLS tests lose campaign and result acknowledgements after the server
has processed the request, restart from the campaign identity and verify exact-byte
retry without native reads or signing. Dedicated PostgreSQL tests retain one inventory
generation after retry and exercise both local and independent-outbox server conflicts.
Installed-package checks require both actual owners without legacy import fallback.

The new `test_collection_claim.py` adds 23 methods, including separate-interpreter
capture races, abrupt exit, completed-original resume, signing/storage failures,
revocation after claiming and corrupt/unsafe claims. Two command-level cases use
the actual AHV HTTPS transport against a synthetic loopback service: a second
process sends no duplicate page chain, and termination of the first client does
not permit automatic recapture. The failed pre-fix race regression is retained
in the delivery evidence. These are local protocol/custody tests, not installed
vendor, filesystem power-loss, PostgreSQL or fleet-scheduler qualification.

Collector IDs, discovery wire formats, normalizer 2, profile resolution 3 and policy
capsule/realization 2 are unchanged. The new local reference is not a compatibility
wrapper, a native capability claim or an approval conversion. Newly collected facts
still require new digest-bound assessment reviews; partial inventory stays partial.

B10/B13/B14–B16/B22 remain partial. Installed command composition is implemented; signer custody,
credential issuance/renewal/revocation, Vault publication, durable anti-rollback and
independent retention, visibility/privilege-loss reconciliation, missing image/hardware
facts, verified external dependency evidence, owner-facing workflow integration,
durable fleet scheduling and estate qualification remain open. Existing application
draft persistence and signed assessment-only owner decisions are implemented; this
custody change neither replaces them nor accepts their unresolved dependencies. Later provisioning, transfer, fencing, cutover and recovery are separate work.
Wave 2 remains open; no Wave 3 work is started by this B22 correction. No installed
vendor, production guest or production dataset was contacted by these tests.
