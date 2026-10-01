# Browser workspace for application draft creation and editing

Reviewed 1 October 2026. This B17/B20 continuation follows the
[existing B01–B50 plan](../product/enterprise-workload-mobility-execution-plan.md).
The existing authenticated portal creates initial application proposals and explicitly
revises saved membership, dataset groups and dependency assertions without hand-authoring
request JSON. Each save appends a revision; the original record is never overwritten. Drafts are still
UNREVIEWED; no ownership acceptance, reservation, native adoption or migration is issued.

## Create an initial application

In **Application drafts**, enter an authorized environment and a new application ID,
leave historical revision blank, and select **Start new application**. The component
first reads the existing scoped draft-list API with `limit=1`, then reads the latest
stored discovery generation. The generation must match the listing. The exact scope,
generation, result digest, capture time and completeness are displayed and retained.
An empty draft list is valid when an observation exists. No draft is saved by opening
this workspace. Missing, changed or inconsistent source summaries leave it closed.

Select **Load observed identities** and, when needed, **Next observed identity page**.
Every page is a separate explicit request for at most 50 stored summaries at the
pinned generation. Only VM rows can be selected; native IDs are not manually entered
or inferred from names. Assign a unique logical workload ID to each selected VM.
Selected members survive pagination; an unadded alias must be added or cleared first.
The browser permits at most 200 pages per source (10,000 summaries). Reaching that
bound stops enumeration, not the ability to propose an already selected group. It
is not a complete-estate search/export or an independent visibility reconciliation.

Enter the application name and proposed owner ID. Add explicit consistency-group IDs
and their dataset IDs, with every proposed dataset in exactly one group. These are
operator assertions, not observed filesystem paths, boot-volume inference, data
ownership, independent consistency evidence or a migration manifest. Add dependencies
one at a time using the selected logical members: relation, known/unknown state,
source, source-reference ID and UTC observation time. A known edge needs a selected
target and no unknown reason. An unknown edge needs a reason and no target. External
or unobserved dependencies remain explicitly unknown. Source labels do not verify
CMDB, monitoring, guest or application-owner evidence.

Before the first save, members, groups and assertions can be removed explicitly. A
member referenced by an assertion cannot be removed until that assertion is removed.
Unfinished input rows survive ordinary redraws and must be added or cleared before
saving; they are never silently omitted from a submitted proposal. Review the startup
order, which must name every selected member once and respect known STARTS_AFTER
edges. Confirm the unreviewed save explicitly. Every local change clears confirmation.

The initial PUT uses the existing contract with `expectedRevision: 0`. The server
reconstructs and verifies the pinned inventory, rechecks current scope, source age,
membership, assertion times and source currency, and appends revision one atomically.
The browser cannot create a generation, assert a server author or override those checks.
Successful readback retains the recorded author and false ownership/execution flags.
Only an unchanged current saved record can become the separate application-comparison
selection; local proposals and unresolved saves cannot.

## Revise a saved application

**List drafts** fetches one live page of at most 50 summaries; **Next live page** is
explicit, not an automatic estate export. Load a current record by application ID,
or supply an exact positive historical revision. The source generation/result digest,
author/time, members, datasets, consistency groups and all dependency assertions
remain visible. Unknown dependencies are not hidden.

Name, proposed owner and startup order can be edited directly. For structural changes,
load a current saved draft with no pending edits, then select **Edit membership and
evidence**. One existing latest-generation GET must match the saved generation and
result digest exactly. The client never changes the source pin or automatically rebases.
An unavailable, mismatched or unwritable source holds both metadata/structural editing
and comparison until an explicit current reload. Opening a proposal makes no PUT and
issues no owner review or native collection request.

The same authoring tables start from deep copies of the saved members, dataset IDs,
groups and dependency assertions. Original array order and timestamp strings, including
microseconds, remain intact unless explicitly changed. Add observed VMs from the pinned
identity pages. Remove and re-add a member to change its logical mapping; first remove
any assertions referring to that member. Remove and add replacements explicitly to
correct groups or evidence, including changing KNOWN/UNKNOWN state. Removing one group
removes only its dataset IDs from this proposal and preserves the ordering of unrelated
IDs. It does not delete data or alter an earlier revision. Empty assertions mean none
were recorded, not independently verified absence of dependencies.

