# Maintained design workspace

**Authority model selected for this corrective release:** converted chapters remain immutable source transcriptions; current design is maintained separately here. The original Word files remain provenance. Source refresh is forbidden from writing here. An ordinary editorial revision to these records passes the current-design structural gate without repeating obsolete source sentences.

The records below are newly authored under distinct IDs and remain Proposed. They are not recovered standalone v1.2 Word files and do not record real site acceptance. Update their version, source relationship and change history with material revisions. Use ADR lifecycle records for decisions; a Git merge is not native authorization.

| Record | Purpose |
|---|---|
| [RAD-M01](RAD-adoption.md) | Baseline applicability, deviations and architecture handoff |
| [TAD-M01](TAD-infrastructure.md) | Technical components, native realization and ownership |
| [SOL-M01](internal-hosting-solution.md) | Existing internal reference fixture selected as a solution profile |
| [SOL-M02](public-hosting-design-profile.md) | New public-extension design profile, not a complete installed service |
| [ICD-M01](interface-agreements.md) | Producer/consumer interface obligations |
| [TRANS-M01](transition-and-as-built.md) | Intermediate states, consistency, observed design and acceptance |

[Source-scope decision inventory](../assurance/source-scope.md) · [Frozen source reading paths](../README.md) · [ADR lifecycle](../adr/README.md)

Run `python scripts/check_documentation.py`: immutable transcription checks and current-design structure are separately reported. Semantic correctness and accepting authority require real review; do not use this gate as an approval service.
