# P03 invariant and recovery coverage

This matrix maps the implemented Catalogue slice to Q01. Actual run identities,
results, source and retained-byte verification belong to the qualification index.
An automated observation does not replace the representative-user review in G03.04.

| Q01 / G03 | Boundary and observations | Executable source |
| --- | --- | --- |
| Q01.01 / G03.01 | Catalogue 1.0.1 specification validation; generated PHP, Python and TypeScript descriptors; PHP response-schema validation and independent Python wire/event validation. Unknown properties and invalid types fail. | `scripts/p03/generate_clients.py`, `verify_live.py`; Console `CatalogueWorkspaceTest`; Catalogue `IntentDocumentTest`. |
| Q01.02–03 / G03.02 | Tenant/resource/environment-scoped delegation, wrong audience and caller rejection, current owner membership, foreign application and cursor rejection. Application authors cannot administer reference definitions; tenant administrators receive no implicit application-author grant. | Catalogue `DelegatedAdmissionTest`; Governance `CatalogueOwnersTest`; live owner/foreign-tenant checks; Console denied-delegation regression. |
| Q01.04 / G03.01–02 | Complete deployment snapshots, immutable reference versions, application-owned workload IDs, one deployment identity per application/environment, explicit same-tenant sharing, retirement and immutable reference identity. | Catalogue `CataloguePersistenceTest`, controlled SQL migration `002_catalogue.sql`; live multi-WSD intent and second-deployment checks. |
| Q01.04, Q01.14 / G03.02 | Strict field allowlists; duplicate identities, ordinary NIC/domain mismatch, invalid device order/boot count, dangling dataset/service/dependency, self-edge, separate startup/shutdown cycles and uncontrolled cross-domain communication are rejected. Bidirectional communication is valid. ZIP cannot be a placement zone. Unsupported required controls and typed values survive; integers beyond the interoperable range are rejected. | Catalogue `IntentDocumentTest`; `contracts/schemas/catalogue/intent-v1.json`; live invalid-wire checks. |
| Q01.05 / G03.03 | Original receipt after later edits, changed-key-payload conflict, missing/stale ETag rejection. Concurrent distinct requests produce one accepted revision and one stale response; concurrent identical requests return one immutable receipt. | Catalogue `CataloguePersistenceTest`; independent concurrent HTTP workers in `verify_live.py`. |
| Q01.06 / G03.03 | Outbox INSERT denial rolls back application, workload, revision, receipt and audit writes. Runtime cannot delete immutable history. Publication cannot overtake an older pending fact for its aggregate. | Catalogue `CataloguePersistenceTest`, `PublishCatalogueEvent`; controlled PostgreSQL roles and authoritative count checks. |
| Q01.06, Q01.09 / G03.03 | Real TLS broker outage retains facts; producer cannot consume its destination. Successful broker publication followed by an injected pre-commit exception produces a replay with the same event ID. Independent observer sees 11 deliveries for 10 unique facts in aggregate order. Catalogue process restart preserves original receipt and revision history. | `verify_live.py`, `broker_process.php`, `live_fixture.py`; broker and database observations. |
| Q01.08, Q01.13 / G03.02, G03.04 | Current authority is checked before duplicate receipt/history access. Revoked editor writes redirect, encrypted page history is invalidated, Back does not restore protected fields, and foreign tenant navigation returns to the account page. | Catalogue revoked-authority case; Console `CatalogueWorkspaceTest`; `tests/browser-p03/catalogue.spec.ts`. |
| Q01.10, Q01.14 / G03.01, G03.04 | Import error retains exact draft and focuses its alert; structured edit and imported stale draft preserve values; explicit current-version review precedes retry; immutable comparison shows changed values. A real accepted response is lost at the private TLS proxy; unchanged retry returns revision 4 and history contains exactly four revisions. | Compiled Console journey plus independent PostgreSQL counts in `verify_live.py`. |
| Q01.12 / G03.04 | Real Console CSRF middleware rejects application/reference writes; the live journey uses actual database-backed browser sessions and owner endpoints. | Console `CatalogueWorkspaceTest`; P02 identity regression retains the broader browser/session baseline. |
| Q01.15 / G03.03 | Four accepted browser revision facts are delivered after the author is revoked, with their original author ID and sequences 1–4; revocation prevents another command. Audit/outbox identities pair exactly. | Post-browser publisher and independent broker observer in `verify_live.py`. |
| Q01.16 / G03.04 | A 501-row core fixture requires one local SQL list query and 50 returned entries; scope-bound cursors reject another tenant. Live metadata skew has 10,001 and 1,001 applications, disjoint pages, captured EXPLAIN ANALYZE and payload size. Statement/lock deadlines are read back from PostgreSQL. | Catalogue `CataloguePersistenceTest`; live `application-page-plan.json` and report `scale`. |

The initial budgets are bounded inputs/outputs rather than production throughput
promises: 256 KiB intent, 100 workloads, 200 datasets, 500 dependency edges,
100 services, 100 deployment streams per application and 50 list/history/reference
entries per page. The large-tenant fixture measures metadata skew, not maximum-size
intent for every application or an operating memory/SLO acceptance. Eloquent lazy
loading is disabled globally; current list/detail reads use explicit Query Builder
fields rather than relation traversal. Future relations must retain that protection.

The independent broker observer is a qualification consumer. The actual Planning
product consumer and its inbox/projection semantics remain P05 work. Search,
export, jobs, native placement and native effects are outside this P03 surface;
their later entry paths require their own Q01 checks.

Automated keyboard focus and zoom/reflow checks run in all three browser engines.
Actual browser/OS/policy/assistive combinations, operator comprehension and the
independent criterion decision remain in the [completion review](../../docs/implementation/p03-completion-review.md).
