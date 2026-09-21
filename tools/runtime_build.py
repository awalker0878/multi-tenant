#!/usr/bin/env python3
"""Build the pinned Linux execution runtime from an exact offline artifact set.

No resolver, download, package source build, account/service installation or native
platform contact. An interrupted output is retained and cannot be reused.
"""
import argparse
import email.parser
import fcntl
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
if __package__ in (None, ''): sys.path.insert(0, str(ROOT))
from tools import readback_core as c
from tools.check_release import verify
from tools.owner_install import installed_path
from tools.run_files import (current_window, digest, encoded, load_private, new_directory,
    private_path, read_private, require, sync_directory, utcnow, write_new)

MAX_ARCHIVE = 128 * 1024 * 1024
MAX_EXPANDED = 1024 * 1024 * 1024
ENV = {'PATH':'/usr/bin:/bin', 'LANG':'C.UTF-8', 'PIP_CONFIG_FILE':'/dev/null',
       'PIP_DISABLE_PIP_VERSION_CHECK':'1', 'CHECKPOINT_DISABLE':'1', 'TF_IN_AUTOMATION':'1'}
PROFILE_CODE = """import json,platform,sys,sysconfig
print(json.dumps(dict(version=platform.python_version(),implementation=platform.python_implementation(),
 platform=sys.platform,machine=platform.machine(),prefix=sys.prefix,base_prefix=sys.base_prefix,
 stdlib=sysconfig.get_path('stdlib'))))"""
PACKAGES_CODE = """import importlib.metadata,json,re,sys
items={}
for d in importlib.metadata.distributions():
 n=re.sub(r'[-_.]+','-',d.metadata['Name']).lower()
 if n in items: raise ValueError('Duplicate installed distribution')
 items[n]=d.version
print(json.dumps(dict(packages=items,prefix=sys.prefix,base_prefix=sys.base_prefix)))"""
PIP_CODE = "import sys,runpy;sys.path.insert(0,sys.argv.pop(1));runpy.run_module('pip',run_name='__main__')"


def normalized(name): return re.sub(r'[-_.]+', '-', name).lower()


def sha(value):
    require(isinstance(value,str) and re.fullmatch('[0-9a-f]{64}',value), 'Exact artifact SHA256 required')


def pins(root):
    """Read only the repository's fixed, pinned requirements include tree."""
    result = {}; seen = set()
    def visit(name):
        require(re.fullmatch(r'requirements-[a-z]+\.txt', name), 'Unsupported repository requirements include')
        if name in seen: return
        seen.add(name)
        for line in (root/name).read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line or line.startswith('#'): continue
            if line.startswith('-r '): visit(line[3:]); continue
            match = re.fullmatch(r'([A-Za-z0-9_.-]+)==([0-9][A-Za-z0-9.!+_-]*)', line)
            require(match is not None, 'Repository dependencies must remain exact pins')
            package,version = normalized(match[1]),match[2]
            require(package not in result or result[package]==version, 'Conflicting repository dependency pin')
            result[package]=version
    visit('requirements-repository.txt')
    return result


