# P08 source fleet and bulk preparation qualification

The [verified index](qualification-index.json) retains the original hosted archives,
exact source bindings, command logs and browser artifacts. Run
`python scripts/p08/verify_fleet_retained.py` with the recorded Git objects present.
Earlier [profile qualification](../profiles/README.md) remains unchanged.

Source `74ab8e41e2d1da90bb47f1b2794c9c7bf3778d66` passes all 35 component commands
and 785 tests without failures or skips: Inventory 96, Planning 119, Lifecycle 304,
Lifecycle-worker 204 and Inventory-worker 62. Both actual Vue/Inertia browser
journeys pass all five quality commands, with no skips, retries or flaky results.
The independent Console package passes all 23 commands, including Pint, Larastan,
architecture, build and 187 Pest tests with 894 assertions. Its seven broker tests
are explicitly skipped because they require the separate verified-TLS campaign;
those skips are not counted as passes. The index verifies 682 component, 218 browser
and 295 Console source bindings plus every reported command log and artifact hash.

| Surface | Measured behavior | Boundary |
| --- | --- | --- |
| Fleet API | Scoped VMware resource listing, complete-generation identity, current authority, missing/stale profile holds and 60-machine pagination | Real PostgreSQL; synthetic native/authority peers |
| Saved groups | Immutable membership, exact replay, revision conflicts, tenant isolation, changed-source identity and append-only SQL | Up to 50 VMs per group; 100 groups and 50 target profiles per site |
| Independent reviews | Separate VM confirmations, unaffected neighbouring VM, superseded-source denial and exact disk mappings | Preparation requires current confirmed source and target profiles |
| Console controller | API refresh, server-owned member/disk facts, revision/digest checks, UUID5 resource IDs, CSRF, actor delegation and forged-response denial | Laravel tests use synthetic owner services |
| Browser | Search, readiness filters, grouping, selection across pages, named groups, mixed prepared/held results, stale group and access loss | Actual Vue/Inertia UI with isolated HTTP fixtures; no real operator or assistive review |
| Contracts | Additive Inventory v1.3, retained v1.2 operations/schemas and older contract bytes, generated clients and Planning schema parity | Unsafe extra fields and oversized membership are rejected |

The [fleet screenshot](migration-fleet.png) is copied byte-for-byte from the final
browser archive and visually inspected. It is synthetic test data, including an
escaped hostile VM name used to check safe text rendering.

## Original failures and corrections

- Component run `37639180297` at `4d9984b` records 95 Inventory passes and one failure.
  The new negative test expected `invalid_shape`; the strict parser correctly
  returned `unknown_field` for an injected field. The correction checks that exact
  rejection. Validation was not relaxed.
- The same run passes the existing migration review journey but times out locating
  the fleet source selector. The correction gives the select the explicit accessible
  name `Source connection` and makes the test fixture module extension explicit.
  The original trace, screenshot and failed report remain retained.
- Console run `37639180323` passes its functional tests but fails Pint import order
  and Larastan's generic type inference for `collect()` over the validated response.
  The correction sorts the imports and uses a typed member lookup loop. No quality
  rule is disabled. Final run `37640141936` passes.
- Commit `74ab8e4` contains these corrections. P08 run `37640141788` passes both
  component and browser jobs. Original failures remain failed in the index.
- Local Inventory results contain database skips, and local PHP/Chromium are
  unavailable. The hosted campaigns above provide the required PostgreSQL,
  Laravel and actual browser observations.

## Remaining scope

Bulk preparation rechecks each saved member and calls Planning. It does not compose,
approve or execute a complete native migration plan. Installed VMware/OpenStack,
converter/copied-guest qualification, owner/trust/stage composition, native Q07 and
G07/G08 receiving remain required. No machine was migrated by this qualification.

The existing native REST collector holds lists over 100 machines, and detailed
profiles use an enrolled allowlist of at most 32 VMs per connection. The GUI pages
the available inventory in 50-row pages; it neither expands source permissions nor
hides those collection limits. See the [implementation record](../../../docs/implementation/p08-execution.md)
and [runbook](../../../docs/operations/runbooks/native-migration.md).
