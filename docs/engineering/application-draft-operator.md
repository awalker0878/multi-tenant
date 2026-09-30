# Application drafts: scoped listing and operator CLI

Reviewed 29 September 2026 (America/Toronto). This B17/B20 continuation follows
[the existing B01–B50 plan](../product/enterprise-workload-mobility-execution-plan.md).
It adds a bounded API listing and thin CLI save/load operations over the existing
[draft repository](application-drafts.md), not owner approval or migration execution.

## Installed commands

Install the existing `controlplane` extra. Obtain a current scoped SSO token using
the enterprise process; supply one token line through stdin, never an argument or
URL. The example HTTPS origin and IDs below are placeholders, not deployed inputs.
Global options precede the resource. Use `--ca-bundle` for the approved enterprise CA.

```sh
hosting-operator --api-url https://control.example --token-stdin application-drafts list --environment env-1 --limit 50
hosting-operator --api-url https://control.example --token-stdin application-drafts get --environment env-1 --id app-1
hosting-operator --api-url https://control.example --token-stdin application-drafts get --environment env-1 --id app-1 --revision 1
```

Save a new proposal by explicitly supplying the chosen discovery generation,
its exact lowercase SHA-256 result digest, and expected revision zero. For edits,
load the current draft and supply its revision; do not automatically choose a newer
revision or inventory generation. `RESULT_DIGEST` below must be replaced with the
actual selected digest; the literal placeholder is deliberately invalid.

```sh
hosting-operator --api-url https://control.example --token-stdin application-drafts save --environment env-1 --id app-1 --generation 1 --result-digest RESULT_DIGEST --expected-revision 0 --file proposal.json
```

`proposal.json` contains exactly `draft` and `dependencies`, using the existing
closed request fields and limits. When editing a GET response, retain its source
and revision separately and copy only `proposal.draft` and `proposal.dependencies`
into the input document. Do not send the full response, actor, status, review,
ownership or execution fields. The file must be a bounded regular file, not a
symlink or FIFO; the complete request must fit the existing 128 KiB API limit.
Duplicate JSON fields, excessive nesting, invalid encoding and non-finite or
out-of-range numbers are rejected before HTTP. Native membership, dependency and
current-authority validation remains exclusively at the API, not copied into a
second local controller.

The new `provisioner/cli/application_drafts.py` owns client request/response shape
and is called by the existing `provisioner/cli/operator.py`. It imports no control
plane, database or platform adapter. No new executable, local SQL writer, credential
issuer, migration action or compatibility entry point is created.

Architecture guards explicitly classify `operator.py` and its draft helper as
remote API clients, not local execution owners. Both guards share that exact
classification; all other command modules still require the shared local service.
The draft helper is restricted to standard-library imports. The operator may
compose that helper and HTTP/TLS dependencies, never controller, database, native
adapter or peer-command modules. Negative fixtures resolve direct and relative
imports so moving a forbidden dependency behind `from ..` cannot bypass the guard.

## One live listing page

The new endpoint is:

```text
GET /v1/environments/{environmentId}/application-drafts?limit=50&after=app-1
```

`limit` is 1–100, default 50; omit `after` for the first page. Each item is the
latest revision of one application group. Group IDs use explicit ASCII byte order
(PostgreSQL C collation). `nextAfter` is the last returned group ID when another
row was observed, otherwise null. Supply it as `--after` for another explicit
CLI request. It is a position, not a signed grant or server URL. The client does
not fetch all pages automatically or treat a cursor as an endpoint.

The response uses `hosting-application-draft-list/1`, full exact scope, the selected
environment, `latestGeneration`, `consistency: LIVE_PAGE`, `items`, `nextAfter`
and `executionAuthorized: false`. A summary retains immutable revision/source,
digest and author/time metadata plus application name, proposed owner, member,
dataset, dependency and unknown-dependency counts. It does not return the full
proposal, native member list or dependency references. Read a selected exact
revision for those details. Unknown counts remain assertions, not independently
measured dependency coverage.

`ApplicationDraftRepository.list_current` uses one SQL statement for latest drafts
and inventory currency, validates stored checksums and rechecks live scope after
reading, including empty pages. Existing tenant RLS and full native-scope filtering
remain active. An empty authorized environment may have no discovery generation;
that is represented by null, not a fabricated generation or complete inventory.
The existing migration 0021 and runtime SELECT grants suffice; no migration or
additional write privileges are introduced by this increment.

