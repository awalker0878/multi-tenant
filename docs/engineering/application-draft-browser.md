# Browser workspace for existing application drafts

Reviewed 29 September 2026 (America/Toronto). This B20 increment follows the
[existing B01–B50 plan](../product/enterprise-workload-mobility-execution-plan.md).
It composes a bounded application-draft workspace into the existing authenticated
portal. It does not implement owner acceptance, native adoption or migration.

## Operator path and deliberately limited editing

Sign in through the existing enterprise portal. In **Application drafts**, enter
an authorized environment ID and select **List drafts**. Listing fetches one live
page of at most 50 summaries; **Next live page** is an explicit request, not an automatic
estate export. Enter a listed application ID to load its current revision, or an
exact positive revision for a historical read. The original source generation,
result digest, recorded author/time, members, datasets, consistency groups and
all dependency assertions remain visible. Unknown dependencies are not hidden.

The form edits only an existing current draft's name, proposed owner ID and startup
order. Startup order must name every member once and respect known STARTS_AFTER
edges. Membership, datasets, consistency groups and dependency evidence are read-only
and retained in the submitted proposal, including their original timestamp precision.
Creating a draft or changing those assertions still uses the
[operator CLI](application-draft-operator.md). This is not the completed guided
application-creation or dependency-review interface required for B17/B20 closure.

Historical and superseded-source revisions are read-only. Editing pins the original
inventory generation/result digest and expected revision; there is no implicit
rebase, rescan or choice of a newer revision. Confirm the unreviewed save explicitly.
While edits or an unresolved save exist, changing the selected environment/application
requires an explicit discard. A successful response still says UNREVIEWED, with
ownershipAccepted and executionAuthorized false. Changing a proposed owner ID does
not verify that person's authority or transfer workload ownership.

## API, identity and response boundaries

`provisioner/controlplane/api/portal/application_drafts.js` owns the component.
The existing `app.js` supplies its in-memory token and identity version. Sign-out,
a new login and page exit clear draft content and abort outstanding reads; replies
from an earlier identity or selection cannot repopulate the workspace. The component
stores no token, draft or unresolved operation in browser persistent storage and
does not use cookies or alternate authentication. API session/scope/evidence checks
remain authoritative for every list, read and write.

The portal serves the new script through its existing fixed-origin, no-store and
content-security-policy boundaries. The script has no external dependency or
native access. Missing component assets leave its markup controls disabled rather
than enabling a partial editor. Existing job, discovery, approval and comparison
interfaces continue to use their original owners.

Every action issues at most one fixed, same-origin API request with redirect mode
`error`, no credentials cookies, a 15-second abort deadline and bounded response
streaming. Response JSON requires the expected media type, valid UTF-8, no duplicate
keys, closed record fields and exact environment/scope/source/revision semantics.
The response bound is 512 KiB and the complete save request remains within the
existing 128 KiB API limit. Counters outside JavaScript's safe-integer range, and
fractional/exponential numeric spellings, are refused instead of rounded. All
untrusted labels and assertions are rendered as literal text, not HTML.

The [Fetch standard](https://fetch.spec.whatwg.org/), consulted 29 September 2026,
defines the request mode, redirect and abort mechanisms used here. Those mechanisms
limit the client transport; they do not replace server authorization or prove that
a cancelled write did not reach the database. Node tests exercise their selected
options and cancellation behavior, not every browser implementation.

## Save acknowledgement and reconciliation

A save is acknowledged only on HTTP 200 with the exact next revision, original
source, scope, complete submitted proposal and false authority flags. An exact
APPLICATION_DRAFT_CONFLICT requires reloading current history, not an automatic
retry. A lost connection, malformed or mismatched reply, other error response or
interruption after attempting the PUT leaves **SAVE UNKNOWN**. No automatic
retry, token refresh or compensating write is issued.

**Check exact saved revision** performs only a GET for the original expected next
revision. Missing, inaccessible or different history leaves the uncertainty in
place. Exact matching history is shown read-only with its recorded author; it is
not proof that this tab, rather than another actor, committed that revision. Reload
current history before further edits. Server idempotency/conflict rules remain
unchanged and authoritative.

Discarding unresolved state requires a second explicit checkbox and never undoes a
committed write. Leaving the page warns about dirty/in-flight/unresolved work, but
that warning is not a durable journal or a guarantee that navigation can be stopped.
Sign-out intentionally clears sensitive tab state. After closing the tab or changing
identity, reconcile via persisted server history and original source/revision inputs;
do not assume that cancellation, a missing local record or an error means rollback.
The discovery publication outbox is a separate mechanism and is not used for human
application-draft edits.

## Verification and unfinished work

The new Node suite runs the actual component and, in a composition test, the full
portal shell. It covers strict decoding, literal rendering, scope/cursor checks,
source/history holds, retained assertions, explicit confirmation, frozen submissions,
conflicts, unknown acknowledgements, GET-only reconciliation, identity changes,
resource cleanup and deadlines. Python ASGI tests check asset serving, disabled and
wrong-origin behavior, script order and accessibility labels; the Python test runner
also invokes the Node suite when Node is available, without a new workflow.
Installed-package checks include the new asset outside the source checkout.

Report final-revision CI separately from focused local tests. The local Chromium
smoke attempt was blocked by the execution environment's administrator navigation
policy; it did not validate layout, keyboard interaction or an end-to-end browser
session. Browser usability/accessibility acceptance and deployed SSO still require
an authorized browser environment. No browser restriction was disabled.

No database migration, grant expansion, collector/normalizer/profile version change,
compatibility shim or native support claim is introduced. B17 owner acceptance and
revocation, independently verified dependency evidence, reviewed assessment input,
full browser creation/membership editing and B22 scheduling remain open. Later native
provisioning, transfer, fencing, cutover, recovery and qualification gates are unchanged.
