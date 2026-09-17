#!/usr/bin/env python3
"""Index the actual frozen document library without copying or rewriting its files."""
from pathlib import Path
import hashlib, json
from urllib.parse import quote
ROOT=Path(__file__).resolve().parents[1]

def collect(root=ROOT):
    rows=[]
    for p in sorted(root.rglob('*')):
        rel=p.relative_to(root)
        if not p.is_file() or p.is_symlink() or p.suffix.lower() not in ('.docx','.xlsx','.pdf'):
            continue
        if any(x in rel.parts for x in ('build','.git','.venv','evidence')):
            continue
        text=rel.as_posix()
        role=('architecture' if '01_Architecture' in text or '05_Reference' in text else
              'engineering' if '02_Engineering' in text else
              'implementation' if '03_Implementation' in text or len(rel.parts)==1 else 'shared')
        rows.append({'id':'ART-'+hashlib.sha256(text.encode()).hexdigest()[:12],
                     'path':text,'role':role,'title':p.stem.replace('_',' '),
                     'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
                     'status':'IMPORTED_UNCHANGED_NOT_REAPPROVED'})
    return rows

def main():
    rows=collect();(ROOT/'sources/artifact_catalog.json').write_text(json.dumps(rows,indent=2)+'\n')
    lines=['# Artifact catalogue','','Generated from the actual files in this repository. Titles are filename labels, not inferred approval.',
           'Reference files remain unchanged; actual site records and live evidence must stay outside source control.',
           '', '| Artifact | Role | File |','|---|---|---|']
    for r in rows:
        lines.append(f"| `{r['id']}` | {r['role']} | [{r['title']}](../{quote(r['path'])}) |")
    lines += ['', 'This import includes Increment 04 and its embedded delivery-kit v1.1 / architecture v1.4 library.',
              'Separately described RAD/TAD v1.2 artifacts were not present in the supplied archive; this catalogue does not claim to contain them.', '']
    (ROOT/'docs/ARTIFACT_CATALOG.md').write_text('\n'.join(lines))
    print(f'Indexed {len(rows)} actual Word/Excel/PDF files.')
if __name__=='__main__':main()
