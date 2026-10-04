# Documentation templates

Copy the relevant structure when a concrete work item begins. Replace instructional text with actual scoped content and link the new document from its owning index. These templates are authoring aids, not completed decisions, tests or approvals.

| Template | Destination and use |
| --- | --- |
| [Service specification](service-specification.md) | `docs/services/<service>.md`; ownership and behavior of a deployable |
| [Work package](work-package.md) | A section of `docs/implementation/phases/pNN.md`; an implementable increment |
| [Architecture decision](adr.md) | `docs/decisions/adr-NNN-title.md`; options, rationale and consequences |
| [Gate review](gate-review.md) | Approved evidence system; sanitized review references in the delivery register |
| [Runbook](runbook.md) | `docs/operations/runbooks/<action>.md`; a versioned, rehearsed operating procedure |
| [Qualification campaign](qualification-campaign.md) | `docs/qualification/<campaign>.md`; synthetic test design and protected evidence references |

The [documentation guide](../documentation-guide.md) defines canonical ownership. Follow the [status model](../implementation/status-model.md) rather than creating a new checklist status vocabulary. Raw operational evidence, personal approvals and site secrets remain in approved systems.