Pending aliases and unfinished evidence fields are retained across redraws and block
saving. Existing membership, dataset, dependency, order, byte and page limits apply to
both initial and revised proposals. The new save uses the loaded `expectedRevision: N`
and requires acknowledgement of exactly `N+1`; it never resets a saved edit to revision
zero. The server independently validates membership, freshness, current source and
concurrent revisions. Even an unchanged proposal requires confirmation and appends a
new unreviewed revision when accepted. Browser revision values must permit a safe next
integer; they do not change the server's signed-64-bit API contract.

Entering editing invalidates the comparison selection immediately. Only a valid current
acknowledged record can be selected again, with its new revision and digests. It still
needs a separately accepted exact-draft owner review. Guided owner signing, independent
external evidence verification and administrator acceptance remain open. The
[operator CLI](application-draft-operator.md) continues to use the same API contract.

Historical and superseded-source records are read-only. Every edit pins the original
inventory and expected revision; there is no implicit rebase, rescan or selection of a
newer revision. Dirty or unresolved state prevents changing the selected environment
or application without an explicit discard. A proposed owner ID never verifies that
person's authority or transfers native workload ownership.

## One component, existing API and finite client bounds

`provisioner/controlplane/api/portal/application_drafts.js` owns creation, saved-record
editing and uncertainty handling. Shared proposal, dependency and list validators
replace the previous embedded copies; one `proposalRequest` owner checks initial,
metadata and structural requests, including the explicit writable expected revision.
The initial-only `creationRequest` helper is removed, with callers migrated and no
forwarding alias. No second representation, controller or route is introduced. The existing `app.js` supplies the in-memory token and identity version.
Sign-out, a new identity and page exit clear content and abort outstanding reads.
Earlier identity/selection replies cannot repopulate the workspace. No browser
persistent storage, cookies, token refresh, external asset or native access is added.
Existing fixed-origin, no-store and content-security-policy asset serving is unchanged;
missing scripts leave markup controls disabled.

| Operation | Existing path / bound |
|---|---|
| Initial scope and source | Two serial GETs: `application-drafts?limit=1`, then `discovery/generations/latest`. No automatic collection or draft creation. |
| Saved edit entry | One latest-generation GET checked against the loaded exact source pin; no draft write, automatic rebase or owner review. |
| Source VM choices | One GET per explicit page: `discovery/generations/<pinned>/objects?limit=50`, using the exact identity cursor. Maximum 200 pages. |
| Proposal | 2–100 observed VMs; 1–1,000 dataset IDs; 1–100 disjoint consistency groups; 0–500 attributed dependencies; complete startup order. |
| Save | One PUT to `application-drafts/<id>`; at most 128 KiB including source pins and expected revision. |
| Reconcile | One GET of the exact attempted revision; never an automatic PUT retry. |
| Transport | Per-request 15-second abort deadline; same-origin, no cookies, redirect error, no-store; declared and decoded response size at most 512 KiB each. |

Responses require JSON media type, valid UTF-8, no duplicate fields, closed expected
shapes and exact environment/scope/generation/revision bindings. Digest fields must be
strings, not coerced arrays. Unsafe integers and fractional/exponential spellings are
refused rather than rounded. Native selectors retain their bounded native text rather
than being reduced to logical IDs. All labels and assertions are literal text, not HTML.
Object pages must retain exact native kinds/IDs, unique identities across pages, the
last-identity continuation and count consistency. Any missing or inconsistent page
holds both initial and saved-revision authoring until explicit discard/reload. A terminal stored chain, a zero unknown
count or a COMPLETE summary does not independently prove native completeness.

New dependency timestamps require an explicit UTC suffix, real calendar date and
seconds, with at most six fractional digits. They are canonicalized to the Python
proposal format without losing microseconds or guessing a local timezone. Invalid or
absent evidence time is not replaced with the browser clock. The server remains the
owner of source/evidence freshness and acceptable attribution.

