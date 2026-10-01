# Installed offline application-owner preparation and signing

Reviewed 1 October 2026. This B17/B20 continuation starts at
`1db0e51fa7a0ed8a974268c9d5202dd13fea7b40` and follows the
[existing execution plan](../product/enterprise-workload-mobility-execution-plan.md).
`hosting-application-review` prepares and signs the existing assessment envelope.
It does not enroll owners, submit evidence, access a database, contact a platform
or grant ownership/migration authority. It is separate from `hosting-operator`.

## Prepare, inspect, then sign

Export the full saved `hosting-application-draft-revision/1` record through the
existing authorized draft GET/operator path, retaining its immutable revision,
proposal and record digest. Transfer it to the owner's protected workstation through
the organization's approved channel. A summary listing is not a full export.
The owner must review the complete proposed membership, datasets, startup order,
known/unknown assertions, recorded editor and exact scope. A proposed owner name
and an internally consistent checksum do not establish authentic server provenance.

The following paths and IDs are illustrative. Both digest variables must be set
from independently reviewed records; no private key is passed on a command line.
Inputs and the already-created output directory must meet the custody requirements
below. Output names must not exist.

```sh
hosting-application-review prepare \
  --draft-file /srv/owner-review/draft.json \
  --record-digest "$REVIEW_RECORD_DIGEST" \
  --evidence-id review-001 --evidence-revision 1 \
  --decision ACCEPT_FOR_ASSESSMENT --review-reference change-001 \
  --ttl-seconds 1800 --output /srv/owner-review/decision.json
```

Preparation uses the existing retained-record parser to recompute the proposal and
record digests; it does not invent native observations. It checks exact full-export
shape, version, false authority flags, scope, source metadata, UTC time and independent
owner/editor binding. Opaque recorded editor subjects retain the existing audit
contract, including valid OIDC subjects; they are not coerced into logical-ID grammar.
Acceptance refuses an export explicitly marked source-superseded. Historical records
can still be the subject of an exact `REVOKE` decision.

The new private file contains canonical unsigned `hosting-assessment-evidence/1`
JSON. The safe summary reports `PREPARED_UNSIGNED`, its `evidenceDigest`, exact draft
and proposal digests, decision, owner and expiry. Inspect the complete prepared file
and explicitly confirm that digest before signing. This is a two-command boundary,
not an automatic sign-after-prepare pipeline.

```sh
hosting-application-review sign \
  --draft-file /srv/owner-review/draft.json \
  --record-digest "$REVIEW_RECORD_DIGEST" \
  --decision-file /srv/owner-review/decision.json \
  --confirm-evidence-digest "$REVIEW_EVIDENCE_DIGEST" \
  --config /srv/owner-review/signer.json \
  --output /srv/owner-review/signed.json
```

Signing preserves the prepared evidence ID, revision, issue/review times and expiry.
It does not renew an expired decision or select another draft. Only the exact canonical
prepared bytes are accepted; whitespace rewrites or changed fields require a fresh
explicit preparation/review, not silent normalization under an earlier confirmation.
The existing evidence stream requires a unique evidence ID and explicit revision.
This offline command does not allocate or reserve either; ingestion resolves conflicts.

## Existing enrollment authority and key custody

The protected config has exactly `format`, `trust` and `signer`:

| Field | Required value / meaning |
|---|---|
| `format` | `hosting-application-review-signer/1`. |
| `trust.policyFile` | Absolute path to the existing root-signed assessment enrollment policy. |
| `trust.rootKey` | Base64-encoded 32-byte Ed25519 public root key, independently pinned. It is not a signing private key. |
| `trust.minimumRevision` | Explicit positive signed-64-bit policy floor from protected administration. |
| `signer.keyId` | The exact independently enrolled application-owner key ID. |
| `signer.keyFile` | Absolute path to an independently provisioned raw 32-byte Ed25519 private key. PEM, arbitrary-length secrets and key generation are not supported. |

The existing `SignedFileAssessmentTrustStore` now shares one enrollment selector
between pre-sign authorization and original signature verification. The key must have
the exact `APPLICATION_OWNER` role, proposed owner subject, environment/seven-field
native scope and validity interval. The owner differs from the saved editor. Another
role, subject, root key, public key, revoked key/evidence or stale policy cannot substitute.
Private signing material remains outside the control API and operator client.

Eligibility is checked before signing; the actual signature and current root-signed
policy are verified again before publishing the output. Config, private key, reviewed
export and prepared bytes are reread; changed inputs hold. UTC regression or expiry
holds rather than extending validity. The existing maximum decision lifetime is one
hour from review and must fit the enrolled key's validity. No separate approval store,
trust issuer, evidence interpretation or privileged runtime path is introduced.

