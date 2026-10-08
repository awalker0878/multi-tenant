# Qualification authority invalidation delivery (E2 engineering)

This describes implementation in PR #64, not a commissioned E3/E4 capability.
Until a receiving environment with its own verified trust boundary is enrolled,
the publisher is **disabled by missing configuration**; events remain in SQL.

## Producer custody

- The Assurance authority database migration creates append-only publication
  history, monotonic per-scope epochs and an outbox in the same transaction.
- Run `assurance:deliver-invalidations --limit=50` only in a separately
  commissioned Assurance environment with SQL authority mode enabled.
- The command uses PostgreSQL `FOR UPDATE SKIP LOCKED` and avoids delivering a
  later undelivered epoch before an earlier one for the same scope.
- An unconfirmed event remains pending. A killed process, missing acknowledgment
  or commit failure may replay the same immutable `event_id`; no speculative
  success or automatic revocation reversal is allowed.
- No recurring scheduler is enabled by this branch. Arrange controlled invocation
  and monitoring only after the receiving inbox is qualified.

## Required private configuration

| Variable | Meaning |
| --- | --- |
| `ASSURANCE_QUALIFICATION_AUTHORITY_MODE=database` | Explicitly enables durable SQL qualification authority |
| `ASSURANCE_INVALIDATION_SINK_URL` | Approved HTTPS receiving inbox endpoint |
| `ASSURANCE_INVALIDATION_CA_FILE` | Absolute path to trusted receiving TLS CA certificate |
| `ASSURANCE_INVALIDATION_CREDENTIAL_FILE` | Absolute mounted service credential; never reuse observer/reviewer or Planning authority |

The publisher rejects plain HTTP, URL user information, redirects, missing
credentials and untrusted TLS. No secret is embedded in code or repository
configuration.

## Receiving inbox protocol

Each event contains `event_id`, `scope_sha256`, `authority_epoch`,
`operation`, `state`, `decision_sha256` and `event_sha256`.
The receiver must independently authenticate the source, persist the event
and its scope/epoch before responding, and reject any conflicting reuse of an
event identity. A duplicate delivery with identical bytes may acknowledge the
original persisted event. An old or reordered scope epoch must not roll back
current negative authority or restore stale qualification.

Only after durable acceptance may it respond HTTP 200 with the exact fields:

```json
{
  "persisted": true,
  "event_id": "<same event_id>",
  "scope_sha256": "<same scope_sha256>",
  "authority_epoch": 1,
  "event_sha256": "<same event_sha256>"
}
```

The producer requires **all** fields to match and will retry otherwise.
An HTTP success or broker receipt without downstream durability is not enough.
The receiver must enforce its own tenant/scope authorization and monotonic
inbox constraints; this PR does **not** supply that receiving implementation.

## Failure operations and completion gate

Observe pending SQL rows, oldest undelivered epochs, and repeated unconfirmed
invocations; keep source-bound logs with no credential values. If downstream is
unavailable, stop dispatch and preserve the outbox and current support holds.
Never mark delivered rows manually to work around a failed receiver.

To close A10/A11 and CT-06, exercise real and reordered/duplicated/lost deliveries
against a commissioned consumer, verify that downstream Planning marks affected
plans stale, and verify Lifecycle independently rechecks current Assurance authority
at every applicable native effect. The E2 PostgreSQL workflow tests only producer
transactions and a mock receiving acknowledgment; it cannot grant E3 or E4.
