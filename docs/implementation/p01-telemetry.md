# P01 correlated diagnostic telemetry

Owners: service maintainers and SRE/security. Scope: P01.06, R29/R30/R31,
G01.06. This increment instruments the seven running foundation HTTP applications.
The selected workers still consume no tasks and perform no native operations.

## Implemented signal contract

Each application adds `X-Trace-Id`, `X-Span-Id` and `X-Telemetry-State` response
headers without changing health response bodies, authentication or readiness.
The PHP middleware uses an application-owned `SignalBuffer` contract and an
infrastructure implementation; Python composes its ASGI adapter with an injected
infrastructure writer. No sibling service source or new dependency is imported.

Only a single valid W3C version-00 `traceparent` with nonzero trace/parent IDs and
flags `00` or `01` is continued. Other versions, duplicate headers, malformed
values and zero identifiers start a fresh trace. Each request gets a new random
span ID. Caller correlation is untrusted, grants no tenant or actor identity and
does not change authorization. Baggage and tracestate are not propagated. This
deliberately limited diagnostic adapter is not a general W3C/OTLP implementation.
See [W3C Trace Context](https://www.w3.org/TR/trace-context/) for the underlying
identifier and trust rules.

The record is an allowlist: schema/event, owning service, exact source revision,
fixture environment, start time in Unix microseconds, trace/span/parent IDs,
bounded route/method, HTTP status and monotonic duration to response headers.
Arbitrary paths become `other`, unknown methods become `OTHER`. Headers, query
strings, cookies, credentials, payloads, client addresses and caller tenant IDs
are never recorded. Timing excludes body transmission and does not assert
business-operation completion.

Explicit configuration is `TELEMETRY_ENABLED=1`, a full lowercase 40-character
`SOURCE_REVISION`, and `TELEMETRY_ENVIRONMENT` equal to `development`,
`p01-compose` or `p01-kubernetes`. The two disposable runtime generators set the
latter two values. Other environments need an operating integration decision;
an invalid enabled configuration returns `unavailable`, never a fabricated
source identity. Disabled instrumentation reports `disabled`.

## Bounded collection and recovery

Each application owns a private mode-0700 `/tmp/product-telemetry` directory and
a mode-0600 JSONL file. Every record is at most 1,024 bytes; the complete buffer
is at most 65,536 bytes. Nonblocking exclusive file locks serialize writers and
the collector. Existing records are preserved when full; the response reports
`full`, `contended` or `unavailable`. Successful local acceptance reports
`buffered`, which is not remote delivery or durable retention.

The diagnostic buffer is deliberately ephemeral and contains no mandatory audit
or effect records. It does not extend authority, acknowledge jobs or enable
native writes. Product flows that require durable accountability must use their
own durable journal and hold on mandatory-record failure.

The operator collector in `scripts/p01/telemetry.py` strictly validates ownership,
revision, dimensions, types, record size, duplicate fields/spans and complete
lines before deriving structured logs, spans and response-count/latency metrics.
Metrics use only service, route, method and status-class labels. Their population
is collected responses, not all traffic; missing samples must not be counted as
zero failures. Freshness distinguishes MISSING, STALE, CLOCK_INVALID and FRESH.
The campaign's 300-second freshness window is a fixture bound, not an SLO.

Collection requires an operator with container-exec access. There is no public
telemetry endpoint or tenant-readable store. This does not establish a future
tenant dashboard authorization model. Snapshot reads are nondestructive. The
collector retains and validates the bytes before acknowledging their SHA-256;
any concurrent appended record invalidates acknowledgement and preserves the
entire buffer. Operating collection needs a receiving store, access policy,
cadence and independently accepted loss/retention budget under OP03/OP05.

## Verification and scope

Both deployed campaigns now run an authenticated operator diagnostic fan-out
with a common trace through all seven applications, compare returned span IDs
with collected records, inspect private-input canaries, deny public reads, and
compare the three signal views. This is not a service-to-service business
workflow or native attempt; those paths belong to later feature qualification.

For each language, collection stops until actual HTTP requests exhaust the real
buffer. The campaign records explicit loss, injects an unavailable filesystem,
rejects a stale acknowledgement, proves retained bytes unchanged, acknowledges
the accepted snapshot, detects missing samples and observes resumed collection.
Package tests also exercise lock contention and malformed/zero correlation.

Hosted measurements and exact source/artifact bindings will be recorded here
after the campaigns finish. Existing synthetic HTTPS alert delivery/acknowledgment
remains a separate measured boundary. The real receiver, operational custody,
review-role activation and accountable G01 decision are still required by
[the operating inputs](../../release/operating-inputs.json) and
[the G01 assessment](../qualification/gate-reviews/g01-engineering-assessment-2026-10-05.md).
