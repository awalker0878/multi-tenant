# P09 completion and publication review

P09 remains IN_PROGRESS; G09 remains NOT_REVIEWED. This packet identifies the
concrete publication step, unexecuted qualification and remaining exact-tuple work.

## Published development work

The user approved public publication and selected
`greenfield/enterprise-microservices-plan`. All nine P09 commits were published
there, ending at `f7001d3e75cffa13b28701f184c076a1bd1854af`. The published tree
matches the prepared local tree exactly; the original local branch is preserved.

The full PostgreSQL-backed P09 campaign passed at that source in
[run 37697578952](https://github.com/awalker0878/multi-tenant/actions/runs/37697578952).
It also passed with the P07/P08 product-control changes at `58807949bca43c46bbee77bd3fda382f983351a5`
in [run 37699712413](https://github.com/awalker0878/multi-tenant/actions/runs/37699712413).
The original local skips below are historical observations, not current unexecuted
component cases. BL-P09-001 is resolved. Actual tuple qualification and receiving
acceptance remain open.

## Reviewable local verification

The [retained evidence](../../verification/p09/local/README.md) binds the actual
component checks to `86fb17a7154caa23dd4f67728bc6b068f518d111`, with campaign-order
correction `1a9fd01f23a40f148467eacefffb0befadb5469d`. Every component source hash
matches. The original artifacts are in local commit
`eca275f98c7aca9774d4a20b2174a7c017c878ce`.

| Check | Observed result |
| --- | --- |
| Planning | 303 passed; 5 PostgreSQL cases skipped |
| Lifecycle | 301 passed; 59 PostgreSQL cases skipped |
| Native worker | 277 passed; 15 PostgreSQL cases skipped |
| All three components | Locked installs, lint, format, strict typing and wheel builds passed |
| Schema / architecture | Schema passed; original generated-build-copy architecture failure retained and corrected without weakening the gate |
| Original local P09 / native qualification | Incomplete locally / not executed; full hosted component conformance subsequently passed above |

Publishing alone will not complete P09. The workflow must run and the selected
integration and actual native/receiving obligations below must also be fulfilled.

## Remaining work and inputs

| Blocker | Owner | Unblock condition and next executable work |
| --- | --- | --- |
| BL-P09-001: complete verification/publication | Requesting user and quality | RESOLVED: approved publication to the selected greenfield branch and passing full hosted PostgreSQL conformance. Original local limitations remain in their historical evidence. |
| BL-P09-002: exact tranche and selected integrations | Product/architecture, platform, service and SRE owners | Select actual source/target instances, API/backend/network/storage/guest versions and operations. Supply API-observed profile revisions, owner-only constraints, selected service/HA/patch/rotation/scaling protocols, native exclusion and independent readback. Implement/compose those selected effects and dispatcher/worker boundary connections; qualify them against the common controls. |
| BL-P09-003: native and receiving qualification | Platform/security/qualification owners and independent observers | Supply scoped lab authority, actual read/write identities and custody, accepted impact budgets, guest/data/recovery objectives and receiving reviewers. Execute Q02/Q04–Q08/Q10 obligations for every advertised tuple; retain positive, denied, drift, response-loss, recovery, pause/stop and upgrade outcomes. Record real G09 decisions. |

Generic operation contracts do not implement an unselected installation's HA,
network-policy realization, patching, credential rotation or service recovery.
The five implemented VMware/AHV lifecycle operations also need native evidence.
The complete R26 obligation remains six separately qualified cross-platform
directions plus any selected same-family topologies, rather than just a passing
schema or one export/import path.

## Required receiving checks

1. Product/architecture freeze the exact tranche and exclusions. Bind every selected
   operation and route to a release, adapter digest, constraints and all eleven
   platform profile dimensions. Review every deferred row explicitly.
2. Platform/security owners run each direction/guest/method independently, including
   native policy denials, all disks/NICs, firmware/drivers, encryption, application
   consistency, both recovery boundaries and measured outage/data loss.
3. Inventory/lifecycle and the independent observer run no-change import, collisions,
   competing writers, drift, uncertain transfer, restore/reconciliation and detach
   in a brownfield lab. Verify exclusion at the native request boundary.
4. SRE/quality measure shared endpoint/tenant/correlated-failure budgets and fairness;
   stop queued, active and uncertain work; restore the journal and prove old workers
   cannot mutate; exercise selected HA/day-two effects and adapter transitions.
5. Record the actual observer/reviewer identities, source/artifact/environment
   fingerprints, dates, limitations and decisions. Update the canonical register
   and support publication only from accepted evidence.
