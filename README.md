# Enterprise Workload Mobility — Greenfield Microservices Plan

This branch establishes a new implementation programme for an enterprise application that discovers, assesses, provisions, migrates, recovers and retires workloads across qualified VMware, Nutanix and OpenStack environments.

**Status: planning baseline, 4 October 2026.** This branch contains documentation only. No application, platform integration, deployment or native capability is represented as implemented or qualified.

The active branch is `greenfield/enterprise-microservices-plan`. It supersedes `greenfield/laravel-product-foundation` for this work. It starts from repository `main` at `3cbc0c1e1e52a4bedd70972b05b04ccec48de699` for history, with a fresh documentation tree. The abandoned branch, earlier implementations and unfinished work remain reference material; they are not dependencies of this product.

## Start here

| Document | Purpose |
| --- | --- |
| [Phased implementation plan](docs/implementation/phased-plan.md) | Scope, work packages, dependencies, owners, exit gates, deployment and release sequence |
| [Target architecture](docs/architecture/target-architecture.md) | Contexts, product model, authority boundaries, contracts, execution and deployment |
| [Requirements and qualification](docs/implementation/requirements-and-qualification.md) | Requirements coverage, platform matrix, evidence levels and acceptance campaigns |
| [Decision register](docs/decisions/decision-register.md) | Fixed direction, proposed defaults and decisions that Phase 0 must resolve |
| [Next work](next_work.md) | Ordered Phase 0 backlog and conditions for starting implementation |
| [Progress](docs/implementation/progress.md) | Honest phase status and completion evidence |
| [Sources and branch reset](docs/reference/sources-and-reset.md) | Input precedence, provenance, framework sources and reset policy |

## Product and delivery baseline

- Laravel 13 / PHP for the console, governance, application catalogue and assurance.
- Inertia 3, Vue 3, TypeScript, Tailwind CSS 4 and Vite 8 for the operator experience.
- Python for inventory, planning, lifecycle orchestration and scoped site workers; Temporal for durable workflows.
- One repository, seven principal application deployables, service-owned data, versioned API/event contracts and independent releases.
- A new implementation with no runtime shims or dependency on the abandoned application.
- First proposed native path: OpenStack provisioning, followed by one explicitly selected VMware-to-OpenStack offline application migration route. Additional platforms, directions, versions and methods require separate qualification.

The plan deliberately separates code completion, simulated verification, native qualification and operating acceptance. A framework scaffold or green CI result does not grant permission to modify infrastructure.
