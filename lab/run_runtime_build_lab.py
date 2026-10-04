#!/usr/bin/env python3
"""Actual offline venv/pip/Terraform build; disposable candidate provenance only.

Downloads candidate wheels before the test, then runs every runtime subprocess in
an empty network namespace. No platform service or production artifact approval.
"""
import argparse
from copy import deepcopy
from datetime import timedelta
import email.parser
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from provisioner.execution import readback_core as c
from provisioner.execution import runtime_build as d
from provisioner.execution.source_integrity import _protected_checkout
from provisioner.execution.run_files import digest,encoded,require,utcnow,write_new


class EngineHost(d.Host):
    """Hosted tool cache custody is a fixture, not an accepted base OS image."""
    def __init__(self): self.commands=0
    def identity(self,config,root):
        source=d.verify(root)
        require(_protected_checkout(root) and source['status']=='HASHES_MATCH'
                and source['commit']==config['source_commit'],'Protected fixture checkout changed')
        require(digest(Path(config['python']).read_bytes())==config['python_sha256'],'Fixture Python changed')
    def command(self,argv,cwd):
        self.commands+=1
        result=subprocess.run(list(map(str,['/usr/bin/unshare','--net','--',*argv])),cwd=cwd,
            env=d.ENV.copy(),stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=300,umask=0o077)
        if result.returncode:
            # These are solely disposable public package fixtures, with no native
            # credentials. Preserve engine diagnostics for CI without retrying.
            print(result.stdout.decode(errors='replace')[-2000:])
            print(result.stderr.decode(errors='replace')[-4000:])
        require(result.returncode==0 and len(result.stdout)<=2*1024*1024,'Disposable runtime engine failed')
        return result.stdout.decode()


def authority(config):
    return dict(format='hosting-runtime-build-authority/1',config_sha256=c.digest(config),
        valid_from=(utcnow()-timedelta(minutes=1)).isoformat(),valid_until=(utcnow()+timedelta(minutes=20)).isoformat(),
        change_ref='DISPOSABLE-CANDIDATE-FIXTURE-ONLY')


