# ADR-023 — Context code boundaries and automated controls

Owner role: Architecture and engineering leads. Related phases: P00, P01, P10. Record date: 2026-10-04.

Origin: `DESIGN`. Disposition: `PROPOSED`, as recorded in the [decision register](decision-register.md). The user's requirement for context-oriented microservices and code control is binding; the detailed namespace, layer and enforcement design below is its proposed implementation. This record does not claim that repository protection settings or application CI gates are active.

## Context

The earlier engineering guide placed business code in conventional application-wide actions, models and policies. That allowed source ownership and dependency direction to remain matters of convention. The user explicitly rejected that level of structure for this enterprise product. Independently deployed microservices need code boundaries that preserve their bounded contexts as features, developers and shared packages grow.

## Decision and scope

Use the [context code structure](../architecture/context-code-structure.md) as the implementation blueprint. Each business context owns its model, use cases, ports, persistence mapping, entry adapters, contract exports and tests. Keep the six business contexts and the console composition boundary distinct from their independently built deployables; capabilities are modules inside those owners rather than automatically becoming new services.

Laravel hosts load explicit `src/Contexts/<Context>/Domain`, `Application`, `Infrastructure` and `Interfaces` namespaces. Domain and Application remain independent of Laravel/Eloquent; Infrastructure implements persistence and integration ports; Interfaces adapt HTTP, messages, CLI and jobs to use cases. A small host composition root binds implementations. Python contexts mirror these responsibilities. The console owns presentation/session composition, not copies of service domain models.

Maintain the machine-readable [context map](../../architecture/context-map.yaml) with source roots, ownership, languages, allowed dependencies and worker/package boundaries. Apply [code controls](../engineering/code-control.md) to source placement, imports, dependency manifests, contracts, review ownership, required checks, exceptions and artifact promotion. The repository validator is an initial control; its reported source-analysis scope must remain explicit.

Checkpoint: P00.02 reviews ownership and source boundaries; P00.03 selects compatible analysis tooling. P01.01 implements the structure and complete language-aware boundary checks; P01.04 establishes required review/CI enforcement with actual authorized owners. G01 requires positive and deliberately forbidden-change evidence. P10.06 rechecks policy activation and exceptions for release.

## Alternatives considered

| Option | Consequence |
| --- | --- |
| Application-wide Laravel folders with informal ownership | Familiar initially, but makes the user's required boundaries too easy to bypass as the codebase grows |
| Explicit context/layer structure with automated import and ownership controls | Chosen blueprint; additional mapping/ports are justified by independently evolving contexts and privileged workflows |
| A service or package for every capability/entity | Adds deployment and compatibility overhead without establishing a useful business or authority boundary |
| Shared business models across contexts | Couples data ownership, runtime dependencies and releases; rejected for this architecture |

## Consequences and controls

- Eloquent models are context-private Infrastructure persistence records; domain aggregates and application DTOs are separate types.
- Public service contracts are schema-owned and versioned. Another context may consume a client or event DTO but cannot import private domain/application classes or migrations.
- Composition is the explicit exception to inward dependency direction. It is narrow, owned and checked; general `app/` or `Shared/` directories are not bypass areas.
- Each independently deployed service owns its lockfiles, build image, data migrations and deployment identity. Worker builds declare any included owning-context code as an immutable input.
- Ownership metadata is connected to actual repository review controls. Listing several CODEOWNERS does not by itself require all of them to approve.
- Changes to policy configuration, architecture maps, ownership, suppression baselines or CI workflows receive the same protected review as the code they govern.

## Verification required

Prove valid same-context composition and isolated builds. Intentionally introduce and reject a cross-context model import, a Domain framework dependency, an Application-to-Infrastructure dependency, an unregistered source root, a shared-package cycle and an incompatible public contract. Demonstrate that an ordinary contributor cannot merge a failing or insufficiently reviewed change under the selected repository configuration.

The current architecture validator and its fixture tests establish only the checks they actually execute. No application source, completed PHP architecture analysis, live branch protection or native qualification can be inferred from an empty source tree passing registry checks. Keep current execution status and evidence in the delivery register.

## Revisit conditions

A bounded-context ownership change, justified deployment consolidation/split, new shared package, generator/tool limitation, required infrastructure adapter or repository-plan capability changes the permitted graph. Amend the registry, design, checks and migration plan together; do not make an unreviewed import exception the new architecture.
