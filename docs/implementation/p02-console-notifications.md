# P02 Console tenant notification consumer

Owner: Console/product engineering with Governance/IAM as fact and authorization
owner. Packages P02.02/P02.03/P02.05; requirements R03/R04/R14/R32;
criteria G02.02/G02.03/G02.04. Implementation and verification remain IN_PROGRESS.

## Consumer scope and custody

Console now consumes five unchanged Governance v1 routes: tenant, membership,
grant change, grant revocation and quota change. Installation identity and approval
events are excluded. The [published schema](../../contracts/schemas/events/governance-change-v1.json)
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

This increment does not deliver an installation-identity consumer, Catalogue
resource guard integration, approval/plan UI, broker HA, full-store restore or an
operated notification service. It does not pass G01/G02, approve retention, assign
an operating receiver, or establish manual accessibility/support-floor acceptance.