The [Fetch standard](https://fetch.spec.whatwg.org/), rechecked 1 October 2026, defines
redirect, abort and content-coding handling. Fetch exposes decoded body bytes; their
length is compared to Content-Length only for absent/identity content encoding.
Compressed responses retain independent declared-size and decoded-size bounds, not
an incorrect equality between compressed and decompressed lengths. Cancellation is
not evidence that an attempted write did not reach the database.

## Save acknowledgement and reconciliation

A save is acknowledged only on HTTP 200 with the exact next revision, original source,
scope, complete submitted proposal and false authority flags. Creation therefore
requires revision one; a conflict never overwrites an existing application. The request
and reconciliation target are frozen before sending. An exact APPLICATION_DRAFT_CONFLICT
requires reloading current history. A lost connection, malformed/mismatched reply,
other error or interrupted PUT leaves **SAVE UNKNOWN** and prevents another save.
No retry, token refresh, deletion or compensating write is issued.

**Check exact saved revision** reads the original expected next revision. Missing,
inaccessible or different history leaves uncertainty in place. Matching history is
shown read-only with its recorded author; it is not proof that this tab, rather than
another actor, committed it. Reload current history before further edits. Initial
creation uses the same uncertainty owner as later edits, not an optimistic success
message or a second journal.

Discarding unresolved state requires a second explicit checkbox and never undoes a
committed write. Navigation warns about dirty/in-flight/unresolved work, but is not a
durable journal or guaranteed navigation block. Sign-out intentionally clears sensitive
tab state. After closing/changing identity, reconcile persisted server history against
the original application/source/revision, not the absence of a local record. The
collector's discovery outbox is separate and is not used for human draft edits.

## Verification and remaining work

The existing Node suites exercise the real component and compose it with the portal
shell and application comparison. This saved-edit continuation adds 27 standalone
cases: exact source/revision entry, unchanged-byte retention, member/group/assertion
replacement, historical/superseded holds, failed-source/page holds, stale replies,
identity cleanup, frozen writes, conflicting revisions, uncertain acknowledgement,
exact `N+1` reconciliation, discard and safe-integer bounds. All 124 standalone cases
passed locally. Python serialization supplies two additional conditional Node cases;
one drives saved-record editing through the actual workspace and passes its changed
request back to the actual Python proposal parser and validator. The focused 25-test
Python run passed; these overlapping suite counts are not additive.

A broad local API run discovered 224 tests, with two `psycopg` module-import errors;
the 222 runnable tests passed. That attempt is not a complete API pass. Local FastAPI
is 0.128.2 rather than the declared deployment pin; final-revision CI must independently
run the pinned installed-package, database/API and integration gates. Successful prior
revision checks are historical evidence, not qualification of this change.

An offline Chromium DOM smoke used the repository markup, styles and component,
synthetic in-memory identity and injected transport. It revised membership/data/evidence
and acknowledged revision two after actual Python parsing/validation/serialization,
with no script errors. It did not test SSO, network transport, persistence, an actual
owner signature or a vendor environment. The earlier navigation attempt was blocked by
the browser's administrator policy and remains a blocked result; no browser policy
was disabled. Accessibility, deployed usability and administrator acceptance remain
separate from this component smoke.

No database migration, grant expansion, API/collector/normalizer/profile format change,
compatibility shim or native support claim is introduced. Initial and saved-revision
browser authoring are implemented; independent dependencies, owner-facing signing and
administrator acceptance remain open. B22 fleet scheduling, monitoring, resumability
and measurements and later provisioning, transfer, fencing, cutover, post-write recovery
and qualification obligations remain in the existing plan.

## Signed review and application comparison are separate

The [owner-review contract](application-owner-review.md) provides independent exact-draft
assessment/revocation. The [saved-application comparison](application-comparison-browser.md)
uses a current saved draft plus separately accepted review. Creating or saving a draft
does not sign that review, change status from UNREVIEWED, grant ownership or authorize a
migration. Application-wide native execution is not supplied by either browser view.
