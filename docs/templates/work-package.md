# Work-package card template

Use a stable PNN.NN ID. Keep progress values in the delivery register.

| Field | Required content |
| --- | --- |
| Outcome and scope | User/operator result; included and excluded behavior |
| Accountability | Owner role now; actual assignee/reviewer when assigned |
| Traceability | Requirement, ADR, service/contract, campaign and gate criterion IDs |
| Dependencies | Exact preceding package/output; current decision constraints; external access/owner dependency |
| Inputs | Source revisions, schemas, synthetic fixtures and environment prerequisites |
| Outputs | Concrete paths/artifacts; distinguish existing documents from planned future files |
| Implementation steps | Small ordered increments with a reason for the order |
| Acceptance | Objective positive, negative, concurrency/recovery checks relevant to scope |
| Evidence | Required level/environment, immutable artifact reference and reviewer responsibility |
| Operating impact | Configuration, identity, deployment, support, observability and recovery changes |
| Estimate | Range, staffing/access assumptions, confidence and re-estimation trigger |
| Blockers and next action | Dependency owner, unblock condition and concrete independent work still possible |

Do not replace acceptance with “tests pass” or “documentation complete.” Name the behavior to demonstrate and the conditions under which it must hold. A future output path is not proof that the file or behavior exists.
