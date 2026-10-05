# Console tenant notification delivery

Owner: Console/product engineering; production custody and alert recipients require
the operating input record. This is a bounded implementation runbook, not an
operated deployment or receiving approval. See the [implementation](../../implementation/p02-console-notifications.md).

## Provision and run

1. Apply Console migrations 001 then 002 as `console_migrator`. Retain the Console
   database and its application encryption key under the approved custody process.
   Migration replay does not clear existing inbox, cursor or quarantine rows.
2. Review and import the additive [broker definitions](../../../deploy/dependencies/stateful/console-notifications.json)
   with provisioning authority after creating independently held `governance` and
   `console` principals. These definitions contain no credentials. Inspect existing
   vhost permissions before import; do not overwrite another deployment's reviewed
   grants indiscriminately. Console may read only `console.governance`; it cannot
   publish or configure queues. Bind the five exact v1 routes before publishing.
3. Supply `CONSOLE_BROKER_HOST`, `CONSOLE_BROKER_PORT` (5671 by default),
   `CONSOLE_BROKER_PASSWORD_FILE` and `CONSOLE_BROKER_CA_FILE` to the Console command
   worker. Use verified TLS and a matching broker hostname. There are no default
   credentials, plaintext fallback or browser broker credentials.
4. Run `php artisan console:consume-notifications --limit=100`. Accepted limits are
   1–500. When a broker host is configured, the Laravel scheduler invokes a bounded
   batch every minute, with overlap/single-server locks in the shared cache. The
   deployment must actually run its scheduler; an HTTP replica alone does not
   consume events. The disposable browser campaign invokes the same commands more
   frequently to observe the complete path.
5. Inspect aggregate `recorded`, `duplicate` and `quarantined` counts and the exit
   status. A nonzero exit reports unavailable delivery without reflecting payloads,
   credentials or connection diagnostics. Provision monitoring for failures,
   quarantine growth, retained bytes and backlog/age through the actual receiving
   route once its owner and budgets are supplied. A zero exit on an empty queue is
   not a freshness or business-authority statement.

## Recover without manufacturing state

A connection loss after commit can redeliver the same message. Restart the bounded
consumer after repairing the connection; the inbox digest makes unchanged replay
idempotent. A failed database transaction rolls back its receipt and hint; the
broker retains the unacknowledged message. Recover storage before retrying.

Same-ID/different-byte and malformed bounded deliveries are stored encrypted with
their complete envelope and sanitized reason. Do not rewrite the original inbox,
turn the quarantine into a permission, or deserialize untrusted envelopes into
objects. Investigation uses the retained digest, approved custody and Governance's
audit/outbox reconciliation. No automatic quarantine deletion or reprocessing
command is provided.

For oversized/truncated messages, stop repeated consumers and investigate through
the authorized broker custodian. Preserve the **complete** original body and
properties before any destructive broker action. The supplied queue uses
`x-delivery-limit: -1`, no TTL and no automatic pruning; do not replace this with a
finite discard limit unless an independently verified durable custody path exists.
Changing an existing queue's arguments can require migration: inspect and plan it,
never delete/recreate a live queue as an installation shortcut. Capacity/retention
and alert policy still require operating decisions.

Refresh the authorized owner page after reconnect or restore. A cursor never
proves current membership, quota revision, plan approval, freshness or permission.
Do not reconstruct grants from notifications or revive retired identities. Full
broker/database/key restore consistency and independent revocation custody remain
unqualified; retained development evidence does not close those conditions.

Protocol references: [RabbitMQ acknowledgements](https://www.rabbitmq.com/docs/confirms),
[access control](https://www.rabbitmq.com/docs/access-control) and
[quorum poison-message handling](https://www.rabbitmq.com/docs/quorum-queues#poison-message-handling).

## Installation settings notifications

Apply Console migration 003 before enabling the extended bindings in
`deploy/dependencies/stateful/console-notifications.json`. Run both Governance
outbox commands and the existing Console consumer. The twelve explicit identity
routes share the durable queue and immutable inbox; installation rows have no
tenant ID. No additional configure, write or cross-queue read grant is needed.
The two setup-change types invalidate the installation hint. An installation
administrator can review current settings through the owner-authorized setup page;
a notification cannot activate a provider, restore a password or confer a grant.
