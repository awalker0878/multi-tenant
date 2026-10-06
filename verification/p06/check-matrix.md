# P06 verification map

The [qualification index](final/qualification-index.json) binds actual source,
original archives, reports and observations. Tests below are E1/E2 simulation;
none supplies native E3 or designated G06 receiving acceptance. A skipped local
PostgreSQL case is never counted as a persistence pass.

| Gate / campaign | Executed boundary | Evidence location |
| --- | --- | --- |
| G06.01 / Q04.01 | Concurrent identical admissions, conflicting payload, immutable history and one dispatch row; accepted admission reply loss and unchanged recovery; actual Temporal start reply loss and original workflow recovery. | Core `execution.xml`; live `report.json`, admission checks, `p06-lost-temporal-start-response.log`, `p06-recover-original-temporal-start.log`, `execution-observations.json`. |
| G06.01 / Q01/Q03 | Actual Catalogue/Inventory facts and Planning consumer, immutable approved plans, four action graphs, Lifecycle execution, Assurance and compiled Console. Provision, recover and retire complete; migrate reaches an accepted target write and exercises safe cancellation. | Each live report, owner HTTP logs, broker observations, job/evidence browser JSON and execution observations. |
| G06.02 / Q04.04–05 | Epoch, expired grant, wrong worker, revoked approval, stop, unavailable owner, changed input/scope, lost field hold, conflicting admission, unsupported operational lane and wrong tenant. Current Governance separately rechecks executor, requester and reviewer; committed custody survives executor revocation. | Core boundary cases; Governance `ApprovalTest`; live revoked-executor denial and custody observations. |
| G06.03 / Q04.02–03 | Five important effect boundaries on both sides of acceptance; independent sealed absent/present observations, no delayed arrival after absence, no duplicate accepted operation and no resource release. Real processes die before acceptance and after target activation. | Core effect-boundary matrix; live crash/reconciliation logs and journal observations. |
| G06.03 / Q04.06 | Real refused journal connection while simulator remains available; owner partition and lost acknowledgement; actual workflow worker/server restart; evidence outage prevents completion; retained P05 confirmed broker replay keeps one fact identity. | Core connection/partition cases; live restart logs, evidence-pending checks, broker observations and `temporal-replay.json`. |
| G06.03–04 / Q04.07 | Pause, cancel and stop during reserve, reviewed apply and activation, both before and after acceptance; no prohibited new redemption. Console stale controls, uncertain command receipt recovery, cancellation and revoked history. | Core operator-control matrix; `p06-browser.json`, operator journal events and final independent observations. |
| G06.04 / Q04.08 | Restore actual pre-effect Lifecycle dump after accepted effects; independently rotate epoch, keep simulator acceptance, deny old worker and grant, retain holds and refuse invented completion. | `p06-restore-older-journal.log`, `p06-restored-worker-denied.log`, `restore-observations.json`, `final-projection.json`. |
| G06.04 / Q04.09 | Upload/finalize digest and immutable source binding; separate direct observer; append-only runtime grants; upload/persisted tamper and foreign-tenant denial; exact custody response contracts; simulation-only independent review. | Core missing-custody case; live report, Assurance logs and `execution-observations.json`; `p06-evidence-browser.json`. |
| G06.04 / Q04.10 | Durable hold alert outbox, independent TLS receiver, stable event acknowledgement and actual receipt; attributable stop/reconcile requests. | `alert-receipts.json`, live report and job event timelines. |

The restore test establishes safe denial after an older journal is restored; it
does not claim a qualified re-enable operation. No automatic epoch rebind, native
state recovery, release, or source-return adapter is shipped. Full native fault
campaigns require later exact-tuple authorization and independent observers.

Use [corrections](corrections.md) for retained failed observations, and the
[receiving packet](../../docs/implementation/p06-completion-review.md) for the
remaining named reviewer and representative operator tasks.

The [regression completion receipt](final/regression-completion.json) records all
15 associated workflow passes, with exact-source or explicit unchanged-input
comparisons. It includes final-source package, image, Compose and Kubernetes
checks and the carried P02–P05 regression boundaries.
