# G04 engineering assessment — 2026-10-06

This is Codex's examination of source `6b21490af3a9b0fbd5ce288bfbca8f82c790d6d9`
and original engineering measurements retained at `91ee1152ccd723857056aa32cf2217a5d87608fb`. It is not an independent G04 receiving decision. The canonical gate
requires native E3 observations; no actual OpenStack or VMware installation has
been accessed or qualified by this work.

| Criterion | Engineering result | Formal acceptance boundary |
| --- | --- | --- |
| G04.01 | Restricted GET adapters, complete eleven-dimension profile contracts, stable identity and explicit VMware/AHV limits are implemented and exercised with synthetic native TLS peers. | Selected installed OpenStack/VMware tuples and read-only Q02 evidence are absent. |
| G04.02 | Tenant/site/workload/actor separation, explicit outbound trust, partial/expired/reused identity holds and current revocation are covered by PostgreSQL, real service and hostile-input tests. | Actual permission-visibility and native negative cases plus independent security review are required. |
| G04.03 | Durable scheduling, per-authority/per-tenant budgets, fairness, bounded retries, backlog pressure and restart are implemented. No incomplete generation establishes readiness. | Native approved-budget/load/disconnection observations and SRE/Inventory review remain. |
| G04.04 | Observations never grant ownership/reservations, collisions hold further matching, immutable facts survive uncertain delivery, and the independent synthetic peer records no state change. | Actual independent native before/after observations and ownership review remain. |

The [check matrix](../../../verification/p04/check-matrix.md) maps executable
boundaries; the [corrections record](../../../verification/p04/corrections.md)
retains failures. The [completion packet](../../implementation/p04-completion-review.md)
names concrete native inputs, steps and receiving roles. Final qualification passes all 99 core/worker tests and all three live 60-check campaigns, with no skipped or failed hosted cases. Twenty local quality commands pass with their database-only skips explicit. Campaign identities and exact-source results are recorded in EV-P04-001–003 and the qualification index.

BL-P04-001/002 remain open and G04 remains NOT_REVIEWED. Package and phase work
cannot be marked COMPLETE while their required native and receiving evidence is
missing. No actual reviewer identity, observed native fact or gate decision is
invented. The user has already authorized development; these are missing facts and
reviews, not a request to repeat that authorization.

The [regression completion receipt](../../../verification/p04/final/regression-completion.json)
records the passing final runtime-source Kubernetes campaign and affected
foundation/identity/Catalogue regressions with explicit source-impact boundaries.
Those engineering checks are complete; actual native E3 and designated receiving
reviews remain the outstanding P04 completion work.
