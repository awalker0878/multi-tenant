# Documentation index

This documentation describes a proposed enterprise product and its delivery programme. Read the repository [README](../README.md) for the application, intended users and first release. A design example, candidate contract or planned test is not evidence of implemented behavior.

## Product and user behavior

| Document | Question answered |
| --- | --- |
| [Product overview](product/README.md) | Who uses the product, what tasks matter and what outcomes define success? |
| [Domain model](product/domain-model.md) | What do the entities mean, how do they relate and which invariants apply? |
| [Application walkthrough](product/application-walkthrough.md) | What happens to one application, including failure and recovery? |

## Architecture and service design

| Document | Question answered |
| --- | --- |
| [Target architecture](architecture/target-architecture.md) | Where do data, decisions and execution authority belong? |
| [Service specifications](services/README.md) | What does each deployable own and expose? |
| [Contracts](contracts/README.md) and [examples](contracts/examples.md) | How do the PHP/Python services communicate? |
| [Architecture decisions](decisions/README.md) and [register](decisions/decision-register.md) | What is the reasoning, disposition and deadline for each choice? |

## Implementation and assurance

| Document | Question answered |
| --- | --- |
| [Phased plan](implementation/phased-plan.md) | What is the overall sequence, scope and dependency chain? |
| [Phase work packages](implementation/phases/README.md) | What must each phase deliver, depend on and demonstrate? |
| [Next work](../next_work.md) | Which tasks are next, and what do they depend on? |
| [Requirements and qualification](implementation/requirements-and-qualification.md) | Which requirements and acceptance campaigns must be covered? |
| [Traceability](implementation/traceability.md) | How do requirements connect to packages, decisions, contracts and gates? |
| [Delivery register](implementation/delivery-register.yaml) | What is the canonical structured record of delivery state and evidence references? |
| [Status definitions](implementation/status-model.md) | What does each status mean, and what evidence permits changing it? |
| [Progress](implementation/progress.md) and [gates](implementation/gates.md) | What is the current state and what must a reviewer verify? |
| [Support matrix](implementation/support-matrix.md) | Which platform operations and migration combinations are planned or excluded? |
| [Qualification procedures](qualification/README.md) | How are feasibility, campaigns and gate reviews performed and evidenced? |
| [Estimation and dependencies](implementation/estimation-and-dependencies.md) | Which staffing, access and sequencing assumptions drive the estimate? |

## Deployment, contribution and provenance

| Document | Question answered |
| --- | --- |
| [Operations index](operations/README.md) and [deployment model](operations/deployment-model.md) | How will the application be installed, upgraded, observed and recovered? |
| [Documentation guide](documentation-guide.md) | Where does additional work belong and when must it change? |
| [Templates](templates/README.md) | What should a new decision, service design, work package, gate or runbook contain? |
| [Contribution workflow](../CONTRIBUTING.md) | How should a coherent change be prepared and reviewed? |
| [Release documentation](releases/README.md) | How are candidates, manifests, support, readiness and release notes managed? |
| [Sources and reset](reference/sources-and-reset.md) | Which source direction applies and what is historical reference only? |

Use the linked phase, decision, qualification, operations and release indexes to navigate the working documents. The [guide](documentation-guide.md) defines ownership and update rules. Executable schemas, test results and release-specific evidence are added through their implementation work packages.
