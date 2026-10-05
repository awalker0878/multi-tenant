# P02 Console tenant notification consumer

Owner: Console/product engineering with Governance/IAM as fact and authorization
owner. Packages P02.02/P02.03/P02.05; requirements R03/R04, with early support for R33;
criteria G02.01/G02.03/G02.04. Implementation and verification remain IN_PROGRESS.

## Consumer scope and custody

Console now consumes five unchanged Governance v1 routes: tenant, membership,
grant change, grant revocation and quota change. Installation identity has the bounded consumer described below; approval events
remain excluded. The [published schema](../../contracts/schemas/events/governance-change-v1.json)
is copied byte-for-byte into the independent Console image; Opis validates the
body and the adapter verifies publisher, content type, routing key and message ID.
Console imports no Governance source and reads no Governance database.

The Console-owned inbox records event ID, tenant ID, type, wire digest and receipt
time. A transaction inserts the immutable receipt and changes an opaque tenant
cursor. Only its committed outcome permits broker acknowledgement. Identical
duplicates preserve the cursor. Same-ID/different-byte deliveries preserve the
original receipt and enter encrypted quarantine. Malformed bounded deliveries
also enter quarantine before acknowledgement. An unavailable database, contract
or encryption key leaves the delivery unacknowledged. A caller's outer transaction
is rejected so it cannot defer commit until after acknowledgement.

The consumer accepts at most 16 KiB per body. Truncated or oversized messages stay
unacknowledged; incomplete bytes never count as retained custody. The proposed
queue disables RabbitMQ's delivery-count discard limit, and has no TTL or automatic
pruning. This prevents repeated failures from silently exhausting a delivery limit;
it does not approve an operating retention budget. Independent custody, storage
budgets, monitoring and retained-object reconciliation remain receiving inputs.

Only an invalidation hint is projected. Events contain no external subject or
current grant, and no resource revision is applied to a page. Reordering can cause
an extra review prompt; it cannot roll back current owner state. The existing
Governance read APIs provide reconciliation under current authorization.

## Browser behavior

An unscoped tenant administrator's active page polls its Console presentation
endpoint every 15 seconds. Each request rechecks the session and the current
Governance membership before looking up the cursor. Scoped administrators,
readers, revoked members and guessed tenant IDs cannot obtain hints. The endpoint
returns only a cursor and private no-store headers, with no event IDs, actors,
timestamps, counts or event bodies.

The page takes its baseline before reading current owner values. A changed cursor
shows a review prompt and preserves all unsaved fields. Refreshing is explicit;
the button says **Discard edits and refresh** when a draft exists. Missing hint
storage shows an unavailable state while owner-backed administration remains
usable. Recovery from a missing baseline prompts review instead of implying that
the page stayed current. Poll failures back off to two minutes, requests have a
ten-second bound, hidden pages pause, and unmounted pages abort outstanding work.
Late results cannot change a different tenant page. Authorization loss reloads the
current account journey. The browser never connects to RabbitMQ.

## Deployment and qualification

See the [consumer runbook](../operations/runbooks/console-notifications.md).
Additive Console migration 002 owns the inbox, cursor and quarantine tables;
runtime privileges cannot update/delete inbox or quarantine history. Compose and
Kubernetes foundation generators now apply the ordered Console migrations.

Local feature checks cover acknowledgement ordering, rollback, uncertain-ack replay,
duplicates, conflicts, reordering, tenant isolation, malformed/encrypted custody,
oversized payloads, batch limits, current-access denial and unavailable storage.
PHP types, dependency rules, Vue types and the production frontend build are checked
separately. Real PostgreSQL, broker permission/TLS, process-boundary delivery and
compiled multi-tab refresh qualification are separate hosted campaign results;
test implementation alone is not a passing result.

The extended P02 campaign provisions the proposed queue with disposable principals,
runs Console PostgreSQL/TLS tests, and invokes the real Governance relay and Console
consumer in separate application processes. A second browser tab changes quota;
the first must see the delivered hint while retaining its member draft and original
quota, then fetch the new quota on explicit refresh. Direct hint requests from a
reader and a revoked member must be denied. Each browser engine retains separate
source bindings, command logs and results.

EV-P02-010 retains 114 passing local Console tests (520 assertions), thirteen
command logs and 134 source bindings at `283e6f4`. Six broker cases are explicitly
skipped locally. EV-P02-012 retains the Chromium campaign at that exact source:
58 checks, 105 Governance cases (1,542 assertions), 44 Console notification cases
(163 assertions), two journeys without skips/retries/failures, 284 source bindings
and nine artifact hashes. Independent application processes published and recorded
six notifications with no retries/quarantine. This is the measured product consumer;
the OIDC peer and immutable plans remain synthetic. Other engines require their
own results. See the [retained Chromium receipt](../../verification/p02/identity/run-37371273531/chromium/retrieval.json).

The first Console image build failed because the newly locked AMQP library requires
`ext-sockets`. `b13996d` compiles sockets in the image and declares the platform
requirement explicitly, using the existing pinned build inputs. No package version
or platform check was relaxed. EV-P01-032 retains the corrected seven-service
Compose replay: 249 checks, 612 verified command logs and 451 unique source bindings,
with all seven image build/process reports passing. The complete archive and
[retrieval record](../../verification/p01/local/run-37371858448/retrieval.json) retain
the exact corrected source. The original failed build remains in the
[correction record](../../verification/p02/corrections.md). Separate package,
image-security admission, Kubernetes and corrected-source browser campaigns remain
distinct requirements; a Compose pass does not replace them.

This increment does not deliver Catalogue resource guard integration, approval/plan
UI, broker HA, full-store restore or an
operated notification service. It does not pass G01/G02, approve retention, assign
an operating receiver, or establish manual accessibility/support-floor acceptance.

## Installation identity continuation

P02.01/P02.03/P02.05 now consume the unchanged identity v1 schema in Console.
Explicit bindings cover its twelve event types. The shared immutable inbox uses
one event-ID namespace; installation receipts have a null tenant. A collision with
a tenant receipt is quarantined, never overwritten. Console stores neither actor
identities nor provider configuration from these messages. Only settings-saved and
activation events change the separate installation hint. Login, password and
session/delegation receipts do not produce repeated setup prompts.

`GET /setup/notification-status` asks Governance for current setup authorization
before reading the hint. Tenant administrators and ordinary federated members have
no installation reach. Missing owner authority denies disclosure; unavailable hint
storage returns a redacted 503. Mandatory password change still precedes access.

The setup page takes its baseline before reading current settings. The shared
bounded polling component preserves fields, including a typed write-only client
secret, until explicit refresh; secrets remain excluded from remembered state and
page props. Editing the private-network field also disables testing/activation
until the draft is saved. The two-tab campaign exercises delivery, preserved drafts
and keyboard refresh; automated browser coverage does not replace manual AT review.

Migration 003 relaxes only the inbox tenant column and creates the singleton
installation hint. Existing receipts and restricted history grants remain intact.
Apply the ordered migration before starting the extended consumer. The deployed
queue must include the exact identity bindings; no wildcard or extra broker
privilege is required. Source-bound local/hosted observations must be retained
before this new increment is described as qualified.

The first installation-consumer campaign exposed a fixture defect: replaying only
Governance migration 001 revoked the later outbox delivery-column grants. The
corrected campaign replays the complete ordered migrations and retains the original
failure. Isolated-package tests compare the frozen schema digest without reading
outside their owned package; integration separately checks published/schema bytes.
