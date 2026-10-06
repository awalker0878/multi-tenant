# G03 engineering assessment — 2026-10-06

This is Codex's engineering examination of source
`1c51f56a928291870e5125508aeb04935583fd56`, not the independent G03 decision.
EV-P03-001–003 retain original evidence at
`187ead3a02521cc3d6be063c6f449f0e3b79113a`. The user authorized continued
engineering; no representative-user or independent receiving approval is inferred.

| Criterion | Engineering assessment | Outstanding acceptance |
| --- | --- | --- |
| G03.01 | Full multi-workload/multi-domain intent survives API/Console round-trip, including unsupported required controls, recovery intent, immutable history and pinned references. Generated clients validate the corrected contract version. | Catalogue-owner review of scope and evidence. |
| G03.02 | PostgreSQL constraints and domain checks reject cross-tenant/kind/version/lifetime errors, invalid sharing, NIC/dependency/data associations, identity reassignment and stale concurrent writers. Real requests consult current Governance authority; revocation protects receipt/history access. | Architecture/quality review of positive and denied boundaries. |
| G03.03 | All 89 PostgreSQL tests pass. Concurrent requests, outbox failure, restart, broker outage, lost-confirmation replay and post-revocation publication are measured. Stable event IDs/order and independent database counts establish one logical revision per accepted command. | Independent quality examination of original timelines, counts and recovery limits. The P05 consumer is not claimed. |
| G03.04 | All three engines pass the complete authoring/conflict/uncertain-result/history/access-change journey and 38 live checks. Index scans, one-query core list budget, page/payload bounds and serialization are measured. | Representative comprehension and actual managed-browser/assistive tasks remain unrun. Product-owner acceptance is required. |

The [coverage matrix](../../../verification/p03/check-matrix.md) identifies cases
and limits. The [qualification index](../../../verification/p03/final/qualification-index.json)
records archive/report/source hashes and results. The
[corrections record](../../../verification/p03/corrections.md) preserves failed
campaigns, including the history-restoration disclosure found and fixed during
qualification. No original failure is relabeled as a pass.

P03-specific automated qualification is complete. The formerly queued final-source
foundation Kubernetes workflow `37405120379` subsequently passed at `1c51f56a`.
The [P04 follow-up receipt](../../../verification/p04/final/regression-status.json)
records its actual source and completion. The original P03 regression receipt
remains the record of what was known at that earlier observation. No receiving
or operating acceptance follows from this completed regression.

The [completion packet](../../implementation/p03-completion-review.md) provides
seven manual tasks, precise inputs and reviewer roles. BL-P03-001/002 remain open.
P03.01–03 verification records the completed automated scope. P03.04/.05 and the
phase retain IN_PROGRESS because mandatory representative-user evidence is missing.
Package work retains IN_PROGRESS pending its designated acceptance review.
G03 remains NOT_REVIEWED, without a fabricated reviewer or date.

Native qualifications remain unrun. P01/P02 receiving conditions, actual custody
and support scope are unchanged. Next engineering work is P04 preparation with
installed-platform facts and permitted discovery scope; this assessment does not
authorize native access.
