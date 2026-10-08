# P08 runtime and complete-proposal qualification

Source `7860616293cc0be7a1983ca7bc38529aed5e5b7f` passes all 35 component
commands and **893 tests without skips**: Inventory 96, Planning 169, Lifecycle 332,
Lifecycle-worker 234 and Inventory-worker 62. The three actual Vue/Inertia journeys
pass all five browser quality commands with no skips, retries or flaky results.
The same source passes all 23 Console quality commands, with **195 Pest tests and
922 assertions**. Seven explicitly separate broker-campaign tests remain skipped.

The [verified index](qualification-index.json) retains the original hosted archives,
source bindings, command logs, JUnit counts and browser observations. Run:

```bash
python scripts/p08/verify_campaign_retained.py \
  --directory verification/p08/runtime --screenshot migration-fleet.png
```

The verifier checks 719 component and 230 browser source bindings against the exact
Git source and 305 Console source bindings, plus archive/log/artifact digests.
The [fleet screenshot](migration-fleet.png)
is copied unchanged from the browser archive and visually inspected. The hostile VM
name is synthetic test data rendered as text. Earlier P08 evidence and its original
failures remain intact.

The first implementation source `d7d350befb4aab531dd2dfa79a23996e5441c5ff`
also passed these component/browser checks and all 23 Console quality commands,
including 194 Pest tests and 920 assertions. Seven separate broker-campaign tests
were explicitly skipped. Its original archives and
[first screenshot](migration-fleet-first.png) remain retained. No earlier result
is relabeled as the latest source's run.

## Corrections and regression boundaries

[Correction records](corrections.json) retain the original failures and exact bytes:

- The first image run `37673681072` rejected two executable entry points absent
  from the worker's component manifest. Commit `2b0d25a` declares both commands;
  the unchanged image gate passes in run `37674739551`.
- Console package runs `37674739577` and `37674971088` timed out during browser
  dependency installation after 300 seconds with exit 124. Their apt logs show
  the Ubuntu mirror stalling. The original archives, all 15 attempted commands
  and exact source bindings are retained. Neither reached Pest or counts as a pass.
- Commit `8494cba` added explicit held responses to an already published migration
  v1.1 contract. The immutable-version check correctly failed in run `37674971112`.
  Commit `7860616` restores v1.1 byte for byte and adds v1.2 for the new responses.
  Its immediate-parent comparison also fails, since the parent contains the
  incorrect edit. The [accepted-baseline comparison](restored-contract-compatibility.json)
  verifies compatibility with `2b0d25a` and the restored frozen versions. No
  validator was relaxed and neither failed run is described as passing.
- The strict hosted contract gate passes at evidence commit `0a2d1cf` in run
  `37676737472`. Its retained archive verifies all 24 command logs and 79 exact
  source bindings, with no changed frozen contract, deterministic generation and
  passing cross-language conformance. The product contract bytes are unchanged
  from the restored `7860616` source.

The [regression status](regression-status.json) records 12 passing source workflows,
the separately corrected contract result and all six passing evidence-publication
workflows. Source Kubernetes integration is still queued behind earlier branch runs
at that observation. It is not counted as a pass. Product, contract and deployment
tree identities are unchanged between the qualified source and evidence publication.

| Surface | Verified behavior | Boundary |
| --- | --- | --- |
| Accounts | Scoped six-account identity/permission checks; distinct identities and secrets; changed/expired manifests, wrong project, excessive roles and missing/forbidden privilege denials | Protected files with synthetic API responses; no real native account configured |
| Worker | Executable TLS composition, fixed adapter registry, immutable intent/scope/custody checks and in-flight commissioning revocation | Real TLS protocol fixtures and existing native components; no actual application/guest/service implementation inferred |
| Planning | All 30 explicit method/mode stage sets, current base/review/recipe binding, minimum expiry, full disk budgets, durable exact retry/outbox, current recipe/profile revalidation and wire-schema agreement | Real PostgreSQL with synthetic qualified owners; complete proposal supplies no native write authority |
| Bulk Console | Server-derived member mappings, current group checks, scoped plan choices, explicit selection, uncertain-command preservation and review links | Actual Vue/Inertia browser and Laravel tests; native campaign dispatch still needs its owner/resolver composition |
| VM custody | Separate VMs may share an application; duplicate source identity or shared custody remains held; older retained application-keyed jobs recover without losing their hold | Real PostgreSQL admission/recovery controls with synthetic native owners |

The commissioning instructions are in the
[runtime record](../../../docs/implementation/p08-runtime-commissioning.md).
Local PostgreSQL/browser attempts were unavailable because the workspace lacked
those binaries; they are not counted as passes. The original hosted archives above
contain the completed checks with the required dependencies.

P08 remains incomplete. Native current-owner/approval/custody and execution-plan
resolver integration, actual performance/capacity producers, the selected copied-guest,
delta/service/traffic/recovery/cleanup protocols, converter qualification and safe
large-transfer continuation remain open. Actual commissioned environments, a qualified
G07 entry path, Q07 observations and G08 receiving decisions have not been supplied.
These E2 results establish none of those native outcomes.
