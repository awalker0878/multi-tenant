# Service design and architecture decisions

[Documentation home](../../README.md) · [Source document](../../../reference/Portable_Hosting_Delivery_Kits_v1_1/01_Architecture/Service_Design_and_Decision_Development.docx)

> **Source:** SDP — Delivery-kit v1.1 collection; original document version retained in the front matter. Proposed reference or working template; site adoption is not recorded by conversion.
> This is a source-content transcription, not a new approval or a current platform-validation result.

<!-- source-sha256: 133c2512e904737c1f410106fd1b421fba8309965af0621785b250402fb9214e -->

## Chapters

- [1. Define the offered service before choosing the build](1-define-the-offered-service-before-choosing-the-build.md)
- [2. Choose sharing at each infrastructure layer](2-choose-sharing-at-each-infrastructure-layer.md)
- [3. Develop a boundary architecture decision](3-develop-a-boundary-architecture-decision.md)
- [4. Turn dependencies into explicit service interfaces](4-turn-dependencies-into-explicit-service-interfaces.md)
- [5. Make capacity-on-demand and exit economically explainable](5-make-capacity-on-demand-and-exit-economically-explainable.md)
- [6. Release the architecture as an accountable engineering contract](6-release-the-architecture-as-an-accountable-engineering-contract.md)

## Source front matter
DESIGN DEVELOPMENT  /  SDP

## Service Design and Architecture Decisions

*Develop a service offer that engineering can translate into a bounded infrastructure design.*

Kit release v1.1 • 17 September 2026 • Parent architecture v1.4 retained

Proposed engineering development. Reference examples, site decisions, actual observations and approval remain separate.

This supplement develops the decisions behind AK-01–AK-08. It supplies worked alternatives, a service-envelope method and an engineering handoff. It does not replace the HLD template or pre-approve any site. Use the existing architecture register as the project record; the examples here explain how to complete it.

## Section navigation

[1. Define the offered service before choosing the build](1-define-the-offered-service-before-choosing-the-build.md#SDP_01)

[2. Choose sharing at each infrastructure layer](2-choose-sharing-at-each-infrastructure-layer.md#SDP_02)

[3. Develop a boundary architecture decision](3-develop-a-boundary-architecture-decision.md#SDP_03)

[4. Turn dependencies into explicit service interfaces](4-turn-dependencies-into-explicit-service-interfaces.md#SDP_04)

[5. Make capacity-on-demand and exit economically explainable](5-make-capacity-on-demand-and-exit-economically-explainable.md#SDP_05)

[6. Release the architecture as an accountable engineering contract](6-release-the-architecture-as-an-accountable-engineering-contract.md#SDP_06)

Basis: linked RA/WD and role-kit sections retain their original authority. The elaborations, record formats and calculations in this supplement are local proposals, not new government requirements. D-source references identify freshly checked public mechanisms, not installed compatibility. Exact source locators are in 04\_Shared/development/source\_reviews.csv.
