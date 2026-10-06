#!/usr/bin/env python3
"""Source-bound real PostgreSQL execution qualification, preserving failed observations."""
import argparse
import hashlib
import json
import os
import platform
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    paths=subprocess.check_output(['git','ls-files'],cwd=ROOT,text=True).splitlines()
    report={'source_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'environment':platform.platform(),'evidence_level':'E2','native_platforms_tested':[],
            'source_bindings':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths if p.startswith(('services/lifecycle/','workers/lifecycle/','scripts/p06/','.github/workflows/p06','contracts/openapi/lifecycle-v1','contracts/openapi/assurance-evidence-v1','apps/console/resources/contracts/lifecycle-v1'))},'commands':[]}
    commands=[('.', ['python','scripts/p06/generate_contracts.py','--check'])]
    for component in ('services/lifecycle','workers/lifecycle'):
        commands += [(component,['uv','sync','--locked']),
                     (component,['uv','run','--frozen','ruff','check','src','tests']),
                     (component,['uv','run','--frozen','ruff','format','--check','src','tests']),
                     (component,['uv','run','--frozen','mypy','src','tests']),
                     (component,['uv','run','--frozen','pytest','-q','--junitxml='+str(out/(component.replace('/','-')+'.xml'))])]
    commands.append(('.', [str(ROOT/'services/lifecycle/.venv/bin/python'),'-m','pytest','scripts/p06','-q','--junitxml='+str(out/'execution.xml')]))
    env=os.environ|{'PYTHONPATH':':'.join(str(ROOT/p) for p in ('services/lifecycle/src','workers/lifecycle/src','services/lifecycle/tests'))}
    for i,(component,command) in enumerate(commands):
        run=subprocess.run(command,cwd=ROOT/component,env=env,capture_output=True,text=True,timeout=600)
        log=run.stdout+run.stderr;name=f'{i:02d}.log';(out/name).write_text(log)
        report['commands'].append({'component':component,'command':command,'exit_code':run.returncode,'log':name,'sha256':hashlib.sha256(log.encode()).hexdigest()})
        print(component,command[-2:],run.returncode,flush=True)
    report['result']='PASSED' if all(c['exit_code']==0 for c in report['commands']) else 'FAILED'
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    raise SystemExit(0 if report['result']=='PASSED' else 1)

if __name__=='__main__':main()
