#!/usr/bin/env python3
"""Record successful hosted preparation results, actual locks, and tested source hashes.

Does not upgrade native-qualification or organizational decision status. Run only
when the actual engine commands already succeeded; validates report contents.
"""
import hashlib,json,os,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 q=ROOT/'build/reports';out=ROOT/'evidence/completion-audit';out.mkdir(parents=True,exist_ok=True)
 tf=json.loads((q/'terraform_validation.json').read_text());an=json.loads((q/'ansible_validation.json').read_text());local=json.loads((q/'local_validation.json').read_text());docs=json.loads((q/'documentation_validation.json').read_text());repo=json.loads((q/'repository_check.json').read_text());locks=json.loads((q/'provider_lock_review.json').read_text())
 assert tf['status']=='PASSED_TOOLCHAIN_ONLY',tf['status']
 assert not locks['errors']
 assert local['unit_and_source_tests']['failures']==0 and local['unit_and_source_tests']['errors']==0
 assert docs['status']=='PASSED' and not repo['issues']
 assert an['status']=='PASSED_LOCAL_ANSIBLE_ONLY',an['status']
 for name in ('terraform_validation.json','ansible_validation.json','local_validation.json','provider_lock_review.json'):
  shutil.copy2(q/name,out/name)
 compact={'status':'PASSED_SOURCE_AND_HOSTED_ENGINE_PREPARATION','workflow_run_id':os.environ['GITHUB_RUN_ID'],
  'workflow_attempt':os.environ.get('GITHUB_RUN_ATTEMPT'), 'preparation_commit':os.environ['GITHUB_SHA'],
  'repository':os.environ['GITHUB_REPOSITORY'],'source_hashes':{},'documentation_metrics':docs['metrics'],
  'repository_check':repo,'native_platform_tests':'NOT_RUN','organizational_acceptance':'NOT_ISSUED',
  'scope':'Preparation commit generated readable source and real dependency locks. Final PR commit reruns the independent read-only checks; use that exact PR status before merge.'}
 for base in ('scripts','tests','tools','terraform'):
  for p in sorted((ROOT/base).rglob('*')):
   if p.is_file() and '__pycache__' not in p.parts and '.terraform' not in p.parts:
    compact['source_hashes'][p.relative_to(ROOT).as_posix()]=hashlib.sha256(p.read_bytes()).hexdigest()
 (out/'preparation_validation.json').write_text(json.dumps(compact,indent=2)+'\n')
 (out/'README.md').write_text('''# Completion-audit validation evidence

These are actual source/engine results produced by the correction-branch hosted job.
The preparation record binds its source hashes and workflow run. The final PR commit
must pass the independent read-only jobs before merge; no native target test, issuer
approval or production authorization is implied. Full schema output remains a workflow
artifact; provider locks are committed as reviewed source with their actual checksums.

The earlier completion audit and older implementation results remain historical.
[Correction status](../../docs/assurance/completion-audit.md) distinguishes repaired
source defects from still-open native qualification and unavailable original sources.
''')
 print('Recorded actual hosted preparation evidence; no native qualification claimed')
if __name__=='__main__':main()
