# ADR-0002 — Markdown-first, source-backed architecture documentation

Status: Proposed publishing decision for this repository package. This implements the requested documentation layout, not an organizational security approval.

## Context

The earlier repository catalogue exposed binary files but not their full content to code review. Infrastructure decisions were embedded in chapters, tables and worked designs, while only one repository-organization ADR was visible.

## Decision

Keep chapter-sized Markdown in the role and subject directories under `docs/`. Preserve the original document bytes at their existing reference paths. Resolve converted Word cross-references to Markdown sections and retain actual diagram assets. Maintain the source hash, document/version, original section and conversion ledger so that a reader can distinguish a source transcription from new synthesis.

Extract documented architecture choices into proposed ADRs, preserving original decision identifiers. Do not invent an acceptance date, signatory, completed test, rejected-option meeting or missing source document. Keep historical audits and superseded handbook text in `docs/archive/` with an explicit historical banner.

## Relationship to ADR-0001

[ADR-0001](0001-architecture-first-repository.md) establishes the repository layout and preservation of original paths. This decision supplements its binary catalogue with full Markdown content; it does not replace its separation of architecture, engineering and implementation.

## Alternatives and consequences

A catalogue alone was insufficient for the requested Git documentation. One large Markdown file per original would preserve text but make review and linking cumbersome. Rewriting from general knowledge would obscure lineage and could change the supplied architecture. Chapter decomposition preserves the source organization while subject indexes connect related content.

Markdown is the working review surface for this package. A future normative change must update the applicable architecture, ADR, engineering and verification references together. Frozen Word originals remain provenance, not a second automatically synchronized live authoring surface. Explicit source refresh overwrites converted chapter text and therefore belongs in a clean review branch, never an unattended production pipeline.

## Scope and exclusions

This is not a new architecture approval, site design, live qualification, or assertion that historical contract defects were repaired. Workbooks and native infrastructure code are unchanged. Standalone RAD/TAD v1.2 source files were not present; the RAD and TAD pages in this package are clearly identified reading views over available material.

## Verification and maintenance

Use [the migration procedure](../DOCUMENTATION_MIGRATION.md) and `python scripts/check_documentation.py` to verify source hashes, block coverage, images, tables, fields, links, decision identifiers and source-derived ADR status. Review architecture status separately from passing documentation checks.
