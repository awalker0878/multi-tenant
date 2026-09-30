# B22 — inspect local discovery capture and recovery state

Reviewed 30 September 2026. This continues
[Wave 2 of the existing B01–B50 plan](../product/enterprise-workload-mobility-execution-plan.md).
It exposes the existing private outbox and first-capture claim to an operator without
collecting, publishing, resetting an intent or starting a later-wave operation.

## Installed command

```sh
hosting-discovery-collect inspect --config /etc/hosting/discovery/collector.json
```

The path is illustrative, not a supplied site configuration. Use the existing
protected collector configuration, original signed campaign, public trust policy,
independent native-read witness policy and exact local outbox root. The `native`,
`signer` and `publisher` sections may be omitted. No native token, signing private
key, client TLS certificate, API connection or database connection is needed.
Current campaign, enrollment and witness authority are still mandatory. An expired
or revoked campaign cannot be inspected through an offline trust bypass.

| Report status | Meaning |
|---|---|
| `LOCAL_REFERENCE_ABSENT` | This root has neither a campaign reference nor a capture intent at the checked reads. It does not prove no previous native read, loose payload, publication or other-root attempt exists. |
| `COLLECTION_UNRESOLVED` | A matching local capture intent exists without a completed original. Preserve the hold and reconcile the attempt; inspection does not unlock collection. |
| `STAGED_ORIGINAL` | The exact referenced signed original is retained and verifies under current authority. Its original digests, capture time, completeness and count are reported unchanged. This is not a server receipt. |

Exit 0 means a valid inspection report was produced, including absent or unresolved
local states. Automation must inspect `status` and `reconciliationRequired`; exit 0
alone does not mean collection completed or publication succeeded. Corruption,
unsafe files, mismatched identities, missing referenced bytes, changing state or
unavailable authority produce the existing generic `HELD` outcome and exit 2.
Interruption retains the existing exit 130. No raw exception, secret path, private
key, native response or inventory object is printed.

## Report and consistency contract

`hosting-discovery-outbox-inspection/1` identifies the exact campaign, environment,
authorization digest and checked time. `collectionIntent`, when present, contains
its original local record digest, attempt ID and claim time. This local intent is
not an independently signed completion record. `original`, when present, contains
request/result digests, capture time, completeness and object count, not full facts.

Every valid report includes `localCustodyOnly: true`,
`consistency: LOCAL_RECORDS_RECHECKED`, `publicationStatus: NOT_CHECKED`, and false
`collectionRequested`, `publicationAttempted` and `executionAuthorized` flags.
`reconciliationRequired` describes missing completed **local custody**. A false
value for a staged original does not settle a lost server acknowledgement, establish
independent retention, or authorize a retry or native operation.

The implementation remains in `PrivateDiscoveryOutbox.inspect` and the existing
collector runtime. Namespace derivation is shared with normal custody, but inspection
does not call the directory-creating store path. It reads only the selected hashed
claim/reference and, when referenced, its exact payload. No directory scan, orphan
promotion, reference repair, intent removal, new signature or record write occurs.
Filesystem access timestamps may change; record contents, names and modes do not.

Claim and reference reads are bounded to 1 KiB each; the referenced signed original
retains the existing 1 MiB limit. Strict canonical JSON, protected regular-file and
ancestor checks, exact tenant/campaign/environment/signature bindings, UTC claim time,
original result signatures and current authority are verified. Two bounded record
reads bracket live signature verification; a concurrent completion, deletion or
changed payload holds rather than mixing observations. UTC expiry and regression
are checked again after the final read. This is not an atomic global snapshot,
an administrative rollback detector, a hard filesystem-I/O deadline or proof that
an unrecorded remote operation is absent.

## Recovery and wave boundary

Completed originals without the newer collection-intent record remain inspectable
under their original signed format. A damaged intent is not ignored merely because
a valid payload is also present. Loose payloads without a campaign reference are
not discovered or selected automatically. Preserve them for separately authorized
original-digest reconciliation, as described in the
[publication recovery contract](discovery-publication-recovery.md).

Tests exercise all three states, unchanged outbox records, current signatures,
revocation, mismatched scope, malformed/private/nonregular files, missing payloads,
concurrent state changes and fresh command processes without native/signing material.
The focused local suite is not full-tree, database or installed-vendor qualification;
record exact final-head CI results separately in the existing PR delivery ledger.

**Wave 2 remains open.** This completes operator inspection of local capture custody,
not durable fleet dispatch, global endpoint budgets, periodic freshness history or
alert delivery, larger resumable publication, or estate-scale acceptance. Independent
visibility, remaining image/hardware/security facts, verified external dependencies,
guided authoring and adoption/owner acceptance also remain open. No Wave 3 work or
completion claim is introduced; no production environment is contacted.
