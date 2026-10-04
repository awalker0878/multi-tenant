# Delivery state and evidence rules

The [delivery register](delivery-register.yaml) is the sole editable source for package, requirement and phase delivery state, gate review results, blockers and evidence references. [Progress](progress.md) and [traceability](traceability.md) are generated views. The requirement prose, task cards and gate criteria specify expected behavior; their existence is not a passing result. All implementation starts empty on this branch.

## Four independent state axes

| Axis | Allowed values | Meaning and transition rule |
| --- | --- | --- |
| `work` | `NOT_STARTED`, `IN_PROGRESS`, `COMPLETE` | Delivery of the scoped output. `COMPLETE` needs an identified source/artifact revision and review; it does not imply tests passed. P00 output may be a reviewed design/spike rather than a product feature. |
| `verification` | `NOT_RUN`, `IN_PROGRESS`, `PASSED`, `FAILED`, `NOT_APPLICABLE_REVIEWED` | Deterministic/contract/integration checks for the record's scope. `PASSED` needs all mandatory checks at the stated revision and environment. A design-only output may use reviewed non-applicability, with a reason and reviewer. |
| `native_qualification` | `NOT_STARTED`, `IN_PROGRESS`, `QUALIFIED`, `FAILED`, `EXPIRED`, `NOT_APPLICABLE_REVIEWED` | Native platform/service outcomes on an exact supported tuple. `QUALIFIED` requires E3 evidence and independent review. Changed relevant artifacts, assumptions or expired evidence invalidate the claim. |
| `operational_acceptance` | `NOT_STARTED`, `IN_REVIEW`, `ACCEPTED`, `REJECTED`, `NOT_APPLICABLE_REVIEWED` | Acceptance by the receiving service, security and application owners as applicable, based on E4 evidence. No simulator or developer self-review substitutes. |

`BLOCKED` is deliberately not an axis value. An active blocker names the blocked scope, dependency owner, unblock condition and next action while retaining the work already performed. A phase may complete repository work while native testing is blocked; it cannot pass a gate that requires that missing evidence.

A phase's state is a reviewed roll-up of its selected packages and requirements, not the most advanced child value. Mixed results remain `IN_PROGRESS`; any mandatory failed verification is `FAILED`. `COMPLETE`, `PASSED`, `QUALIFIED` and `ACCEPTED` are permitted only when every applicable child obligation for that scope is satisfied. Expansion requirements are evaluated for the selected tranche, with deferred scope explicit; a partial tranche never passes the complete requirement. Gate decisions are separate: `NOT_REVIEWED`, `IN_REVIEW`, `PASSED`, `FAILED`. Passing G00 does not imply native qualification, and passing G07 does not grant operational approval.

## Evidence levels