Each page has one database statement snapshot. Separate pages are live reads, not
an immutable export: a concurrently created group behind the cursor requires a
new listing. `sourceSuperseded` compares the original pin with the generation seen
by that page; it is not a freshness, complete-visibility, owner-acceptance or native
qualification verdict. Always reload the selected draft before editing. The
[PostgreSQL 17 isolation reference](https://www.postgresql.org/docs/17/transaction-iso.html),
consulted 29 September 2026, explains why successive reads cannot be presented as
one frozen snapshot. Estate-scale latency remains unqualified under B22.

## Authentication, acknowledgements and uncertainty

GET/list require the existing exact-scope JOB_READER or EXECUTION_OPERATOR grant.
PUT additionally requires EXECUTION_OPERATOR and the current evidence gate. The
existing API derives the author from its authenticated session. Neither an input
owner ID nor a cursor creates scope or ownership. List response validation rejects
foreign scope, duplicated/nonadvancing groups, full proposals and approval claims.
All existing draft statuses remain UNREVIEWED with both authority flags false.

Every CLI invocation makes at most one API request and does not follow redirects,
retry, rebase, recapture native inventory or refresh a token automatically. A save
succeeds only on HTTP 200 with matching environment/application, next revision,
source generation/digest, unreviewed state and the submitted proposal content.
Equivalent UTC timestamp spellings may normalize, but assertions cannot disappear
or change. The comparison uses the in-memory original request, not a file reread
after transmission. This validates API response consistency, not a native proof.

| Outcome | Meaning |
|---|---|
| Exit 0 | A validated draft/list response was received. Saving remains draft-only. |
| Exit 2 | Read/list refusal, or the exact HTTP 409 APPLICATION_DRAFT_CONFLICT. No automatic rebase is attempted. A conflict does not prove an earlier invocation never committed. |
| Exit 3, APPLICATION_DRAFT_SAVE_UNKNOWN | A PUT was attempted but its exact acknowledgement could not be established. Reconciliation is required. |
| Exit 3, INVALID_INPUT / API_UNAVAILABLE / APPLICATION_DRAFT_RESPONSE_INVALID | Local input, transport or read-response failure. Error output excludes raw exception strings and tokens. |
| Exit 130 | Interrupted. An attempted save retains its uncertainty fields rather than claiming rollback. |

After a save is attempted, redirects, connection loss, malformed/mismatched replies,
HTTP 202, and non-conflict error responses are conservative unknown outcomes. Even
HTTP 404 can follow a committed PUT if the API loses authority before response
readback. The uncertainty record includes environment/application, original expected
revision, generation/result digest and a canonical request SHA-256; it contains no
proposal body or token. The hash is a reconciliation identity, not a server receipt
or cryptographic signature. Load exact history and reconcile; an explicitly approved
retry must retain the same content, actor and references. The server's existing
idempotency and conflict rules remain authoritative across restarts and users.

## TLS protection and verification

The operator CLI now supplies an explicit certificate-verifying SSLContext for
both enterprise-CA and default HTTPX/certifi-CA selection. It retains hostname
checks, TLS 1.2 minimum, strict/partial-chain flags, finite request timeouts and
`trust_env=False`. Inherited `SSLKEYLOGFILE` is not enabled and the environment is
not modified. A baseline regression reproduced the prior default-context helper
creating that file. The [Python 3.13 SSL reference](https://docs.python.org/3.13/library/ssl.html),
consulted 29 September 2026, documents the environment-sensitive helper and explicit
context alternative. Certificate/hostname checks are not disabled as a workaround.

Tests cover CLI requests, bounded files, exact content/source acknowledgements,
revision conflicts, lost replies, interrupted saves, scope/approval rejection,
strict JSON, encoded-once cursors and both TLS trust selections. API tests exercise
current session/scope checks, pagination and response guards. Disposable PostgreSQL
tests cover latest-revision ordering, supersession, summaries, tenant isolation,
post-read revocation and CLI-to-authenticated-API-to-database round trips using an
in-process HTTP test transport. Installed-package checks load the thin client
outside the checkout with legacy imports blocked. Report final-revision CI and
actual skips separately; these tests are not native platform qualification.

The separate signed owner-review path below now persists and evaluates exact-draft
assessment decisions. Owner-facing signing, trusted dependency enrichment and
application-wide destination planning remain unfinished B17/B20 work. The
[browser workspace](application-draft-browser.md) edits existing metadata/startup
order; this CLI still uses structured JSON for full proposals. B22 scheduling and scale, native provisioning, transfer, fencing,
cutover and post-write recovery remain in the existing waves. No native support
claim, reviewed candidate, ownership acceptance or production grant is added.


## Signed owner-review continuation

The [owner-review evidence contract](application-owner-review.md) now provides
independent exact-draft acceptance/revocation and GET-only candidate evaluation.
This is separate from draft saves, listing and editing; drafts remain UNREVIEWED.
The CLI/browser in this document do not issue signatures or show a native approval.
Read-only CLI status inspection is now available through the existing draft helper;
owner-facing signing, verified external dependencies and application-wide migration
planning remain open. The separate review does not change draft status,
create a native owner or authorize a migration.

### Read an exact draft's owner-review status

```sh
hosting-operator --api-url https://control.example --token-stdin application-drafts review --environment env-1 --id app-1 --revision 1
```

This is one GET, not an owner decision. `--record-digest` can additionally pin the
immutable recordDigest previously obtained from a draft read. Valid statuses,
including revocations and holds, are returned unchanged with exit 0; this means
retrieval succeeded, not that migration is approved. Exact source/evidence/validity,
unknown counts and candidate/status consistency are checked before output. No
signature is issued and no draft is modified. Read the
[complete review command and evidence boundary](application-owner-review.md#inspect-the-review-from-the-operator-cli)
for errors, current-authority limits and deployment prerequisites.
