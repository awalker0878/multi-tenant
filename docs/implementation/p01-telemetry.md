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

Each application owns a private `/tmp/product-telemetry` directory with effective
access mode 0700 and a mode-0600 JSONL file. Kubernetes `fsGroup` inheritance adds
the setgid bit (observed directory mode 02700) without granting group access.
Every record is at most 1,024 bytes; the complete buffer
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

## Retained hosted measurements

Both campaigns pass at source
[`36a14811b5afa23717566d5e8a08632e011f44a5`](https://github.com/awalker0878/multi-tenant/commit/36a14811b5afa23717566d5e8a08632e011f44a5).
EV-P01-029/030 retain the complete archives, identical report copies and verified
source/log bindings at evidence commit
[`61a972cba5eba4e09bb5f806f6d67d1af29c6373`](https://github.com/awalker0878/multi-tenant/commit/61a972cba5eba4e09bb5f806f6d67d1af29c6373).

| Observation | Compose | Kubernetes |
| --- | --- | --- |
| Retained report | [Run 37278731868](../../verification/p01/local/run-37278731868/report.json) | [Run 37278731990](../../verification/p01/kubernetes/run-37278731990/report.json) |
| Passing campaign checks | 249, including 70 telemetry checks | 266, including 70 telemetry checks |
| Retained telemetry | 22 snapshots and three signal export files | 22 snapshots and three signal export files |
| Collected journey population | 21 records, 21 spans, 21 metric series | 30 records, 30 spans, 21 metric series |
| Independently verified bindings | 324 source bindings; 610 command logs | 310 source bindings; 1,052 command logs |
| Resource observations | 30 samples across 15 containers | 30 samples across 15 containers |
| Cleanup | Complete | Complete |

Seven authorized diagnostic spans match the common caller trace. The retained
records also include seven public-reader denials on that trace and seven
malformed-trace authentication denials on fresh traces; Kubernetes adds nine
concurrent readiness records on other traces. The campaign matches each diagnostic
response's trace/span to its collected record; it does not require an exclusive
request population. All three exported views agree on
the collected population, and each campaign reports FRESH at collection time.
Both languages pass actual buffer exhaustion, explicit loss and unavailable
storage, stale-acknowledgment preservation, missing-span detection and resumed
collection. A changed snapshot is retained and recollected before any bounded
acknowledgment retry; concurrent writes cannot authorize clearing unseen bytes.

Two failed Kubernetes runs remain unmodified:

- [Run 37277023414](../../verification/p01/telemetry/initial-kubernetes-failure/report.json),
  source `6c2201c7ba3ec04eebac35d84c00d2632e4aafaf`, rejected the inherited setgid
  bit despite private 0700 access. The correction checks effective access bits
  and records the complete observed mode.
- [Run 37277893777](../../verification/p01/telemetry/concurrent-probe-failure/report.json),
  source `5502f1f1e6a01110cb8c16b22a147dd9552f7681`, failed an exact record-count
  assertion when readiness probes appended concurrently. The final source uses
  exact request/span membership and preserves the stale-acknowledgment boundary.

EV-P01-028 also retains [all nine passing package results](../../verification/p01/telemetry/packages/36a14811b5afa23717566d5e8a08632e011f44a5/report.json)
and [current artifact admission](../../verification/p01/artifact-trust/run-37278732015/retrieval.json).
EV-P01-031 retains [affected HTTP, Permit Desk and policy requalification](../../verification/p01/requalification/36a14811b5afa23717566d5e8a08632e011f44a5/report.json).

Existing synthetic HTTPS alert delivery/acknowledgment remains a separate measured
boundary. These local buffers and retained exports do not establish an operating
receiver, durable custody, a native attempt or an accepted loss/retention budget.
The real receiver, operational custody, review-role activation and accountable
G01 decision are still required by
[the operating inputs](../../release/operating-inputs.json) and
[the G01 assessment](../qualification/gate-reviews/g01-engineering-assessment-2026-10-05.md).
