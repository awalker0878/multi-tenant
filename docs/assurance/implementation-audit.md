# Implementation and audit reading map

## Basis and boundary

This is a source-backed integration map, not a new deployed-system security assessment. The full [v1.1 independent audit](../archive/audit-v1-1/README.md) and [architecture-led content review](../archive/content-review-v1-2/README.md) are preserved in the historical archive. Their original findings, proposed corrections and scope limitations remain intact. The legacy API/schema defects are not labelled repaired by removing them from the main infrastructure narrative.

## Distinguish the evidence layers

| Layer | Read | What it does not establish |
| --- | --- | --- |
| Architecture decision | [RA §29](../architecture/reference/29-architecture-decisions-and-alternatives.md) and [ADRs](../adr/README.md) | A proposed pattern is not an accepted site design |
| Engineering completeness | [NBD §6](../engineering/network-boundaries/6-issue-an-interface-control-and-handoff-record.md) and [PBS §9](../engineering/platform-build/9-release-a-native-build-package-that-can-be-independently-reviewed.md) | A populated record is not a supported or deployed configuration |
| Code coverage | [Code map](../implementation/code-map.md) | A module or reader name is not full lifecycle or security coverage |
| Local fixture observations | [Historical report context](../../quality/README.md) | A local model, protocol server or namespace is not vendor qualification |
| Native campaign | [QUAL §5](site-qualification/5-qualification-stages-applicability-and-evidence.md) and [QCP §6](qualification-campaign/6-build-an-evidence-packet-a-reviewer-can-challenge.md) | No native execution is asserted by conversion |
| Operational authorization | [RA §28](../architecture/reference/28-architecture-acceptance-and-verification.md) and [QUAL §7](site-qualification/7-operating-accountability-handover-and-change.md) | A successful command or document check cannot issue authorization |

## Current documentation treatment

The conversion supplies complete chapter text, tables, diagrams and working prompts; an explicit Word-section-to-Markdown map; bidirectional links to decisions; and requirement, implementation and verification navigation. The migration report checks these publishing properties only.

## Outstanding implementation decisions

Retain the source gaps in [GM §3](gap-map/3-detailed-gap-register-and-treatment.md) and the [native implementation backlog](../../sources/implementation_backlog.csv). Choose actual site/component versions, isolation and handoff construction, platform/API authority, real capacity and service limits, independent recovery dependencies and the evidence required by the offered service. No missing values or signatures are completed on behalf of an authority.

The numbers G0–G4 identify types of acceptance. As [WD §9](../solutions/internal-protected-workload/9-build-sequence-with-explicit-acceptance-dependencies.md) states, the required initial operational and recovery readiness precedes production activation; continuing exercises do not substitute for that initial gate.