def run(terraform):
    require(os.geteuid()==0 and Path('/usr/bin/unshare').is_file(),'Disposable network namespace lab requires root')
    require(platform.python_version().startswith('3.13.'),'Repository Python 3.13 engine required')
    source=d.verify(ROOT)
    require(_protected_checkout(ROOT) and source['status']=='HASHES_MATCH','Protected clean exact source fixture required')
    binary=Path(terraform).read_bytes()
    with tempfile.TemporaryDirectory(prefix='hosting-runtime-lab-',dir='/var/lib') as temporary:
        base=Path(temporary); wheelhouse=base/'candidates'; wheelhouse.mkdir(mode=0o700)
        # Candidate acquisition is deliberately outside the offline builder. The
        # selected versions/hashes here are test fixtures, never release approval.
        subprocess.run([sys.executable,'-I','-m','pip','download','--only-binary=:all:','--no-cache-dir',
            '--disable-pip-version-check','--dest',str(wheelhouse),'-r',str(ROOT/'requirements-repository.txt'),
            'pip=='+importlib.metadata.version('pip')],env=d.ENV.copy(),check=True,timeout=240)
        # The application runtime is an actual wheel built from this exact local
        # checkout; it is installed and byte-checked with the dependency wheels.
        wheel_source=base/'wheel-source'
        shutil.copytree(ROOT,wheel_source,ignore=shutil.ignore_patterns(
            '.git','build','dist','__pycache__','*.egg-info'))
        subprocess.run([sys.executable,'-I','-m','pip','wheel','--no-index','--no-deps',
            '--no-build-isolation','--wheel-dir',str(wheelhouse),str(wheel_source)],
            env=d.ENV.copy(),check=True,timeout=240)
        wheels=[]
        for path in sorted(wheelhouse.glob('*.whl')):
            path.chmod(0o600)
            with zipfile.ZipFile(path) as package:
                name=next(name for name in package.namelist() if name.endswith('.dist-info/METADATA') and name.count('/')==1)
                meta=email.parser.BytesParser().parsebytes(package.read(name))
            wheels.append(dict(name=d.normalized(meta['Name']),version=meta['Version'],path=str(path),sha256=digest(path.read_bytes())))
        archive=base/'terraform.zip'
        with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as package: package.writestr('terraform',binary)
        archive.chmod(0o600)
        config=dict(format='hosting-runtime-build/1',enabled=True,source_commit=source['commit'],python=str(Path(sys.executable).resolve()),
            python_sha256=digest(Path(sys.executable).read_bytes()),python_version=platform.python_version(),
            base_os_sha256=digest(Path('/etc/os-release').read_bytes()),base_runtime_ref='SYNTHETIC-HOSTED-BASE-NOT-IMAGE-PROVENANCE',
            artifact_acceptance_ref='SYNTHETIC-CANDIDATE-WHEELS-NOT-RELEASE-APPROVAL',wheels=wheels,output=str(base/'runtime'),
            terraform=dict(path=str(archive),sha256=digest(archive.read_bytes()),binary_sha256=digest(binary),version='1.13.5'))
        host=EngineHost()
        # Ambient install redirection must not affect the builder.
        hostile=base/'hostile-pip.conf'; hostile.write_text('[global]\nindex-url = https://unreachable.invalid/simple\n[install]\ntarget = /invalid-runtime-target\n')
        os.environ['PIP_CONFIG_FILE']=str(hostile); os.environ['PIP_TARGET']='/invalid-runtime-target'
        receipt=d.build(config,authority(config),host=host)
        require(receipt['packages'].get('ansible-core')=='2.19.7','Actual Ansible pin differs')
        calls=host.commands
        require(d.build(config,None,host=host,observe=True)==receipt and host.commands==calls,'Read-only repeat executed an engine')
        # Real ordinary imports must preserve the already sealed hash bytecode.
        python=Path(config['output'])/'env/bin/python'
        host.command([python,'-I','-c','import ansible, jinja2, yaml, dns.resolver, cryptography, provisioner.execution.owner_worker; print(ansible.__version__)'],base)
        d.build(config,None,host=host,observe=True)
        # Exercise the new operating identity with the *actual* sealed Python,
        # accepted application wheel and installed tree in an empty network
        # namespace. This is installation verification, not commissioning.
        identity_config=base/'installed-identity-config.json'
        write_new(identity_config,encoded(config))
        identity_code=('from pathlib import Path;import sys;'
            'from provisioner.controlplane.workflow.installed_identity import InstalledApplicationIdentity;'
            'identity=InstalledApplicationIdentity.from_configuration(Path(sys.argv[1]),Path(sys.argv[2]));'
            'assert identity.require_current()==(sys.argv[3],sys.argv[4]);'
            'print("SEALED_INSTALLED_IDENTITY_VERIFIED")')
        application=next(row for row in config['wheels'] if row['name']=='hosting-provisioner')
        identity_result=host.command([python,'-I','-B','-c',identity_code,identity_config,ROOT,
                                     source['commit'],application['sha256']],base)
        require(identity_result.strip()=='SEALED_INSTALLED_IDENTITY_VERIFIED',
                'Actual installed interpreter identity was not verified')
        # A transitive omission is permitted by the request schema but must fail
        # the actual offline dependency check, without a completed receipt.
        missing=deepcopy(config); missing['output']=str(base/'missing-dependency')
        require(any(w['name']=='packaging' for w in missing['wheels']),'Expected Ansible transitive package missing from fixture')
        missing['wheels']=[w for w in missing['wheels'] if w['name']!='packaging']
        try: d.build(missing,authority(missing),host=host)
        except ValueError: pass
        else: raise RuntimeError('Missing transitive dependency was accepted')
        require(not (Path(missing['output'])/'receipt.json').exists(),'Failed dependency build published completion')
        previous=host.commands
        try: d.build(missing,authority(missing),host=host)
        except ValueError: pass
        else: raise RuntimeError('Incomplete runtime was reused')
        require(host.commands==previous,'Incomplete build repeated an engine')
        path=Path(config['output'])/'bin/terraform'; path.write_bytes(b'CHANGED')
        try: d.build(config,None,host=host,observe=True)
        except ValueError: pass
        else: raise RuntimeError('Changed completed runtime was accepted')
        return dict(status='PASSED_OFFLINE_RUNTIME_ENGINE_ONLY',source_commit=source['commit'],python=platform.python_version(),
            packages=receipt['packages'],sealed_entries=len(receipt['files']),empty_network_namespace=True,
            offline_build=True,missing_dependency_held=True,incomplete_build_not_repeated=True,changed_runtime_held=True,
            ordinary_imports_preserve_seal=True,installed_identity_verified=True,
            production_activation=False,native_qualification=False,
            provenance='Disposable candidate wheel and Terraform packaging; hosted base custody not production-qualified')


def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--execute',action='store_true')
    parser.add_argument('--terraform',default=shutil.which('terraform')); args=parser.parse_args()
    if not args.execute: print('{"status":"NOT_RUN_USE_EXECUTE_FOR_DISPOSABLE_ENGINE_LAB"}'); return
    require(args.terraform is not None,'Actual pinned Terraform executable required')
    result=run(args.terraform)
    output=ROOT/'build/reports/runtime_build_lab.json'; output.parent.mkdir(parents=True,exist_ok=True)
    output.write_bytes(encoded(result)); print(json.dumps(result,indent=2))


if __name__=='__main__': main()
