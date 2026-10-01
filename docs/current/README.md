# Maintained design workspace

**Authority model selected for this corrective release:** converted chapters remain immutable source transcriptions; current design is maintained separately here. The original Word files remain provenance. Source refresh is forbidden from writing here. An ordinary editorial revision to these records passes the current-design structural gate without repeating obsolete source sentences.

The records below are newly authored under distinct IDs and remain Proposed. They are not recovered standalone v1.2 Word files and do not record real site acceptance. Update their version, source relationship and change history with material revisions. Use ADR lifecycle records for decisions; a Git merge is not native authorization.

| Record | Purpose |
|---|---|
| [RAD-M01](RAD-adoption.md) | Workload mobility, capability boundaries, adoption and architecture handoff |
| [TAD-M01](TAD-infrastructure.md) | Control application, discovery, profiles, native realization and recovery ownership |
| [SOL-M01](internal-hosting-solution.md) | Existing internal reference fixture selected as a solution profile |
| [SOL-M02](public-hosting-design-profile.md) | New public-extension design profile, not a complete installed service |
| [ICD-M01](interface-agreements.md) | API, workflow, worker, transfer, shared-service and evidence interface obligations |
| [TRANS-M01](transition-and-as-built.md) | Intermediate states, consistency, observed design and acceptance |

TAD-M01 is **version 0.20 (Proposed)**; ICD-M01 is **version 0.19 (Proposed)**.
RAD-M01 and TRANS-M01 are **version 0.12 (Proposed)** following the 30 September 2026
signed owner-review, application-comparison and bounded batch-staging increments. Both solution records remain **version 0.3 (Proposed)** following the 28 September 2026
mobility review. They describe the authenticated control application, durable discovery
and comparison, 97 explicit capability dimensions, mandatory workload/service profile
requirements, migrated qualification owners, and the remaining admitted native workflow
and operating-acceptance gaps. The [B01–B50 execution plan](../product/enterprise-workload-mobility-execution-plan.md)
remains the implementation backlog; coverage in this register does not close its gates.

[Source-scope decision inventory](../assurance/source-scope.md) · [Frozen source reading paths](../README.md) · [ADR lifecycle](../adr/README.md)

Run `python scripts/check_documentation.py`: immutable transcription checks and current-design structure are separately reported. Semantic correctness and accepting authority require real review; do not use this gate as an approval service.

The
[verified research record](../engineering/platform-migration-research.md) identifies
accepted assumptions, rejected recommendations and remaining native evidence.
The existing B01–B50 plan remains the only implementation backlog.

[Signed publication and restart recovery](../engineering/discovery-publication-recovery.md)
now documents implemented collector signatures, campaign-bound original-byte custody
and explicit mTLS delivery. Deployed site orchestration, independent retention and
restart/DR authority reconciliation remain open under the same wave plan.

[Installed collector command](../engineering/discovery-collector-runtime.md) provides
separate stage/publish actions over the existing adapters and original-byte custody.
It neither issues native credentials nor replaces deployment and qualification gates.

[Persisted application drafts](../engineering/application-drafts.md) retain observed
membership, proposed datasets, attributed assertions and revision history without
accepting ownership or granting migration authority.

[Draft operator listing and save/load](../engineering/application-draft-operator.md)
retain unreviewed state, live-page semantics and explicit uncertain-save handling.
The [browser workspace](../engineering/application-draft-browser.md) now lists and
edits existing draft metadata/startup order while retaining read-only evidence.
[Signed owner-review evidence and status](../engineering/application-owner-review.md)
now provide separately verified assessment-only decisions and exact-revision CLI
status inspection. Owner-facing signing,
full browser creation/evidence editing and application-wide migration planning
remain open; immutable drafts and native execution authority stay separate.

[Application-comparison operator](../engineering/application-comparison-operator.md)
now exposes exact reviewed-draft multi-member comparison through the existing API,
with canonical selection binding and no native execution or reservation authority.

[Saved-application browser](../engineering/application-comparison-browser.md) adds
portal comparison from an unchanged current draft, explicit per-member profiles
and the existing destination picker. Exact response checks and stale-result clearing
preserve assessment-only scope. Guided authoring, native evidence and B22 remain open.

[Bounded discovery batch staging](../engineering/discovery-batch-scheduling.md)
adds due-task selection and process-local endpoint backpressure to the installed
collector. Durable fleet scheduling, global budgets, periodic monitoring and resumable
publication remain B22 work. Wave 2 stays open; no later wave is advanced.

[Scoped freshness inspection](../engineering/discovery-freshness.md) now separates
capture age, missing inventory and reported collection-health gaps through the
existing API. TAD/ICD versions above include this inspection interface. Periodic
monitoring/alerts, global scheduling and other Wave 2 gates remain open. RAD/TRANS
stay at 0.12 and both solution records at 0.3; no authority boundary is changed.

[Freshness operator inspection and checks](../engineering/discovery-freshness-operator.md)
now expose that same metadata API through the existing installed CLI. Optional
check mode distinguishes valid-but-unhealthy metadata from a failed read while
retaining unverified native visibility and no collection/execution authority.
This B22 client increment does not add periodic monitoring or close Wave 2.

[Shared-outbox capture claims](../engineering/discovery-publication-recovery.md#shared-outbox-first-capture-exclusion--b22-continuation)
now prevent concurrent first capture by cooperating updated processes using the
same local custody. Incomplete intents survive process exit and remain held;
completed originals resume unchanged. This is not fleet scheduling or global
endpoint budgeting, and Wave 2 stays open. Architecture versions above are unchanged.


[Retained freshness history](../engineering/discovery-freshness-history.md) records
the implemented on-demand check writer, exact-ID retry, paginated history and
cursor/predecessor integrity. Its deployment addendum names migration 0023, narrow
API runtime grants, atomic audit and restore obligations. This closes the retained
history/API gap, not periodic monitoring or alert delivery. The maintained architecture
versions above are unchanged; this engineering addendum supplies the implemented
interface and recovery detail without recording design or operational acceptance.
