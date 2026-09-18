# F15  |  Printed control-family crosswalk omits existing catalogue mappings

[Documentation home](../../README.md) · [Source document](../../../reference/migration-source-documents/Independent_Audit_v1_1.docx) · [Chapter index](README.md)

> **Source:** AUD11 — Audit of Draft v1.1. Historical source; not the active design.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: cd901aaf004d45cf29ffe14ff955a0c9cf81f668be674e8d4de8c590303c62d8 -->

> **Historical only.** Use the [v1.4 reference architecture](../../architecture/reference/README.md) for the active design baseline. Conflicting historical text has not been silently reconciled.
High priority • Confirmed document/package parity defect and scope gap<br>Location: Appendix E p91; catalogues/requirements.json

Observed. Appendix E prints 14 families. The JSON requirement catalogue contains 16: PT has one mapping through PLACE-002, and SA has two through PLACE-003 and PORT-003. Both disappear from the printed summary. AT, MA, PE and PS have no family mappings in the catalogue.

Why it matters. Readers of the handbook and machine catalogue see different coverage. Absent organizational/physical families can disappear rather than being deliberately inherited or scoped out.

Improve. Generate the appendix from the complete family map and include a disposition for every applicable family: directly implemented, inherited, tenant-owned, shared, not applicable or gap. Do not invent control selection or require this reference handbook to implement organizational programs. \[W04\]

Close when. Printed and JSON families/counts are identical; omitted families have a named applicability/inheritance disposition and evidence owner.

Owner: Assurance and documentation owners

[Previous chapter](16-f14-reference-validation-needs-explicit-coverage-tiers-and-stronger-negatives.md) · [Chapter index](README.md) · [Next chapter](18-f16-requirement-to-test-links-do-not-yet-prove-assertion-level-coverage.md)
