# Portable multi-tenant secure hosting — documentation

**Infrastructure architecture → engineering → solution design → implementation → operational acceptance.**

This repository now contains the Word documents' actual content as Markdown chapters. The active source baseline remains the supplied v1.4 reference architecture, delivery-kit v1.1 development documents and Implementation Increment 04. Conversion does not issue approval or replace unknown site values with defaults.

| Start with | Content |
| --- | --- |
| [Architecture](architecture/README.md) / [RAD reading view](architecture/RAD.md) | Scope, physical/logical design, security and service boundaries, portability and adoption |
| [Engineering](engineering/README.md) / [TAD reading view](engineering/TAD.md) | Fabric, native stacks, forward/reply paths, dependencies and supported build responsibilities |
| [Solution designs](solutions/README.md) | Service alternatives and a connected two-tenant OZ/RZ worked environment |
| [Implementation](implementation/README.md) | Commissioning work packages, code coverage, readback, safe stopping and handover |
| [Operations](operations/README.md) | Change, recovery, migration, failback, retention and operating ownership |
| [Assurance](assurance/README.md) | Gap map, requirements, test specifications, qualification and audit boundaries |
| [ADRs](adr/README.md) | Proposed source-backed design decisions and original decision-ID mapping |
| [Templates](templates/README.md) | Full HLD, LLD, implementation, review and acceptance prompts |
| [Governance](governance/README.md) | Delivery framework, gate dependencies and responsibilities |
| [Archive](archive/README.md) | Historical handbook editions, audit and content-disposition review |

## Review one connected path

Read [the inter-domain boundary](architecture/reference/8-zone-interfaces-routing-and-security-edge-topology.md) → [its forward and return routing](engineering/network-boundaries/2-walk-f14-01-through-the-forward-and-reply-routes.md) → [its vendor realization](solutions/internal-protected-workload/8-mapping-the-schedules-into-each-vendor-stack.md) → [its provisioning sequence](implementation/provisioning-strategy/4-end-to-end-fixture-provisioning-and-safe-activation.md) → [its verification observations](assurance/qualification-campaign/3-observe-network-paths-and-boundary-enforcement.md). The chapters preserve their source diagrams, tables and cross-references.

## Source and change rules

[Conversion coverage and maintenance](DOCUMENTATION_MIGRATION.md) records what was moved, what is historical and what source artifacts were unavailable. [The binary catalogue](ARTIFACT_CATALOG.md) remains for provenance and workbook access. The [implementation coverage map](implementation/code-map.md) distinguishes candidate code from actual platform qualification.

Do not silently change inherited requirements while copying them into an ADR. Source-derived ADRs have no recorded organizational acceptance. Initial operational and promised recovery readiness remains a prerequisite to production activation—not a later paperwork step.
