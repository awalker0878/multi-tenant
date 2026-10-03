# Exact-draft owner-review inspection in the portal

Reviewed 1 October 2026; continuation from
`b0704b559d70a8f5b6af875ab933ef2fbf898fd4` under B17/B20 of the
[existing execution plan](../product/enterprise-workload-mobility-execution-plan.md).
This adds browser consumption of the existing signed-review read API. No signing,
enrollment, evidence ingestion, native ownership or migration authority is added.

## Operator path

Load a saved draft in **Application drafts** and select **Check exact owner review**.
The action uses the loaded environment, application ID and immutable draft revision:

```text
GET /v1/environments/{environmentId}/application-drafts/{applicationGroupId}/review?revision=N
```

There is one explicit request, not polling, a latest-revision lookup or another
approval flow. Current and historical saved records can be inspected. Local initial
proposals, structural working copies, unsaved metadata changes and unresolved saves
cannot be used as review inputs. Loading a draft does not automatically request a
review. No new API route or SQL privilege is needed.

The display retains the server evaluation time, exact native scope, original and
latest revisions/generations, draft/proposal/result digests, signed owner decision,
evidence ID/revision/digest, validity, candidate digest and unknown-dependency count.
Missing evidence is explicit, not inferred from the proposed owner ID. Unknown counts
are shown as not evaluated when no assessment candidate exists, never silently zero.
Native text is rendered literally and wrapped, not interpreted as HTML or a URL.

All eight states in [the signed-review contract](application-owner-review.md) remain
distinct: UNREVIEWED, REVOKED, HELD_SUPERSEDED_DRAFT, HELD_SUPERSEDED_INVENTORY,
HELD_INCOMPLETE_INVENTORY, HELD_STALE_INVENTORY, REVIEWED_ASSESSMENT_ONLY and
REVIEWED_WITH_UNKNOWNS. Only the last two have a candidate digest. Every state
retains false dependencyEvidenceVerified, ownershipAccepted and executionAuthorized.
A valid response is the API's result at checkedAt, not a continuing approval.

## One browser response interpretation

`ApplicationDraftWorkspace.validateReview` is the common wire-contract owner for
this action and the existing application-comparison report. The former comparison-local
validator is deleted and its consumer calls the common implementation; no forwarding
alias or compatibility representation remains. Existing server signature verification,
immutable-record checking and independent review authority are unchanged.

The client checks the complete closed response shape, all loaded draft/source pins,
exact scope, positive safe integer revisions, owner versus proposed owner/editor,
status precedence and evidence/candidate consistency. A returned latest generation
cannot regress behind the loaded record's already observed latest generation. Review
and evaluation times cannot predate the saved record. UTC parsing validates calendar
dates and retains up to six fractional digits; integer microsecond arithmetic prevents
a one-microsecond expiry or one-hour-limit violation from being rounded away.

These checks validate transport consistency, not native membership, signatures or
independent dependency evidence. Comparison still requests and verifies its own current
server-side evidence; it does not reuse the display as authorization. Server formats,
profile/normalizer versions, signed evidence bytes and interpretation are unchanged.

## Read bounds, invalidation and time

The action reuses the existing in-memory identity, epoch cancellation and bounded
request implementation: same-origin GET, no-store, omitted ambient credentials,
redirect rejection, 15-second abort deadline, strict duplicate-aware JSON and
512 KiB bounds for both declared and decoded response sizes. Authentication failure
uses existing session cleanup. Failure, malformed content or changed identity discards
the result without showing an earlier accepted review or issuing an automatic retry.

Starting any other draft operation, editing content, changing selected IDs, signing
out or exiting the page clears review content and its timer. A response reporting a
newer draft or source makes the current view read only until an explicit current
reload; it does not rebase or rewrite the immutable loaded record. A historical
acceptance or revocation never re-enables draft editing.

Display clearance is scheduled for the smaller of 60 seconds and remaining signed
validity at the server's checkedAt, conservatively subtracting the complete request
and processing elapsed time. Non-finite/regressed elapsed time or an elapsed display
interval holds the result. The browser monotonic clock measures elapsed duration;
the server's UTC strings remain unchanged for human inspection. This is a local
presentation bound, not an authority lease or proof of synchronized clocks.

Hidden tabs clear the display. An in-flight review read is cancelled and its late
reply suppressed. Hiding during a separate draft save does not cancel that save,
erase its uncertainty or disable exact-history reconciliation. Returning to the tab
requires another explicit check. Browser callbacks may be delayed or frozen; timer
clearance is best effort, not a hard revocation deadline or continuous monitoring.
No UI state is persisted, and no browser key or signed artifact is produced.

## Verification and remaining integration

The added Node cases use all eight actual Python service states with ephemeral
Ed25519 signature verification, plus real authenticated API export/review responses.
They cover exact bindings, malformed fields, authority injection, microsecond bounds,
status conflicts, unknown counts, invalid responses, authentication/selection changes,
hidden tabs, timing, uncertain saves, read deadlines and literal rendering. The
existing draft/authoring/comparison cases continue to exercise the same scripts.
A Python asset test checks the actual packaged shell and invokes the new Node suite
through the existing CI discovery path; no workflow modification is required.

The Chromium smoke uses the actual markup, styles and all three portal scripts,
with a synthetic tab identity and in-memory responses produced by the real API test
fixture. It checks review display and edit invalidation. It is not deployed SSO,
network/database persistence, accessibility acceptance or native-platform qualification.
Final-revision CI, installed-package checks and database/engine results remain separate
from local component tests and must identify their actual tested revision and skips.

The separate [owner signer](application-owner-signing.md) prepares/signs decisions.
Owner/key onboarding, authenticated signed-artifact delivery, independent dependency
enrichment and enterprise/administrator acceptance still keep B17/B20 open. This
increment does not close B05, Wave 2 or the later provisioning/migration waves.

## Primary browser references

Consulted 1 October 2026. The [W3C High Resolution Time working draft](https://www.w3.org/TR/hr-time-3/)
describes monotonic duration measurement separately from user-visible wall time; it
is cited as a working draft, not a deployment certification. The [HTML timer contract](https://html.spec.whatwg.org/multipage/timers-and-user-prompts.html#timers)
and [Page Visibility specification](https://www.w3.org/TR/page-visibility-2/) support
explicit visibility cleanup and the distinction between scheduled callbacks and a
hard timing guarantee. These references do not establish deployed browser acceptance.