def validate(config, root=ROOT):
    c.exact_keys(config, {'format','enabled','source_commit','python','python_sha256','python_version',
        'base_os_sha256','base_runtime_ref','artifact_acceptance_ref','wheels','terraform','output'})
    require(config['format']=='hosting-runtime-build/1' and type(config['enabled']) is bool,
            'Exact runtime build profile required')
    require(isinstance(config['source_commit'],str) and re.fullmatch('[0-9a-f]{40}',config['source_commit']),
            'Exact source commit required')
    toolchain=json.loads((root/'config/toolchain.json').read_text(encoding='utf-8'))
    require(isinstance(config['python_version'],str) and re.fullmatch(re.escape(toolchain['python'])+r'\.[0-9]+',config['python_version']),
            'Accepted full Python version must match the repository minor version')
    for key in ('python','output'): installed_path(config[key])
    for key in ('python_sha256','base_os_sha256'): sha(config[key])
    for key in ('base_runtime_ref','artifact_acceptance_ref'): c.text(config[key])
    require(isinstance(config['wheels'],list) and 1<=len(config['wheels'])<=64, 'Bounded complete wheel set required')
    packages={}; paths=set()
    for wheel in config['wheels']:
        c.exact_keys(wheel, {'name','version','path','sha256'})
        require(isinstance(wheel['name'],str) and re.fullmatch('[a-z0-9]+(?:-[a-z0-9]+)*',wheel['name']),
                'Canonical wheel distribution name required')
        require(isinstance(wheel['version'],str) and re.fullmatch('[0-9][A-Za-z0-9.!+_-]*',wheel['version']),
                'Exact wheel version required')
        path=installed_path(wheel['path']); sha(wheel['sha256'])
        require(re.fullmatch(r'[A-Za-z0-9_.+-]+\.whl',path.name), 'Local wheel filename required')
        require(wheel['name'] not in packages and path.name not in paths, 'Duplicate wheel package or filename')
        packages[wheel['name']]=wheel['version']; paths.add(path.name)
    require('pip' in packages and all(packages.get(k)==v for k,v in pins(root).items()),
            'Complete accepted wheel set must include pip and every repository pin')
    archive=config['terraform']; c.exact_keys(archive,{'path','sha256','binary_sha256','version'})
    installed_path(archive['path']); sha(archive['sha256']); sha(archive['binary_sha256'])
    require(archive['version']==toolchain['terraform'], 'Terraform version differs from repository pin')
    output=Path(config['output'])
    require(not output.resolve().is_relative_to(root.resolve()) and not root.resolve().is_relative_to(output.resolve()),
            'Runtime destination must be separate from source')
    for path in [config['python'],archive['path'],*(item['path'] for item in config['wheels'])]:
        require(not Path(path).resolve().is_relative_to(output.resolve()), 'Build inputs cannot be inside the output')


def authorize(config, authority):
    c.exact_keys(authority,{'format','config_sha256','valid_from','valid_until','change_ref'})
    require(authority['format']=='hosting-runtime-build-authority/1' and authority['config_sha256']==c.digest(config),
            'Exact runtime build authority required')
    current_window(authority); c.text(authority['change_ref'])


def archive(raw):
    require(len(raw)<=MAX_ARCHIVE, 'Artifact archive exceeds bound')
    handle=zipfile.ZipFile(io.BytesIO(raw)); names=set(); total=0
    require(0<len(handle.infolist())<=30000, 'Artifact entry count exceeds bound')
    for item in handle.infolist():
        path=PurePosixPath(item.filename); mode=item.external_attr>>16
        require(not path.is_absolute() and '..' not in path.parts and '\\' not in item.filename
                and ':' not in item.filename and '\x00' not in item.filename
                and path.as_posix().rstrip('/')==item.filename.rstrip('/') and item.filename not in names,
                'Unsafe or duplicate archive path')
        require(stat.S_IFMT(mode) in (0,stat.S_IFREG,stat.S_IFDIR) and not item.flag_bits & 1,
                'Unsupported archive file type or encryption')
        names.add(item.filename); total+=item.file_size
        require(item.file_size<=MAX_EXPANDED and total<=MAX_EXPANDED, 'Expanded archive exceeds bound')
    return handle


def artifacts(config):
    """Verify bytes and wheel identity before any accepted artifact can execute."""
    result={}; total=0
    for item in config['wheels']:
        path=private_path(item['path']); require(path.stat().st_size<=MAX_ARCHIVE, 'Wheel exceeds bound')
        raw=read_private(path); require(digest(raw)==item['sha256'], 'Wheel artifact changed')
        with archive(raw) as wheel:
            metadata=[name for name in wheel.namelist() if re.fullmatch(r'[^/]+\.dist-info/METADATA',name)]
            require(len(metadata)==1 and wheel.getinfo(metadata[0]).file_size<=1024*1024, 'One bounded wheel identity required')
            meta=email.parser.BytesParser().parsebytes(wheel.read(metadata[0]))
            require(len(meta.get_all('Name',[]))==len(meta.get_all('Version',[]))==1
                    and normalized(meta['Name'])==item['name'] and meta['Version']==item['version'], 'Wheel identity differs')
        result[path.name]=raw; total+=len(raw)
        require(total<=512*1024*1024, 'Combined wheel artifacts exceed bound')
    item=config['terraform']; path=private_path(item['path'])
    require(path.stat().st_size<=MAX_ARCHIVE, 'Terraform archive exceeds bound')
    raw=read_private(path); require(digest(raw)==item['sha256'], 'Terraform archive changed')
    with archive(raw) as package:
        require(set(package.namelist()) in ({'terraform'},{'terraform','LICENSE.txt'}), 'Unexpected Terraform archive contents')
        require(not package.getinfo('terraform').is_dir(), 'Terraform binary is not a file')
        binary=package.read('terraform')
        require(digest(binary)==item['binary_sha256'], 'Terraform executable differs')
    result['terraform.zip']=raw
    return result,binary


