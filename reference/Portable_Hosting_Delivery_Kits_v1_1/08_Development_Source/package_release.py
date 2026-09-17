"""Package this document release after its current local checks pass.

Writes only the validation report, release manifest, checksum list and requested ZIP.
No infrastructure or workbook calculation is performed.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile
from validate_release import validate


def included(root: Path):
    return sorted(p for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts
                  and p.suffix!='.pyc' and p.relative_to(root).as_posix() not in ('RELEASE_MANIFEST.json','SHA256SUMS'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--archive',type=Path,required=True)
    args=parser.parse_args();root=args.root.resolve();archive=args.archive.resolve()
    try:archive.relative_to(root)
    except ValueError:pass
    else:
        print('Keep the output archive outside the release directory.',file=sys.stderr);return 2
    try:
        report=validate(root)
        (root/'07_Quality/v1_1/validation_report.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
        if report['failed']:
            print('Packaging stopped: local validation has failures.',file=sys.stderr);return 1
        paths=included(root)
        symlinks=[p for p in paths if p.is_symlink()]
        if symlinks:raise ValueError('Do not package symbolic links: '+str(symlinks))
        manifest={'release':'Portable Hosting Delivery Kits v1.1','reference_architecture':'Frozen v1.4',
                  'scope':'Reference document development; no infrastructure execution, actual site acceptance or authorization',
                  'manifest_exclusions':['RELEASE_MANIFEST.json','SHA256SUMS','__pycache__ and .pyc'],
                  'local_checks':{'passed':report['passed'],'failed':report['failed']},'files':[]}
        for p in paths:
            manifest['files'].append({'path':p.relative_to(root).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
        m=root/'RELEASE_MANIFEST.json';m.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
        sums=[(entry['path'],entry['sha256']) for entry in manifest['files']]
        sums.append(('RELEASE_MANIFEST.json',hashlib.sha256(m.read_bytes()).hexdigest()))
        (root/'SHA256SUMS').write_text(''.join(f'{h}  {p}\n' for p,h in sorted(sums)))
        archive.parent.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
            for p in paths+[m,root/'SHA256SUMS']:
                z.write(p,root.name+'/'+p.relative_to(root).as_posix())
        with zipfile.ZipFile(archive) as z:
            bad=z.testzip()
            if bad:raise ValueError('ZIP integrity failure: '+bad)
        print(json.dumps({'archive':str(archive),'files':len(paths)+2,'bytes':archive.stat().st_size,
              'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'local_checks':manifest['local_checks']},indent=2))
        return 0
    except (OSError,ValueError,KeyError,zipfile.BadZipFile) as e:
        print(f'Packaging failed: {e}',file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())
