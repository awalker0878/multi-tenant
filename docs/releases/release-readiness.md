# Release readiness review

Owner: qualification lead coordinating product, security, SRE, platform and receiving service owners. Use the canonical G10/G11 [criteria](../implementation/gates.md) and [review procedures](../qualification/gate-reviews/README.md) for recorded decisions.

## Review inputs

The reviewer receives the candidate manifest, supported-scope matrix, qualification-impact analysis, immutable evidence references, open blockers, operating objectives, install/upgrade/recovery procedures, security findings and pilot plan or outcomes. Each input identifies its artifact revision and scope.

## Required assessments

| Assessment | Reviewer must establish |
| --- | --- |
| Scope | The release advertises only selected operations, methods, directions, guests and deployment conditions |
| Behavior | Required contract, tenant, workflow, failure and recovery cases have applicable results |
| Native outcomes | Actual platform and application observations support the exact claimed tuples |
| Isolation and authority | Cross-tenant denial, revocation, fencing and unknown-outcome containment hold in the release environment |
| Data safety | Required consistency, source/target writer transition, restoration and post-target-write recovery have evidence |
| Operations | Installation, upgrade, dependency/key loss, restore and alert delivery are demonstrated with receiving operators |
| Capacity | Accepted workload tiers and service objectives are supported by reproducible measurement |
| Support | Escalation ownership, runbooks, known limitations, retention and maintenance responsibilities are accepted |
| Pilot | Application, security and service owners accept the bounded pilot outcome |
| Integrity | The artifacts being promoted are the artifacts bound by the qualification and acceptance record |

## Decision and follow-up

Record each gate criterion's evidence, observed result, reviewer and limitations. Missing evidence remains missing even if adjacent tests passed. A narrowed release must update the manifest, support matrix, requirements mapping and release notes so users receive the same scope that reviewers accepted.

Unresolved mandatory outcomes block the relevant gate. Corrective work references the failed criterion and defines the retest needed. Actual gate results and reviewed scope are written to the canonical delivery register; this review procedure does not itself assert a pass.

After publication, monitor the selected service indicators and maintain support validity. A material incident, drift or expired evidence triggers impact review and suspension of affected admission where required.
