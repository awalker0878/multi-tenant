"""Check one active publication authority after merging correction variants.

This rejects orphan duplicate ADR pages and nonempty retired amendment records.
Aliases are navigation only. The record does not approve an architecture or infer
that an old finding is resolved just because its publication path changed.
"""
from pathlib import Path
import hashlib,json,re
from build_documentation import Builder


def alias_text(row):
    return f'''# Decision link relocated — {row['id']}

This is a navigation alias, not a second decision or a lifecycle supersession.
Read the [canonical {row['id']} record]({Path(row['target']).name}); its status and governance are
rendered from `sources/documentation/adr_records.json`.

The earlier duplicate wording remains in Git history. No record was accepted,
rejected or superseded by consolidating these filenames.

[Integration audit](../assurance/main-integration-audit.md)
'''


def check(root):
    errors=[];aliases=[]
    try:
        data=json.loads((root/'sources/documentation/integration_authority.json').read_text())
        builder=Builder(root)
        active={row['id']:builder.adrpath(row) for row in builder.adrs}
        aliases=data['path_aliases']
        expected=set(active.values())|{'docs/adr/0001-architecture-first-repository.md',
                                     'docs/adr/0002-markdown-first-source-backed-documentation.md'}
        seen=set()
        for row in aliases:
            rel=row['path'];target=row['target']
            if row['id'] not in active or target!=active[row['id']]:errors.append('Alias target is not the canonical ADR')
            if rel in expected or rel in seen:errors.append('Duplicate alias or collision with a canonical ADR')
            seen.add(rel)
            p=root/rel
            if not rel.startswith('docs/adr/') or not p.resolve().is_relative_to((root/'docs/adr').resolve()):
                errors.append('Alias outside decision directory');continue
            if p.is_symlink() or not p.is_file() or p.read_text()!=alias_text(row):errors.append('Alias is not a pure navigation record: '+rel)
        numbered={p.relative_to(root).as_posix() for p in (root/'docs/adr').glob('*.md') if re.match(r'^\d{4}-',p.name)}
        if numbered!=expected|seen:errors.append('Numbered ADR files differ from canonical records and explicit aliases')
        for row in data['historical_views']:
            p=root/row['path'];target=root/row['target']
            if not p.is_file() or not p.read_text().startswith('<!-- RETAINED-HISTORICAL-PROPOSAL -->') or not target.is_file():
                errors.append('Historical proposal lacks a visible current-authority boundary: '+row['path'])
            archive=root/row['archived_path']
            if not archive.is_file() or hashlib.sha256(archive.read_bytes()).hexdigest()!=row['previous_blob_sha256']:
                errors.append('Original generated proposal was not preserved byte-for-byte: '+row['path'])
        canonical={
            'adr_records':'sources/documentation/adr_records.json','adr_logic':'scripts/adr_lifecycle.py',
            'maintained_design_records':'sources/documentation/current_design_records.json',
            'maintained_design_directory':'docs/current','source_structure_checker':'scripts/documentation_structure.py',
            'allocation':'sources/assurance/implementation_assertions.json',
            'assurance_builder':'scripts/build_assurance_indexes.py','history':'sources/assurance/historical_audit_dispositions.csv'}
        if data['canonical']!=canonical or any(not (root/path).exists() for path in canonical.values()):
            errors.append('Canonical documentation authority is incomplete or changed without checker review')
        if json.loads((root/data['inactive_amendments']).read_text())!=[]:
            errors.append('Retired source-block amendment ledger must not become a second active authoring surface')
        for rel in data['retained_inactive_records']:
            if not (root/rel).is_file():errors.append('Historical proposal source removed: '+rel)
    except (OSError,ValueError,KeyError,TypeError) as exc:
        errors.append('Invalid integration record: '+type(exc).__name__)
    return {'errors':errors,'decision_aliases':len(aliases),
            'scope':'Publication consistency only; no acceptance or historical finding closure'}
