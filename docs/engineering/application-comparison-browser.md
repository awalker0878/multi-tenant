# Browser comparison of a retained application

Reviewed 30 September 2026. This B19/B20 increment follows the
[existing B01–B50 plan](../product/enterprise-workload-mobility-execution-plan.md).
It connects the portal to the existing [application assessment service](application-comparison.md)
and format-2 selection binding, not to a new controller or native execution owner.

## Operator path

Sign in through the existing portal. Load source observations and add at least two
distinct destination observations using the existing destination picker. Select the
shared migration method, network mode and data mode. In Application drafts, load
the current saved application with the historical-revision field empty. The new
**Compare a saved application** panel shows the exact application revision, record
and observation digests, and every retained native member. Enter an explicit guest
profile for each member and submit the comparison. No request JSON is hand-authored.

The draft must be unchanged, current and not awaiting reconciliation of an unknown
save. Historical or superseded drafts are read-only and cannot become new comparison
selections. Editing, saving, loading another draft or clearing its view invalidates
the application selection. The single-VM selector cannot substitute membership.
Creating drafts or changing membership/dependency evidence still uses the existing
operator/API path; this panel does not implement that missing guided authoring flow.

Results show the checked owner review, selection digest, all destinations, original
and latest inventory generations, exact capacity identity, combined logical demand
and all per-member findings. Missing capacity remains unknown. Units for memory and
storage are bytes. No resource is reserved; staging, retained-source and recovery/HA
footprint are not included. A held owner review produces no destination calculations.
A valid calculation may still be blocked or unknown and never approves migration.

## Client composition and refusal rules

`provisioner/controlplane/api/portal/application_comparison.js` owns this read-only
component. The existing draft component exposes only an unchanged current saved
selection. `app.js` supplies the same tab identity, destination picker and route
settings. Script loading is ordered through the existing same-origin portal routes,
no-store headers and content security policy. No second login, storage, issuer,
SQL writer, native adapter or compatibility entry point is introduced.

The browser builds exactly one bounded POST to
`/v1/assessments/applications/compare`. Existing limits remain 2–100 members,
2–20 destinations and at most 200 member/destination combinations. The canonical
SHA-256 selection digest uses the API's sorted compact ASCII JSON, including Unicode
escapes and omitted absent capacity selectors. It is a consistency binding, not a
signature or independent native evidence. Format 1 and mismatched format-2 replies
are rejected; existing API/CLI interpretation versions do not change here.

The report must match the retained draft/source/review, complete member/profile set,
startup order, dataset counts, ordered destinations and selected capacity identities.
Wrong scopes, omitted members, changed pools, missing shortages or required unknowns,
weakened aggregate severity and true ownership/execution/reservation flags prevent
display. UTC comparisons retain microseconds rather than rounding evidence ordering
to JavaScript milliseconds. Native signatures, current authority, assessment rules
and capacity calculations remain the authenticated server's responsibility.

Requests are at most 128 KiB, responses at most 1 MiB. Strict streaming JSON rejects
duplicate properties, invalid UTF-8, excessive nesting, nonintegral numeric syntax,
unsafe integers and ambiguous response lengths. Integers beyond JavaScript's exact
safe range are refused rather than rounded; the installed Python CLI remains the
alternative for otherwise valid larger quantities. HTTP 200 and JSON content type
are required. Unread streams are cancelled and readers released on refusal.

Each request freezes the selected draft, inputs and session generation. A changed
destination, pool, route setting, profile, draft or login invalidates the request and
clears earlier advice. Cancellation and page departure do the same. Late responses
cannot restore cleared results. The total client deadline is 15 seconds; no automatic
retry, token renewal, inventory recapture, rebase or migration request follows a hold.
HTTP 401 clears the tab's authorization. Other failures display no partial report.
Remote strings are assigned as text, never markup, and no credentials/results are
stored in browser persistent storage. Displayed advice is an as-of result, not a
continuously refreshed authorization or automatic revocation subscription.

## Verification and remaining wave gates

`test_application_comparison_assets.py` verifies actual portal asset routing and
composition and invokes `test_application_comparison_ui.js`. The Node suite uses
actual API/application-service response fixtures with independent synthetic review
signatures, plus a DOM harness loading all three real portal scripts. It covers
selection hashing, complete findings, response bounds, unsafe values, cancellation,
late session/input changes, held reviews and draft-edit invalidation. Existing draft
and single-VM portal tests remain in force. These are client/API contract tests,
not a real-browser rendering, PostgreSQL or installed-platform qualification claim.
A Chromium navigation smoke test was blocked by the development environment and
is not reported as passed. Final CI and its skips must be reported independently.

**Wave 2 remains open.** This completes browser consumption of saved-application
comparison, not guided draft creation/membership/evidence editing, independently
verified external dependencies, remaining image/hardware/security facts or inventory
visibility reconciliation. B22 scheduling, concurrency, freshness, larger resumable
publication and estate measurements remain open. Wave 3 B23/B24 still need actual
commissioned capacity/IPAM/staging reservations and admitted provisioning effects;
no UI result supplies those owners or permission to contact a native environment.
