"""Temporary branch-only installer of a reviewed, checksum-bound source delta.

All payload paths are preflighted against the audited main bytes. It runs no native
infrastructure commands. Removed before the readable source/lock commit is published.
"""
from pathlib import Path,PurePosixPath
import base64,hashlib,json,lzma,os,shutil,subprocess,sys
R=Path.cwd().resolve()
EXPECTED='68ea0df4855569d59c4d3c2a80a077e437ea56e15804abe62f09ccdacd811de0'
parts=[R/f'.audit-payload-{i:02d}.b64' for i in range(13)]
assert set(R.glob('.audit-payload-*.b64'))==set(parts),'Unexpected/missing payload part'
packed=base64.b64decode(''.join(p.read_text().strip() for p in parts),validate=True)
assert hashlib.sha256(packed).hexdigest()==EXPECTED,'Payload digest mismatch'
decoder=lzma.LZMADecompressor();raw=decoder.decompress(packed,max_length=8_000_001)
assert decoder.eof and not decoder.unused_data and len(raw)<=8_000_000,'Payload size/trailing data'
def unique(pairs):
 d={}
 for k,v in pairs:
  if k in d:raise ValueError('Duplicate payload key')
  d[k]=v
 return d
bundle=json.loads(raw,object_pairs_hook=unique)
assert bundle['format']=='reviewed-exact-source-delta-v1'
subprocess.run(['git','merge-base','--is-ancestor',bundle['baseline_commit'],'HEAD'],check=True)
seen=set()
for f in bundle['files']:
 rel=f['path'];p=PurePosixPath(rel)
 assert rel not in seen and not p.is_absolute() and '..' not in p.parts and '.git' not in p.parts and '\\' not in rel and ':' not in rel
 assert rel.startswith(('scripts/','tools/','tests/','sources/','docs/')) or rel=='README.md'
 assert not rel.startswith(('.github/','terraform/','reference/'))
 seen.add(rel);target=R/rel
 assert not any(x.is_symlink() for x in (target,*target.parents) if x.is_relative_to(R))
 current=hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else None
 assert current==f['before_sha256'],f'Unexpected source baseline: {rel}'
 if 'patch' in f:
  assert f['before_sha256'] is not None
  subprocess.run(['git','apply','--check','--whitespace=nowarn','-'],input=f['patch'].encode(),check=True)
 else:assert f['before_sha256'] is None and hashlib.sha256(f['content'].encode()).hexdigest()==f['after_sha256']
history=R/'sources/documentation/history/pre-audit-release-manifest.json';history.parent.mkdir(parents=True,exist_ok=True)
assert not history.exists();shutil.copy2(R/'sources/release_manifest.json',history)
for f in bundle['files']:
 target=R/f['path']
 if 'patch' in f:subprocess.run(['git','apply','--whitespace=nowarn','-'],input=f['patch'].encode(),check=True)
 else:target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(f['content'].encode('utf-8'))
 assert hashlib.sha256(target.read_bytes()).hexdigest()==f['after_sha256'],f'Applied delta mismatch: {f["path"]}'
subprocess.run([sys.executable,'scripts/migrations/seed_completion_allocations.py'],check=True)
sys.path.insert(0,str(R/'scripts'))
from convert_word_docs import build
build(R,allow_existing=True)  # One-time source-fidelity repair; originals are immutable.
subprocess.run([sys.executable,'scripts/build_documentation.py'],check=True)
subprocess.run([sys.executable,'scripts/build_assurance.py'],check=True)
source={'kind':'AUDITED_BASELINE_CORRECTION_INPUT','baseline_commit':bundle['baseline_commit'],'reviewed_delta_sha256':EXPECTED,
 'source_changes':[{k:v for k,v in f.items() if k not in ('content','patch')} for f in bundle['files']],
 'scope':'One-time documented source repair; no approvals or native writes.'}
(R/'sources/assurance/correction_input.json').write_text(json.dumps(source,indent=2)+'\n')
for p in parts:p.unlink()
(R/'.audit-apply.py').unlink()
print('Applied verified source corrections and generated readable documentation. Payload removed.')
