# Word-to-Markdown migration and maintenance

## What was converted

The migration transcribes **28 Word documents** into **411 chapter pages**, plus one content index/front-matter page per source. **224 chapters in 23 documents** belong to the active architecture, engineering, working-template and Increment 04 family. The remaining source chapters are explicitly historical.

The coverage ledger accounts for **5551 source body blocks, 486 tables, 199 editable field prompts and 25 figure occurrences**. Original figure bytes are preserved as **21 deduplicated image files**. These counts describe source coverage, not architectural completeness or security assurance.

The original 24 Word documents from the commit-ready package were retained. Four available historical sources were additionally archived: the original v1.0 handbook, expanded v1.1 handbook, independent v1.1 audit, and architecture-led v1.2 content review. The three workbooks remain unchanged and linked from the catalogue.

## Structure and provenance

Full narrative and tables live below `docs/architecture/`, `docs/engineering/`, `docs/solutions/`, `docs/implementation/`, `docs/operations/`, `docs/assurance/` and `docs/templates/`. Every source chapter links its immutable Word baseline, its source index, previous/next chapter and original section/version context. The original chapter order remains visible. The subject indexes and RAD/TAD reading views connect those chapters without replacing their contents with summaries.

[The section map](../sources/documentation/section_map.csv) records exact Word-to-Markdown destinations. [The conversion manifest](../sources/documentation/conversion_manifest.json) records hashes, bookmarks, tables, image provenance, forms and resolved links. [The block ledger](../sources/documentation/block_coverage.json) records the disposition of every body block.

Only automatic Word contents caches, repeated contents headings and page-layout furniture are replaced by repository navigation. Explicit paragraph/list numbering, tables, examples, source references, cached cross-reference labels, required/optional language and working placeholders are preserved. Named Word bookmarks become explicit Markdown HTML anchors. External source links are retained, **not freshly researched or re-certified**.

The source set contains no unresolved tracked edits, embedded objects, text boxes, footnotes, endnotes or merged table cells requiring a lossy conversion. The converter refuses those unsupported content shapes instead of claiming complete conversion when it cannot preserve them.

## Decisions and status

[ADR-0003 through ADR-0036](adr/README.md) are source-derived decision records. They preserve the original AD-01–AD-15, RD14-01–RD14-05 and DEV-ADR-01 relationships while adding chapter-derived decisions for architecture and engineering concerns already present in the sources. They remain proposed, with accepting authority and evidence **not recorded**. Alternatives are not invented as past meetings. Context and consequences are identified as source-derived synthesis.

ADR-0001 is the original repository-organization decision. ADR-0002 is the new proposed publishing convention. It does not issue an architecture or security approval.

## Missing sources and historical conflicts

The standalone RAD/TAD/solution-design v1.2 package described earlier in the conversation was not available in the supplied repository bytes. This migration does **not** fabricate its original documents. [RAD](architecture/RAD.md) and [TAD](engineering/TAD.md) are new navigation/composition views of content that is actually present. Public-service content is included only to the extent that the available chapters describe it; no missing worked public-service design is reconstructed.

The v1.0 and v1.1 handbook and the v1.2 content-review branch retain historical differences. [The archive](archive/README.md) warns against using them as the active baseline. Removing old schemas from a main narrative does not repair their implementation. Earlier audit findings remain findings against their stated source edition; this migration makes no new closure claim.

## Edit and regenerate safely

Markdown is the working Git review surface. Make substantive changes in a review branch, link the affected ADR and requirement, and update engineering, implementation and verification consequences. Do not modify frozen originals or retroactively edit their evidence.

Source refresh is deliberately explicit and replaces converted chapter text. Run it only in a clean review worktree where the resulting diff can be assessed:

```sh
python scripts/convert_word_docs.py --refresh-from-frozen-sources
python scripts/build_documentation.py
python scripts/catalog_artifacts.py
python scripts/check_documentation.py
python scripts/check_repository.py
```

The converter reads local sources only and never contacts infrastructure. `build_documentation.py` generates reviewed navigation/ADR material from the checked-in records and adds decision backlinks. It is not an acceptance engine. CI checks documentation and never automatically regenerates or commits source refreshes.

Generated navigation is described in `sources/documentation/integration_outputs.json`; source prose remains separate from source-derived ADR synthesis. A future adopted source revision should get an explicit new source record and reviewed migration—not an ambiguous replacement under an old hash.

## Validation boundaries

The documentation checker independently renders Markdown, checks source paragraph/cell text, table dimensions, field placeholders, image bytes, local file and anchor links, unique destinations, requirement references and decision crosswalks. It checks publishing consistency only. External URLs are not crawled. Existing native code and historical evidence are retained; no Terraform/Ansible engine run, remote CI result, target observation, deployment or authorization is implied.

## Local commit

This deliverable is a repository snapshot, not a `.git` checkout. No remote branch was modified. Existing users should use the documentation update procedure in [LOCAL_IMPORT.md](LOCAL_IMPORT.md), not blindly overwrite a working tree or run the original first-import helper against an already populated repository.


## Corrective authoring model — CA-04/05

Converted chapters are immutable transcriptions, including original proposal and historical evidence states. Maintained designs live under [docs/current](current/README.md), with owner role, scope, version, parent sections and change history. They can be edited without repeating superseded source paragraphs; their structural gate does not claim semantic or organizational approval. Frozen-source refresh is explicitly prohibited from targeting those maintained paths. ADR source records own the generated ADR pages and lifecycle; the checker reconciles exact rendering, indexes and valid governance fields. Non-Proposed states need real decision authority/date/record/evidence and supersession consistency. No current ADR was automatically accepted.