class Host:
    def command(self, argv, cwd):
        result=subprocess.run(list(map(str,argv)),cwd=cwd,env=ENV.copy(),stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=300,umask=0o077)
        require(result.returncode==0 and len(result.stdout)<=2*1024*1024,
                'Runtime command failed; retain the incomplete output and use a new accepted destination')
        return result.stdout.decode()

    def identity(self, config, root):
        source=verify(root)
        require(source['status']=='HASHES_MATCH' and source['commit']==config['source_commit'], 'Build source changed')
        release=dict(line.split('=',1) for line in Path('/etc/os-release').read_text().splitlines() if '=' in line)
        require(release.get('ID','').strip('"')=='ubuntu' and release.get('VERSION_ID','').strip('"')=='24.04',
                'Accepted Ubuntu 24.04 base host required')
        path=Path(config['python'])
        require(path.is_file() and os.access(path,os.X_OK) and digest(path.read_bytes())==config['python_sha256'],
                'Base Python executable changed')
        for item in {*path.parents,path.resolve(),*path.resolve().parents}:
            info=item.stat()
            require(info.st_uid in {0,os.getuid()} and not stat.S_IMODE(info.st_mode)&0o022,
                    'Base Python location must remain custodian-controlled')


def seal_permissions(directory):
    """Only a newly built private tree; never repair completed runtime modes."""
    for path in sorted(directory.rglob('*')):
        name=path.relative_to(directory).as_posix(); info=path.lstat()
        require(info.st_uid==os.getuid(), 'New runtime custody differs')
        if path.is_symlink():
            require(name=='env/lib64' and os.readlink(path)=='lib', 'Unexpected runtime symlink')
            continue
        require(stat.S_ISDIR(info.st_mode) or (stat.S_ISREG(info.st_mode) and info.st_nlink==1),
                'Unexpected runtime file type or hard link')
        os.chmod(path,stat.S_IMODE(info.st_mode)&0o700,follow_symlinks=False)


def tree(directory):
    """Seal full files/modes, including bytecode; allow only venv's lib64 alias."""
    result={}
    for path in sorted(directory.rglob('*')):
        name=path.relative_to(directory).as_posix()
        if name in {'receipt.json','writer.lock'}: continue
        info=path.lstat(); mode=stat.S_IMODE(info.st_mode)
        require(info.st_uid==os.getuid() and (path.is_symlink() or not mode&0o022), 'Runtime custody or writable mode changed')
        if path.is_symlink():
            require(name=='env/lib64' and os.readlink(path)=='lib', 'Unexpected runtime symlink')
            result[name]={'type':'symlink','target':'lib'}
        elif path.is_dir(): result[name]={'type':'directory','mode':mode}
        else:
            require(stat.S_ISREG(info.st_mode) and info.st_nlink==1, 'Unexpected runtime file type or hard link')
            result[name]={'type':'file','mode':mode,'sha256':digest(path.read_bytes())}
    return result


def validate_receipt(config, output):
    intent=load_private(output/'intent.json')
    require(intent['config']==config, 'Runtime build identity changed')
    receipt=load_private(output/'receipt.json')
    require(receipt.get('format')=='hosting-runtime-build-receipt/1' and receipt.get('config_sha256')==c.digest(config)
            and receipt.get('status')=='RUNTIME_BUILT_REQUIRES_PLATFORM_ACCEPTANCE', 'Runtime completion record differs')
    require(receipt['files']==tree(output), 'Completed runtime changed; do not repair it in place')
    return receipt


