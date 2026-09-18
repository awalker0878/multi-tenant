#!/usr/bin/env python3
"""Actual Ansible syntax and localhost staging tests when an engine is installed.

No native-contact option exists in these playbooks. Missing binaries fail this gate.
"""
from __future__ import annotations
import argparse,hashlib,json,os,re,shutil,subprocess,sys,tempfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=ROOT/'build/reports/ansible_validation.json');a=p.parse_args()
    started=time.monotonic();report={'kind':'ANSIBLE_ENGINE_CHECK','status':'NOT_RUN','checks':[],'native_target_contacted':False,'native_configuration_changed':False}
    def finish(status,reason=None):
        report['status']=status;report['elapsed_seconds']=round(time.monotonic()-started,3)
        if reason:report['reason']=reason
        a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));return 0 if status=='PASSED_LOCAL_ANSIBLE_ONLY' else 2
    binary=shutil.which('ansible-playbook')
    if not binary:return finish('BLOCKED_TOOLCHAIN','ansible-playbook executable is not installed')
    with tempfile.TemporaryDirectory(prefix='hosting-ansible-') as tmp:
        tmp=Path(tmp);staging=tmp/'staging';staging.mkdir(mode=0o700);(staging/'.hosting-staging').write_text('HOSTING_STAGING_ONLY\n')
        home=tmp/'home';home.mkdir()
        env={k:v for k,v in os.environ.items() if not k.startswith(('ANSIBLE_','TF_VAR_','OS_','NSXT_','NUTANIX_','VSPHERE_'))}
        env.update(HOME=str(home),ANSIBLE_CONFIG=str(ROOT/'ansible/ansible.cfg'),ANSIBLE_FORCE_COLOR='false',ANSIBLE_NOCOLOR='1',ANSIBLE_LOCAL_TEMP=str(tmp/'ansible-tmp'))
        base=[binary,'-i',str(ROOT/'ansible/inventories/localhost.yml')]
        vars=json.loads((ROOT/'ansible/fixtures/reference_bundle.json').read_text());vars.update(hosting_stage_enabled=True,hosting_staging_root=str(staging),ansible_python_interpreter=sys.executable)
        varfile=tmp/'vars.json';varfile.write_text(json.dumps(vars))
        def run(name,play,extra=None,expect_failure=False,zero_changes=False):
            argv=base+[str(ROOT/'ansible/playbooks'/play),'-e','@'+str(varfile),*(extra or [])]
            try:r=subprocess.run(argv,cwd=ROOT/'ansible',env=env,capture_output=True,text=True,timeout=120);stdout=r.stdout;code=r.returncode;stderr=r.stderr
            except subprocess.TimeoutExpired:stdout='';code=124;stderr='Timeout'
            recap=re.findall(r'localhost\s*:\s*ok=\d+\s+changed=(\d+)\s+unreachable=(\d+)\s+failed=(\d+)',stdout)
            passed=(code!=0) if expect_failure else (code==0 and (not zero_changes or (bool(recap) and recap[-1]==('0','0','0'))))
            report['checks'].append({'name':name,'passed':passed,'exit_code':code,'expect_failure':expect_failure,'stdout':stdout[-7000:],'stderr':stderr[-2000:]})
            return passed
        version=subprocess.run([binary,'--version'],capture_output=True,text=True,env=env,timeout=30)
        report['version_output']=version.stdout.splitlines()[0] if version.stdout else ''
        if version.returncode:return finish('BLOCKED_TOOLCHAIN','Cannot query Ansible version')
        for play in ('stage_reference.yml','validate_readback.yml'):run('syntax-'+play,play,['--syntax-check'])
        if any(not row['passed'] for row in report['checks']):return finish('FAILED_ANSIBLE_CHECK','Syntax failure')
        run('stage-first','stage_reference.yml');run('stage-second-idempotent','stage_reference.yml',zero_changes=True)
        directory=staging/'tenant-01--D01O'
        before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.glob('*') if p.is_file()}
        if not before:return finish('FAILED_ANSIBLE_CHECK','No staging artifacts')
        vars['hosting_bundle']['engineering_record_ref']='EXAMPLE-ENG-CHANGED';varfile.write_text(json.dumps(vars))
        run('check-mode-drift','stage_reference.yml',['--check'])
        after={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.glob('*') if p.is_file()}
        report['checks'].append({'name':'check-mode-does-not-mutate','passed':before==after})
        vars['hosting_stage_enabled']=False;varfile.write_text(json.dumps(vars));run('disabled-opt-in-rejected','stage_reference.yml',expect_failure=True)
        vars['hosting_stage_enabled']=True;vars['hosting_bundle']['routes'][0]['owner']='D02O';varfile.write_text(json.dumps(vars));run('foreign-route-rejected','stage_reference.yml',expect_failure=True)
        for platform in ('nsx','nutanix'):
            vars.update(hosting_platform=platform,hosting_manifest_path=str(ROOT/f'examples/{platform}_observation.json.example'));varfile.write_text(json.dumps(vars))
            run(platform+'-validation-no-contact','validate_readback.yml',zero_changes=True)
        try:
            handoff=json.loads((directory/'engineering-handoff.json').read_text())
            safe=handoff['may_apply'] is False and handoff['may_activate'] is False
        except (ValueError,KeyError,OSError):safe=False
        report['checks'].append({'name':'staged-handoff-never-authorizes','passed':safe})
    return finish('PASSED_LOCAL_ANSIBLE_ONLY' if all(c['passed'] for c in report['checks']) else 'FAILED_ANSIBLE_CHECK')
if __name__=='__main__':raise SystemExit(main())
