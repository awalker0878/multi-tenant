#!/usr/bin/env python3
"""Read-only current-checkout integrity, or an explicitly supplied export manifest.

In Git, compare tracked worktree bytes against HEAD and flag untracked/unignored
files. This is consistency with the current commit, not signer trust or approval.
An exported ZIP requires --manifest pointing to its newly generated snapshot; the
historical increment manifest is never silently used as a current release gate.
"""
from __future__ import annotations
import argparse, hashlib, json, subprocess
from pathlib import Path, PurePosixPath
ROOT=Path(__file__).resolve().parents[1]


def verify_snapshot(root,manifest_path):
    issues=[];count=0;root=root.resolve()
    try:
        data=json.loads(manifest_path.read_text());items=data['file_sha256']
        if not isinstance(items,dict) or not items:raise ValueError('Empty digest map')
        for name,digest in items.items():
            rel=PurePosixPath(name)
            if rel.is_absolute() or '..' in rel.parts or '.git' in rel.parts or '\\' in name or ':' in name:
                raise ValueError('Unsafe snapshot path')
            path=root/name;count+=1
            if not path.resolve().is_relative_to(root) or path.is_symlink():issues.append({'kind':'UNSAFE_PATH','file':name})
            elif not path.is_file():issues.append({'kind':'MISSING_FILE','file':name})
            elif hashlib.sha256(path.read_bytes()).hexdigest()!=digest:issues.append({'kind':'DIGEST_MISMATCH','file':name})
    except (OSError,ValueError,KeyError,TypeError):issues.append({'kind':'INVALID_SNAPSHOT_MANIFEST'})
    return {'status':'HASHES_MATCH' if not issues else 'FAILED_INTEGRITY_CHECK','files_checked':count,'issues':issues,'scope':'Explicit export manifest; not signature or native qualification.'}


def verify(root=ROOT):
    root=root.resolve();issues=[];count=0
    def git(*args):return subprocess.check_output(['git','-C',str(root),*args],stderr=subprocess.PIPE,timeout=60)
    try:
        if Path(git('rev-parse','--show-toplevel').decode().strip()).resolve()!=root:raise ValueError('Not repository root')
        commit=git('rev-parse','HEAD').decode().strip()
        for record in git('ls-tree','-rz','--full-tree','HEAD').split(b'\0'):
            if not record:continue
            meta,name=record.split(b'\t',1);mode,typ,expected=meta.split();relative=name.decode('utf-8');path=root/relative;count+=1
            if typ!=b'blob' or mode not in (b'100644',b'100755') or path.is_symlink() or not path.resolve().is_relative_to(root):
                issues.append({'kind':'UNSUPPORTED_OR_UNSAFE_TRACKED_PATH','file':relative});continue
            if not path.is_file():issues.append({'kind':'MISSING_TRACKED_FILE','file':relative});continue
            data=path.read_bytes();actual=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
            if actual!=expected.decode():issues.append({'kind':'WORKTREE_DIFFERS_FROM_HEAD','file':relative})
        for path in git('ls-files','--others','--exclude-standard','-z').split(b'\0'):
            if path:issues.append({'kind':'UNTRACKED_SOURCE_FILE','file':path.decode('utf-8')})
        if git('diff','--cached','--name-only').strip():issues.append({'kind':'INDEX_DIFFERS_FROM_HEAD'})
    except (OSError,ValueError,subprocess.SubprocessError):
        return {'status':'BLOCKED_NO_CURRENT_CHECKOUT','files_checked':count,'issues':[{'kind':'CURRENT_GIT_CHECKOUT_REQUIRED','action':'For a source export explicitly supply its current --manifest.'}]}
    return {'status':'HASHES_MATCH' if not issues else 'FAILED_INTEGRITY_CHECK','commit':commit,'files_checked':count,'issues':issues,'scope':'Tracked worktree bytes equal current Git HEAD; not signature, architecture approval or native qualification.'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path);args=p.parse_args()
    result=verify_snapshot(ROOT,args.manifest) if args.manifest else verify(ROOT)
    print(json.dumps(result,indent=2));raise SystemExit(0 if not result['issues'] else 1)
