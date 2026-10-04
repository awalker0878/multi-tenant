# Sources, precedence and branch reset

## Authoritative direction

1. The current request asks for a detailed implementation plan with phases, abandonment of the previous Laravel foundation branch and a new branch.
2. The supplied `Pasted markdown(6).md` contains successive proposals. Its later explicit greenfield direction takes precedence over its earlier transition plan.
3. Historical repository material supplies hosting, workload mobility and execution-safety requirements. It does not supply current product completion or qualification evidence.

The source transcript's claims about earlier local tests and partly built applications are historical narrative. They are not validated achievements of this branch. Embedded rendering/CSS noise from the pasted transcript is not copied into the product documentation.

## Repository provenance and reset policy

| Item | Recorded reference |
| --- | --- |
| Repository | `awalker0878/multi-tenant` |
| New delivery branch | `greenfield/enterprise-microservices-plan` |
| Main parent at reset | `3cbc0c1e1e52a4bedd70972b05b04ccec48de699` |
| Abandoned branch | `greenfield/laravel-product-foundation` (the complete branch name corresponding to the user's shortened reference) |
| Historical requirement checkout | `a9c7a2fbb2a97acce2b4ad007b098292673c9fbf` |
| Primary supplied file | `Pasted markdown(6).md`, read from the supplied attachment |

The new branch retains Git ancestry for provenance but replaces its working tree with fresh planning documents. It does not derive its implementation from the abandoned branch. This reset affects only the new branch; `main`, previous branches and existing local uncommitted work are preserved. No runtime, compatibility shim, old lockfile, workflow or deployment is carried into the fresh tree.

The [historical requirement register](../implementation/requirements-and-qualification.md) identifies the earlier documents reviewed. Product source, inventories, credentials, native plans, Terraform state and actual evidence must remain in their approved systems. Do not put operational secrets or datasets into documentation examples.

## Current primary-source checks

Checked on 2026-10-04. These establish candidate compatibility and design constraints, not successful local installation or qualification. Upstream branch URLs are moving references; P00 must pin reviewed source commits and exact resolved packages.

| Source | Finding used by the plan | Remaining implementation check |
| --- | --- | --- |
| [Laravel 13 releases](https://laravel.com/framework/docs/13.x/releases) | Laravel 13 lists PHP 8.3–8.5 support | Choose maintained PHP minor/patch and required extensions; test complete dependencies |
| [Official Laravel Vue starter package manifest](https://github.com/laravel/vue-starter-kit/blob/main/package.json) | Declares Inertia Vue adapter 3, Vue 3, Tailwind 4, TypeScript, Vite 8 and Laravel Vite plugin 3 together | Resolve exact dependencies, review starter choices, create new application lockfiles and build/typecheck |
| [Vite 8 release](https://vite.dev/blog/announcing-vite8) | Documents Node requirements of 20.19+ or 22.12+ | Select a currently supported Node LTS meeting the requirement; test production bundling |
| [Temporal workflow definition](https://docs.temporal.io/workflow-definition) | Workflow replay requires deterministic coordination; external interactions belong in activities | Replay tests, workflow/worker versioning, bounded timeouts and safe activity retry/reconciliation |
| [Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/) | Policies require an enforcing network implementation | Verify the selected CNI and actual allowed/denied traffic; independently configure authenticated/encrypted service channels |

Framework existence does not establish managed-browser support, enterprise identity integration, operating-system/container compatibility, accessibility or package security. These are explicit P00/P01 checks. The requested versions remain the target; a necessary change must be documented rather than silently substituted.

## Enterprise engineering review

The [Laravel practices assessment](laravel-practices-review.md), reviewed 2026-10-04, evaluates the supplied Strapi article against primary Laravel, PHP-FIG, frontend, OWASP, W3C and secure-delivery sources. It establishes [engineering guidance](../engineering/README.md) and a [control-to-delivery map](../engineering/coverage.md). Framework facts, project policy and future verification remain distinguishable; these additions do not accept open ADRs or create execution evidence.
