# P08 native control and movement-budget qualification

Source `f765eb9fba61a16565d4085d8e51a4e0ec681ddd` passes all 36 component
commands and **951 tests without skips**: Inventory 112, Planning 170, Lifecycle
349, Lifecycle-worker 258 and Inventory-worker 62. The real Planning compiler and
native resolver agree across all 30 explicit method/mode combinations. Three
migration browser journeys pass all five browser commands without retries or skips.

The separate Governance campaign at `576643e3102ab02a8fd0fc23edd2f2e90d2ec74e`
passes **219 PostgreSQL tests with 5,919 assertions**, 160 campaign checks and both
Chromium journeys. Its complete service tree and native approval contract are
identical at the final component source. This is separate evidence with its original
source identity; it is not relabeled as a run against the final source.

The [verified index](qualification-index.json) retains the original component,
browser and Governance archives, command logs, source bindings and test reports.
Reproduce the evidence checks from a checkout containing the original commits:

```bash
python scripts/p08/verify_control_retained.py
```

The verifier checks 943 component and 231 browser source bindings against their
exact Git source, plus 474 Governance source bindings and 25 Governance artifact
digests. The [migration screenshot](migration-fleet.png) is retained unchanged
from the browser archive and was visually inspected. Its VM names and native
profiles are synthetic; no real workload appears in these checks.

| Surface | Verified behavior | Limit |
| --- | --- | --- |
| Native control | Separate TLS Lifecycle process/dispatcher, protected owner assignments, tenant-scoped worker selection and current credential/configuration checks | Commissioned owner endpoints and runtime deployment still required |
| Immutable resolution | Real Planning compiler output, exact binding/content/recipe/custody digests, live approval, all-dataset Inventory checks and minimum expiry | Custody and observation responses use synthetic peers |
| Approval | Current requester, reviewer and executor memberships, independent operational approval, exact plan, expiry/revocation denials and consent-only receipt | Approval alone never grants a native effect |
| Inventory | Exact current review scope, protected multi-review grants, revocation/expiry and credential separation | No new platform account is commissioned |
| Planning | Recipe revocation checked on unattended execution and Governance binding reads | No mounted recipe is native support evidence |
| Movement | Version 2 budgets up to one day within current authority; preserved version 1 limits, bounded converter CPU, expiry checks and Temporal replay patch behavior | Does not implement interrupted NFC/Glance byte-range resumption |

## Correction and regression

The [original architecture failure](context-policy-original-failure.log) and
[correction record](correction.json) preserve the first failed run. The owner
infrastructure imported immutable-plan validation from an HTTP interface. The
correction moves that canonical function to the domain layer and updates every
caller. The unchanged Context policy passes in run `37684992982`; no validator
was relaxed.

[Regression status](regression-status.json) records the exact observed outcomes
for both source revisions. Pending and running regressions remain labeled as such.
The new contracts pass the frozen-contract gate. Original earlier P08 evidence is
unchanged and remains available alongside this increment.

## Native completion boundary

The [native control instructions](../../../docs/implementation/p08-native-control.md)
describe the delivered interfaces and protected configuration. P08 remains incomplete.
Provider custody/fencing, actual account commissioning, physical measurements, the
selected guest/data/service/recovery/cleanup implementations and interrupted-transfer
reconciliation remain outstanding. No native G07 entry, Q05/Q06/Q07 observations or
G08 receiving decisions are supplied by these E2 checks. Neither blocker is closed.
