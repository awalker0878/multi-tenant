#!/usr/bin/env python3
"""Repository hygiene and structure, not infrastructure or engine qualification."""
from __future__ import annotations
import argparse,hashlib,json,re,sys
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
import xml.etree.ElementTree as ET
import zipfile
import yaml
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.catalog_artifacts import collect
from tools.verify_terraform import plan_only_mock_tests
EXCLUDED={'.git','.venv','__pycache__','build','dist','.pytest_cache','.mypy_cache','.ruff_cache'}

class UniqueLoader(yaml.SafeLoader):
    pass

def construct_mapping(loader,node,deep=False):
    out={}
    for key_node,value_node in node.value:
        key=loader.construct_object(key_node,deep=deep)
        if key in out:raise ValueError(f'Duplicate YAML key: {key}')
        out[key]=loader.construct_object(value_node,deep=deep)
    return out
UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,construct_mapping)

class Links(HTMLParser):
    def __init__(self):super().__init__();self.targets=[]
    def handle_starttag(self,tag,attrs):
        self.targets += [v for k,v in attrs if k=='href' and v]


def high_confidence_secret(text):
    return bool(re.search(r'-----BEGIN (?:RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY-----\s+[A-Za-z0-9+/=\r\n]{64,}',text)
                or re.search(r'\bgh[pousr]_[A-Za-z0-9]{30,}\b',text)
                or re.search(r'\bAKIA[0-9A-Z]{16}\b',text))


def forbidden_path(rel):
    return (any(x in rel.parts for x in ('.terraform','private','actual-inputs','actual-evidence'))
            or rel.name.endswith(('.tfstate','.tfplan','.key','.p12','.pfx','.pem'))
            or '.tfstate.' in rel.name
            or rel.name in ('.env','clouds.yaml','secure.yaml')
            or (rel.name.endswith(('.tfvars','.tfvars.json')) and not rel.name.endswith('.example')))


def check(root=ROOT):
    issues=[];counts={'active_links':0,'reference_files':0,'yaml_files':0,'catalog_artifacts':0,'terraform_module_root_pairs':0,'ansible_playbooks':0,'source_files':0}
    def problem(kind,path,detail=''):issues.append({'kind':kind,'path':str(path),'detail':str(detail)[:500]})
    def local_link(p,target):
        parsed=urlsplit(target)
        if parsed.scheme or not parsed.path or parsed.netloc:return
        counts['active_links']+=1
        dest=(p.parent/unquote(parsed.path)).resolve()
        if not dest.is_relative_to(root.resolve()) or not dest.exists():problem('BROKEN_ACTIVE_LINK',p.relative_to(root),target)
    for p in sorted(root.rglob('*')):
        rel=p.relative_to(root)
        if any(x in EXCLUDED for x in rel.parts):continue
        if p.is_symlink():problem('SYMLINK_NOT_ALLOWED',rel);continue
        if not p.is_file():continue
        counts['source_files']+=1
        if forbidden_path(rel):problem('SENSITIVE_OR_RUNTIME_PATH',rel)
        # Frozen source and imported report history is preserved, not promoted as active code.
        historical=('reference' in rel.parts or rel.parts[0]=='quality' or rel.parts[:2]==('evidence','imported'))
        if p.suffix in ('.py','.md','.txt','.yml','.yaml','.json','.hcl','.j2','.cfg'):
            text=p.read_text(errors='replace')
            if high_confidence_secret(text):problem('POSSIBLE_SECRET',rel)
            if not historical and p.suffix=='.md':
                for target in re.findall(r'(?<!!)\[[^\]]*\]\(([^)]+)\)',text):local_link(p,target.split(' "')[0])
            if not historical and p.suffix in ('.yaml','.yml'):
                counts['yaml_files']+=1
                try:yaml.load(text,Loader=UniqueLoader)
                except Exception as e:problem('YAML_PARSE',rel,e)
        if not historical and p.suffix=='.html':
            links=Links();links.feed(p.read_text())
            for target in links.targets:local_link(p,target)
    try:
        expected=json.loads((root/'sources/reference_checksums.json').read_text())
        for name,digest in expected.items():
            counts['reference_files']+=1;p=root/name
            if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=digest:problem('REFERENCE_BYTES_CHANGED',name)
        rows=json.loads((root/'sources/artifact_catalog.json').read_text());counts['catalog_artifacts']=len(rows)
        if rows!=collect(root):problem('STALE_ARTIFACT_CATALOG','sources/artifact_catalog.json')
    except (OSError,ValueError,TypeError) as e:problem('CATALOG_OR_REFERENCE_ERROR','sources',e)
    for mod in sorted((root/'terraform/modules').glob('*/main.tf.json')):
        counts['terraform_module_root_pairs']+=1
        try:
            m=json.loads(mod.read_text());r=json.loads((root/'terraform/roots'/mod.parent.name/'main.tf.json').read_text())
            if not m.get('resource'):problem('EMPTY_NATIVE_MODULE',mod.parent.name)
            if m['terraform']['required_providers']!=r['terraform']['required_providers']:problem('PROVIDER_PIN_DIVERGENCE',mod.parent.name)
            if r['module']['owned']['source']!=f'../../modules/{mod.parent.name}':problem('ROOT_MODULE_PATH',mod.parent.name)
            if not plan_only_mock_tests(mod.parent):problem('UNSAFE_MOCK_TEST',mod.parent.name)
        except (OSError,KeyError,ValueError) as e:problem('NATIVE_SOURCE_STRUCTURE',mod.parent.name,e)
    for p in (root/'ansible/playbooks').glob('*.yml'):
        counts['ansible_playbooks']+=1
        try:
            for play in yaml.load(p.read_text(),Loader=UniqueLoader):
                if play.get('hosts')!='localhost' or play.get('connection')!='local' or play.get('become') is not False:
                    problem('UNBOUNDED_DEFAULT_ANSIBLE',p.relative_to(root))
        except Exception as e:problem('ANSIBLE_SOURCE',p.relative_to(root),e)
    for p in (root/'.github/workflows').glob('*.yml'):
        try:
            doc=yaml.load(p.read_text(),Loader=yaml.BaseLoader)
            if doc.get('permissions')!={'contents':'read'}:problem('WORKFLOW_PERMISSION',p.name)
            if 'pull_request_target' in doc.get('on',{}):problem('PR_TARGET_FORBIDDEN',p.name)
            for job in doc.get('jobs',{}).values():
                if job.get('runs-on')!='ubuntu-24.04':problem('UNAPPROVED_RUNNER',p.name)
                for step in job.get('steps',[]):
                    if 'uses' in step and not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+@[0-9a-f]{40}',step['uses']):problem('UNPINNED_ACTION',p.name)
                    run=step.get('run','')
                    if re.search(r'\bterraform\s+(?:apply|destroy)\b|--execute-approved-change|--read-authorized-target|secrets\.',run):problem('NATIVE_MUTATION_OR_SECRET_IN_CI',p.name)
        except Exception as e:problem('WORKFLOW_SOURCE',p.name,e)
    return {'status':'PASSED_REPOSITORY_STATIC_ONLY' if not issues else 'FAILED_REPOSITORY_CHECK','counts':counts,'issues':issues,
            'limits':['Not Terraform/Ansible engine validation','Common secret-pattern checks are not exhaustive','Frozen library byte identity, not new technical approval','GitHub workflows were not executed by this command']}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,default=ROOT/'build/reports/repository_check.json');a=p.parse_args()
    r=check();a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2));return bool(r['issues'])
if __name__=='__main__':raise SystemExit(main())