E0–E4 classify evidence items, not phases or a universal maturity ladder. One requirement may need several levels and campaigns simultaneously. The normative definitions live in [requirements and qualification](requirements-and-qualification.md#4-qualification-tuple-and-evidence-levels); this table summarizes them for status review.

| Level | Acceptable evidence | Boundary |
| --- | --- | --- |
| E0 | Reviewed requirement, domain examples, contract, ADR or test design | No implemented behavior claim. |
| E1 | Recorded new-code unit/static/contract test results | No deployed/native outcome claim. |
| E2 | Real dependency integration, simulation, browser and fault/recovery results | No platform support claim. |
| E3 | Authorized exact-tuple native positive, negative and failure/recovery observations | No production change authority or operational acceptance. |
| E4 | Measured service readiness, pilot and receiving-owner acceptance | Only the accepted release and declared support scope. |

Every evidence record must identify `id`, `level`, immutable `artifact_uri`, `sha256`, `source_revision`, `artifact_revisions`, `environment`, `scope`, `campaign_ids`, `criterion_ids`, `observed_at`, `observer`, `reviewer`, `limitations`, `valid_until` and `invalidated_at`. Use explicit `null` plus an explained limitation for a genuinely inapplicable expiry; never invent a digest, date, observer or successful execution. Native records additionally require the exact qualification tuple defined in the requirements register and a campaign authorization reference. Store credentials, endpoint secrets and sensitive raw logs in approved systems, not Git.

Proposed documents in this branch are E0 *candidates*. `evidence: []` means no reviewed evidence has yet been registered. A link to a design alone cannot set a result to `PASSED`.

## Authoritative field ownership

| Record or field | Authoritative source / accountable maintainer |
| --- | --- |
| Requirement ID, priority, normative outcome, context owner | `requirements-and-qualification.md` / requirement owner |
| Phase and package scope, deliverables and dependencies | `phased-plan.md`; P00/P01 detailed task cards / delivery lead |
| All execution state, requirement/package/phase links, evidence and blockers | `delivery-register.yaml` / delivery lead with owning service and reviewer |
| Gate criteria and required evidence/environment/reviewer role | `gates.md` / qualification lead |
| Gate decision and decision evidence | `delivery-register.yaml` gate record / named reviewer at review time |
| Decision origin, disposition, blocking checkpoint and later refinements | `../decisions/decision-register.md` / ADR accountable role |
| API/event semantics and versioned contract ownership | `../contracts/README.md`, service specifications and future contract files / owning service |
| Supported tuples and qualification claims | Support matrix, backed by assurance evidence / qualification lead; never inferred from programme state |
| Current reading order and next actions | `next_work.md` / delivery lead; no duplicated status flags |

The register is YAML version 1. IDs are stable and never recycled. Dates use ISO 8601; repository paths are relative to the repository root. `contract_refs` and `doc_refs` point to existing specifications, not a claim that executable contracts exist. `planned_outputs` are future paths and must not be presented as working links. `campaign_ids` refer to Q01–Q10 definitions in the requirements register. `gate_ids` identify G00–G11. `criterion_ids` identify checklist items such as G01.02. `package_ids`, `requirement_ids`, `phase_ids`, `decision_ids`, `evidence_ids` and `blocker_ids` are explicit joins by ID.

Root fields are `schema_version`, `baseline_date`, `branch`, `defaults`, `phases`, `work_packages`, `requirements`, `gates`, `evidence` and `blockers`. Defaults specify the four initial states. Each phase/package/requirement stores its own `status` for its own scope; these are not competing copies of a single item. Package mappings under each requirement are canonical; package requirement lists in generated views must be derived from them. Each gate has a `decision`, `reviewer`, `reviewed_at`, `evidence_ids` and `blocker_ids`. Empty reviewer/date values mean no review occurred. Requirement optionality is normative; no axis can become `NOT_APPLICABLE_REVIEWED` without `applicability_review.<axis>` containing reason, reviewer, date and scope. Keep validation enums in `scripts/validate_docs.py` aligned when these status rules change.

## Change procedure

1. Identify the requirement, package, changed behavior/contract, source revision and affected support tuples. Update their specifications in the same change.
2. Register immutable evidence and its actual environment. Link it to exact criteria and requirements; record failures and limits as faithfully as passes.
3. Obtain the required review. Update only the affected register statuses and gate decisions. Record unresolved dependencies as blockers; do not overwrite progress with a generic blocked flag.
4. Regenerate progress and traceability, then validate references and view consistency. Update `next_work.md` with the next concrete task and its unblock condition.
5. On a material change, mark affected qualification `EXPIRED`, reopen affected gate review, and schedule the required rerun. Reuse unaffected evidence only with a recorded impact review.

A future blocker record contains `id`, `scope_ids`, `owner_role`, `description`, `unblock_condition`, `next_action`, `state` (`OPEN`/`RESOLVED`) and resolution evidence. Unassigned staffing and lab details in P00 task cards are planning inputs to obtain, not invented confirmed incidents. No exception can waive a mandatory security outcome while preserving the same support claim; narrow scope explicitly or leave the gate failed.