def build(config, authority, *, host=None, root=ROOT, observe=False):
    validate(config,root); host=host or Host(); host.identity(config,root)
    output=Path(config['output']); private_path(output.parent,directory=True)
    if not observe:
        require(config['enabled'], 'Runtime build is disabled'); authorize(config,authority)
    else: require(output.is_dir(), 'Completed runtime does not exist')
    # Atomic directory creation elects the only initial builder. No existing
    # incomplete directory is adopted even when its previous process disappeared.
    existing=output.exists()
    if not existing: new_directory(output,root)
    private_path(output,directory=True)
    fd=os.open(output/'writer.lock',(0 if existing else os.O_CREAT)|os.O_RDWR|os.O_NOFOLLOW,0o600)
    try:
        private_path(output/'writer.lock'); fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        if existing:
            require((output/'receipt.json').is_file(), 'Incomplete runtime remains held; select a new accepted output')
            return validate_receipt(config,output)
        write_new(output/'intent.json',encoded({'config':config,'authority':authority}))
        sources,terraform=artifacts(config)
        profile=json.loads(host.command([config['python'],'-B','-I','-c',PROFILE_CODE],output))
        require(profile['version']==config['python_version'] and profile['implementation']=='CPython'
                and profile['platform']=='linux' and profile['machine']=='x86_64'
                and profile['prefix']==profile['base_prefix'], 'Wrong base Python version, architecture or virtual environment')
        accepted=output/'artifacts'; accepted.mkdir(mode=0o700)
        for name,raw in sources.items(): write_new(accepted/name,raw)
        requirements='\n'.join(f"{accepted/Path(item['path']).name} --hash=sha256:{item['sha256']}" for item in config['wheels'])+'\n'
        write_new(output/'requirements.txt',requirements.encode())
        authorize(config,authority)
        environment=output/'env'
        host.command([config['python'],'-B','-I','-m','venv','--without-pip','--copies',environment],output)
        python=environment/'bin/python'
        pip=next(accepted/Path(item['path']).name for item in config['wheels'] if item['name']=='pip')
        authorize(config,authority)
        host.command([python,'-B','-I','-c',PIP_CODE,pip,'install','--require-hashes','--no-index','--no-deps',
            '--only-binary=:all:','--no-cache-dir','--no-compile','--disable-pip-version-check','-r',output/'requirements.txt'],output)
        host.command([python,'-B','-I','-m','pip','check'],output)
        installed=json.loads(host.command([python,'-B','-I','-c',PACKAGES_CODE],output))
        require(installed['packages']=={item['name']:item['version'] for item in config['wheels']}
                and installed['prefix']==str(environment) and installed['base_prefix']==profile['base_prefix'],
                'Installed packages or Python isolation differ from accepted artifacts')
        # Fixed hash-based bytecode is sealed too, so ordinary imports do not
        # mutate the completed tree. Optimized variants need another profile.
        host.command([python,'-B','-I','-m','compileall','--invalidation-mode','checked-hash','-q',environment],output)
        binary_directory=output/'bin'; binary_directory.mkdir(mode=0o700)
        write_new(binary_directory/'terraform',terraform); os.chmod(binary_directory/'terraform',0o700)
        terraform_version=json.loads(host.command([binary_directory/'terraform','version','-json'],output))
        require(terraform_version['terraform_version']==config['terraform']['version']
                and terraform_version['platform']=='linux_amd64', 'Terraform version or platform differs')
        host.identity(config,root); authorize(config,authority)
        seal_permissions(output); files=tree(output)
        # Flush every published file/directory before publishing the completion.
        for name,record in files.items():
            path=output/name
            if record['type']=='directory': sync_directory(path)
            elif record['type']=='file':
                with path.open('rb') as stream: os.fsync(stream.fileno())
        sync_directory(output)
        receipt={'format':'hosting-runtime-build-receipt/1','status':'RUNTIME_BUILT_REQUIRES_PLATFORM_ACCEPTANCE',
            'config_sha256':c.digest(config),'source_commit':config['source_commit'],'completed_at':utcnow().isoformat(),
            'base_python':profile,'packages':installed['packages'],'terraform':terraform_version,
            'files':files,'production_activation':False,'native_qualification':False}
        write_new(output/'receipt.json',encoded(receipt))
        return validate_receipt(config,output)
    finally: os.close(fd)


def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--authority',type=Path)
    mode=parser.add_mutually_exclusive_group(); mode.add_argument('--execute',action='store_true'); mode.add_argument('--verify',action='store_true')
    args=parser.parse_args()
    try:
        config=load_private(args.config); validate(config)
        if not args.execute and not args.verify: print('{"status":"VALIDATED_NO_RUNTIME_CHANGE"}'); return 0
        require(args.verify or args.authority is not None, 'Current runtime build authority required')
        result=build(config,None if args.verify else load_private(args.authority),observe=args.verify)
        print(json.dumps({'status':result['status'],'config_sha256':result['config_sha256']})); return 0
    except Exception:
        print('{"status":"RUNTIME_BUILD_HELD","reason":"Preserve incomplete or changed runtime; use exact approved artifacts and a new destination"}')
        return 2


if __name__=='__main__': raise SystemExit(main())
