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
    conversion=ROOT/'sources/documentation/conversion_manifest.json'
    converted={}
    if conversion.exists():
        converted={d['source']:d for d in json.loads(conversion.read_text())['documents']}
    lines=['# Artifact and Markdown catalogue','','Read the full chapter content in Git; keep the original files as provenance. Source conversion does not change an approval or test result.',
           '', '| Artifact | Role | Read the content | Original source |','|---|---|---|---|']
    for r in rows:
        d=converted.get(r['path'])
        md=('[Markdown chapters](../'+quote(d['index'])+')'+(' — historical' if d['historical'] else '')) if d else 'Workbook retained in its original format'
        lines.append(f"| `{r['id']}` | {r['role']} | {md} | [{r['title']}](../{quote(r['path'])}) |")
    lines += ['', 'The current source set is Increment 04 plus its embedded delivery-kit v1.1 / architecture v1.4 library, and four explicitly archived historical source documents.',
              'The standalone RAD/TAD v1.2 package was not available. [RAD](architecture/RAD.md) and [TAD](engineering/TAD.md) are composed reading views over the available converted content, not invented originals.',
              '', '[Documentation home](README.md) · [Conversion coverage](DOCUMENTATION_MIGRATION.md)', '']
    (ROOT/'docs/ARTIFACT_CATALOG.md').write_text('\n'.join(lines))
    print(f'Indexed {len(rows)} actual Word/Excel/PDF files.')
if __name__=='__main__':main()