These are checks against the currently provisioned policy file, not an online
revocation lookup or proof that the workstation has the newest policy. Independent
policy distribution and minimum-revision custody across restart/restore are deployment
obligations. No HSM, hardware-backed key, secure-memory zeroization or production key
custody is claimed by a successful software test.

## Private files, publication and uncertainty

This implementation targets a POSIX signing workstation with descriptor-relative
open/link operations and no-follow checks. Every input/output uses an exact absolute
path. Ancestors must be owned by the current user or root and cannot be group/world
writable, except root-owned sticky intermediate directories. The final parent must
be private (no group/other access). No directory is created automatically.

Inputs must be private, single-link regular files, not symlinks, FIFOs or devices.
Reads are bounded and detect changed size/timestamps during access. Full draft exports
are limited to 256 KiB, prepared evidence/configs to 64 KiB, policies to 1 MiB and
private keys to exactly 32 bytes. Duplicate JSON properties and non-finite/oversized
inputs are refused. These bounds are not estate-size or filesystem-performance claims.

Publication writes a private temporary file in the same protected directory, flushes
and fsyncs it, rechecks inputs/authority, and links it into a new final name without
replacement. Cleanup removes the temporary name and fsyncs the directory. Existing
outputs, even identical ones, are not overwritten. An error or interruption may leave
the final file; preserve and reconcile its exact bytes before deciding what to do.
Do not automatically retry with a new evidence ID, erase possible output or infer that
no signature was produced. These checks do not defeat a compromised root/owner account
or promise a hard I/O deadline or remote delivery.

Exit 0 returns a bounded digest/status summary. Errors return `OWNER_REVIEW_HELD`
and exit 2; interruption returns `OWNER_REVIEW_INTERRUPTED` and exit 130. Both error
reports retain `outputMayExist: true` and contain no raw paths, keys or exception detail.
Help remains the ordinary parser help. Successful summaries always retain false
`ingested`, `dependencyEvidenceVerified`, `ownershipAccepted` and `executionAuthorized`.

## Signed output is not accepted evidence

The completed artifact contains exactly `evidence` (the unchanged canonical envelope)
and `signatures` (key ID and Base64 Ed25519 signature). `SIGNED_NOT_INGESTED` is the
successful signing status. The signature covers the complete canonical evidence
message, not the digest confirmation string or arbitrary user-selected content.

A trusted custodian can supply these existing arguments to
`AssessmentInputRepository.ingest(ctx, evidence, tuple(signatures))` under its already
separate authenticated tenant context and ingest role. This is the existing repository
interface, not a new public API, installed importer, database credential recommendation
or completed artifact-delivery service. Deployment of that delivery path remains open.

Actual ingestion independently validates the retained immutable SQL draft, original
source, owner/editor separation, current enrollment, signature and revision stream.
Acceptance requires the current draft/source. An export can become stale after review;
a valid offline signature does not bypass that check. Revocation targets its exact
historical draft and cannot revoke a different revision. The existing read-only review
API/operator path reports accepted evidence separately; immutable drafts stay UNREVIEWED.

## Verification and remaining work

Tests use synthetic exports, ephemeral Ed25519 keys and real signature verification.
They cover digest/content binding, key/role/scope independence, current/revoked policy,
clock changes, file permissions/types/links, create-only publication, changed inputs,
post-publication uncertainty, redacted errors and absence of network calls. The actual
wheel test prepares and signs outside the checkout after deleting its build source.
The package gate also resolves the installed command to its package-owned entry point.

Three added isolated PostgreSQL cases connect real API export -> owner command ->
existing evidence ingest -> review read, reject a superseded draft, and revoke exact
historical evidence. They must run with the existing separate database test roles;
missing local roles cause explicit skips, not an integration pass. No platform,
production dataset or enterprise signing authority is exercised by these tests.

B17/B20 still require independently verified dependency/enrichment evidence, deployed
owner/key onboarding, authenticated artifact delivery, browser/enterprise review and
administrator acceptance. B05, the rest of Wave 2 and Waves 3–6 remain open.

## Primary contract references

The implementation retains the pinned cryptography contract rather than inferring
support from a newer package version. The [cryptography 46.0.4 Ed25519 documentation](https://cryptography.io/en/46.0.4/hazmat/primitives/asymmetric/ed25519/)
and [RFC 8032](https://www.rfc-editor.org/rfc/rfc8032.html) describe raw-key sizes and
full-message signing/verification. The [Python 3.13 OS interface](https://docs.python.org/3.13/library/os.html)
documents descriptor-relative file operations, hard links and fsync; operating-system
support and deployed filesystem behavior must still be qualified independently.
