#!/usr/bin/env python3
"""Write the current source-release byte inventory after reviewed changes.

Excludes its own manifest, Git/runtime caches, mutable local reports and retained
engine output. A manifest authenticates nothing by itself. Never used to claim tests.
"""
from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
EXCLUDE={'.git','.venv','build','__pycache__','.pytest_cache','.terraform','node_modules','dist'}
def selected(root):
    return [p for p in sorted(root.rglob('*')) if p.is_file() and not any(x in EXCLUDE for x in p.relative_to(root).parts)
            and p.relative_to(root).as_posix() not in ('sources/release_manifest.json','.github/workflows/audit-prepare.yml','.audit-apply.py')
            and not p.name.startswith('.audit-payload-')
            and p.suffix not in ('.pyc','.pyo')]
def write(root=ROOT):
    rows={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in selected(root)}
    record={'kind':'CURRENT_REPOSITORY_SOURCE_RELEASE','scope':'Current selected source and documentation bytes, not signature/authentication or native qualification',
            'historical_manifest':'sources/documentation/history/pre-audit-release-manifest.json','file_sha256':rows}
    (root/'sources/release_manifest.json').write_text(json.dumps(record,indent=2)+'\n');print(len(rows),'source files recorded')
if __name__=='__main__':write()
