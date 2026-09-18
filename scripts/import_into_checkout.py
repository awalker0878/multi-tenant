#!/usr/bin/env python3
"""Dry-run-first overlay import. Never stages, commits, pushes or deletes checkout files."""
from __future__ import annotations
import argparse,hashlib,json,os,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.check_release import verify
REMOTE_FORMS={'https://github.com/awalker0878/multi-tenant.git','https://github.com/awalker0878/multi-tenant','git@github.com:awalker0878/multi-tenant.git','ssh://git@github.com/awalker0878/multi-tenant.git'}
EXCLUDE={'.git','.venv','__pycache__','build','dist'}

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def git(path,*args):
    r=subprocess.run(['git','-C',str(path),*args],capture_output=True,text=True,timeout=30)
    if r.returncode:raise ValueError('Git preflight failed: '+ ' '.join(args))
    return r.stdout.strip()

def plan(destination,source=ROOT):
    destination=Path(destination)
    if not destination.is_absolute():destination=destination.absolute()
    for p in (destination,*destination.parents):
        if p.is_symlink():raise ValueError('Destination symlinks are not permitted')
    destination=destination.resolve();source=source.resolve()
    if destination==source or source.is_relative_to(destination) or destination.is_relative_to(source):raise ValueError('Source and checkout must be separate directories')
    if Path(git(destination,'rev-parse','--show-toplevel')).resolve()!=destination:raise ValueError('Target must be the Git checkout root')
    if git(destination,'remote','get-url','origin') not in REMOTE_FORMS:raise ValueError('Origin is not the expected multi-tenant repository')
    if git(destination,'branch','--show-current')!='main':raise ValueError('Use the intended clean main checkout; create a review branch after import')
    if git(destination,'status','--porcelain','--untracked-files=all'):raise ValueError('Checkout has local changes; commit or preserve them before import')
    integrity=verify(source)
    if integrity['issues']:raise ValueError('Source ZIP release hashes do not match')
    manifest=json.loads((source/'sources/release_manifest.json').read_text())['file_sha256']
    names=sorted([*manifest,'sources/release_manifest.json'])
    initial=(source/'evidence/imported/github-initial-README.md').read_bytes()
    rows=[]
    for name in names:
        rel=Path(name)
        if rel.is_absolute() or '..' in rel.parts or any(x in EXCLUDE for x in rel.parts):raise ValueError('Unsafe source path')
        src=source/rel;dst=destination/rel
        for parent in (dst,*dst.parents):
            if parent==destination:break
            if parent.is_symlink():raise ValueError('Symlink collision: '+name)
        if dst.exists():
            if not dst.is_file():raise ValueError('Non-file collision: '+name)
            if sha(dst)==sha(src):action='UNCHANGED'
            elif name=='README.md' and dst.read_bytes()==initial:action='REPLACE_INITIAL_README'
            else:raise ValueError('Unapproved file collision: '+name)
        else:action='ADD'
        rows.append({'path':name,'action':action,'source_sha256':sha(src),
                     'before_sha256':sha(dst) if dst.exists() else None})
    return rows

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('checkout',type=Path);p.add_argument('--apply',action='store_true');a=p.parse_args()
    try:
        rows=plan(a.checkout);counts={k:sum(r['action']==k for r in rows) for k in ('ADD','REPLACE_INITIAL_README','UNCHANGED')}
        print(json.dumps({'mode':'COPY' if a.apply else 'DRY_RUN','files':counts,'git_writes':False},indent=2))
        if not a.apply:return 0
        # Recheck content before each write; stop rather than overwrite a newly changed file.
        for r in rows:
            if r['action']=='UNCHANGED':continue
            src=ROOT/r['path'];dst=a.checkout.resolve()/r['path']
            for candidate in (dst, *dst.parents):
                if candidate == a.checkout.resolve():break
                if candidate.is_symlink():raise ValueError('Symlink appeared during import')
            if sha(src)!=r['source_sha256']:raise ValueError('Source changed during import')
            if dst.exists() and (not dst.is_file() or sha(dst)!=r['before_sha256']):raise ValueError('Destination changed during import')
            if not dst.exists() and r['before_sha256'] is not None:raise ValueError('Destination disappeared during import')
            dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
        print('Copied working-tree files only. Review git diff and git status; commit and push yourself.')
        return 0
    except (ValueError,OSError,subprocess.SubprocessError) as e:
        print('IMPORT REFUSED: '+str(e),file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
