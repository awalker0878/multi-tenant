"""Relocate the existing WSD compiler, migrating callers rather than adding shims."""
from pathlib import Path
import json
import re
import subprocess

root=Path.cwd()
old='tools/compile_wsd.py'
new='provisioner/compiler/wsd.py'
if not (root/old).is_file() or (root/new).exists():
    raise SystemExit('Unexpected compiler relocation baseline')
tracked=subprocess.check_output(['git','ls-files','-z']).decode().split('\0')
for rel in tracked:
    p=root/rel
    if not p.is_file() or p.suffix not in {'.py','.md','.json','.yml','.yaml','.sh','.txt',''}:
        continue
    # Frozen specifications and historical evidence are not current callers.
    if rel.startswith(('.github/','evidence/','quality/','sources/history/',
                       'sources/documentation/history/','sources/assurance/history/',
                       'docs/archive/','docs/deepseek-')):
        continue
    if rel.startswith('sources/') and ('manifest' in p.name or 'traceability' in p.name):
        continue
    if rel=='provisioner/retired_interfaces.json':
        continue
    text=p.read_text(encoding='utf-8')
    changed=text.replace('from tools import compile_wsd, guest_inventory',
                         'from provisioner.compiler import wsd as compile_wsd\nfrom tools import guest_inventory')
    changed=changed.replace('from tools import compile_wsd',
                            'from provisioner.compiler import wsd as compile_wsd')
    changed=changed.replace('tools.compile_wsd','provisioner.compiler.wsd')
    for python in ('python3','python'):
        changed=changed.replace(f'{python} {old}',f'{python} -m provisioner.compiler.wsd')
    changed=changed.replace(old,new).replace('tools/compile_wsd.', 'provisioner/compiler/wsd.')
    changed=changed.replace("'tools' / 'compile_wsd.py'", "'provisioner' / 'compiler' / 'wsd.py'")
    if 'build_wsd_compositions.COMPONENTS' in changed:
        changed=changed.replace('from scripts import build_wsd_compositions',
                                'from provisioner.compiler import components')
        changed=changed.replace('build_wsd_compositions.COMPONENTS','components.COMPONENTS')
    if changed!=text:
        p.write_text(changed,encoding='utf-8')

# The build-only renderer consumes the package declaration. Its generated
# artifacts remain byte-identical; no runtime import of a build script remains.
p=root/'scripts/build_wsd_compositions.py'
s=p.read_text()
block="""COMPONENTS = {
    'nutanix': {'domains': 'nutanix-domain', 'workloads': 'nutanix-workload'},
    'vmware': {'domains': 'nsx-domain', 'workloads': 'vsphere-workload'},
    'openstack': {'domains': 'openstack-domain', 'workloads': 'openstack-workload'},
}
"""
assert s.count(block)==1
(root/'provisioner/compiler/components.py').write_text(
    '"""Native module identities shared by compilation and build-time rendering."""\n'+block)
s=s.replace(block,'from provisioner.compiler import components\n')
s=s.replace('COMPONENTS.items()', 'components.COMPONENTS.items()')
p.write_text(s)

p=root/old
s=p.read_text()
s=s.replace('import sys\n','')
s=s.replace("if __package__ in (None, ''):\n    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))\n",'')
s=s.replace('from scripts.build_wsd_compositions import COMPONENTS',
            'from provisioner.compiler.components import COMPONENTS')
s=s.replace('from tools.neutron_observe import strict_loads\n','')
# Compilation needs a bounded JSON file boundary, not a native networking client.
loader='''INPUT_LIMIT = 4 * 1024 * 1024


def _read_json(path: Path):
    """Reject oversized or ambiguous handoff input before creating any output."""
    with path.open('rb') as stream:
        raw = stream.read(INPUT_LIMIT + 1)
    if len(raw) > INPUT_LIMIT:
        raise ValueError('Compiler JSON input exceeds bounded size')

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate JSON key')
            result[key] = value
        return result

    def reject(_value):
        raise ValueError('Non-finite JSON number')

    return json.loads(raw, object_pairs_hook=pairs, parse_constant=reject)


'''
s=s.replace('def main():\n',loader+'def main():\n')
s=s.replace('strict_loads(args.environment.read_bytes())','_read_json(args.environment)')
s=s.replace('strict_loads(args.domain_outputs.read_bytes())','_read_json(args.domain_outputs)')
s=s.replace('strict_loads(args.vmware_bindings.read_bytes())','_read_json(args.vmware_bindings)')
(root/new).write_text(s)
p.unlink()

p=root/'setup.py'
s=p.read_text().replace("'scripts/__init__.py', 'scripts/build_wsd_compositions.py',",
                       "'scripts/__init__.py', 'provisioner/compiler/components.py',")
p.write_text(s)

p=root/'tests/provisioning/unit/test_architecture.py'
s=p.read_text()
a=s.index('    def test_the_existing_compiler_never_imports_the_portable_core(self):')
b=s.index("\n\nif __name__",a)
s=s[:a]+'''    def test_the_package_owned_compiler_has_only_low_level_dependencies(self):
        for filename in ('wsd.py', 'components.py'):
            compiler = PACKAGE / 'compiler' / filename
            self.assertTrue(compiler.is_file())
            for name in _absolute_imports(compiler):
                with self.subTest(module=filename, imports=name):
                    self.assertFalse(name.startswith(('tools', 'scripts')),
                                     f'{filename} imports legacy owner {name}')
                    if name.startswith('provisioner'):
                        self.assertEqual(name, 'provisioner.compiler.components')
            self.assertNotIn('sys.path', compiler.read_text(encoding='utf-8'))
''' +s[b:]
p.write_text(s)

p=root/'provisioner/retired_interfaces.json'
record=json.loads(p.read_text())
for entry in record['retiredInterfaces']:
    if entry['replacement']==old:
        entry['replacement']=new
record['retiredInterfaces'].append({
    'interface':old,'kind':'path',
    'reason':'The actual compiler is package-owned; all callers migrated, with no forwarding file, path mutation or build-script/native-observer dependency.',
    'replacement':new,'enforcement':'the path must not exist'})
p.write_text(json.dumps(record,indent=2)+'\n')
p=root/'tests/test_retired_interfaces.py'
s=p.read_text().replace("EXPECTED = {", "EXPECTED = {\n    'tools/compile_wsd.py': ('path', 'provisioner/compiler/wsd.py'),")
p.write_text(s)

p=root/'scripts/check_installed_distribution.py'
s=p.read_text()
needle='import provisioner\nimport scripts'
replacement='''# Compiler execution must work without importing the legacy owner packages.
import importlib.abc
class NoLegacyCompilerImports(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'tools', 'scripts'}:
            raise AssertionError('Compiler imported legacy owner: '+fullname)
        return None

blocker = NoLegacyCompilerImports()
sys.meta_path.insert(0, blocker)
compiler_path = list(sys.path)
try:
    import provisioner
    from provisioner.compiler import components, wsd
    for platform in components.COMPONENTS:
        for phase in ('domains', 'workloads'):
            assert wsd.native_variables(platform, phase)
    assert sys.path == compiler_path
finally:
    sys.meta_path.remove(blocker)
assert importlib.util.find_spec('tools.compile_wsd') is None
import scripts'''
assert s.count(needle)==1
s=s.replace(needle,replacement)
s=s.replace('provisioner, scripts, tools, hosting_resources,',
            'provisioner, components, wsd, scripts, tools, hosting_resources,')
p.write_text(s)

p=root/'docs/provisioning/architecture.md'
s=p.read_text()
s=s.replace('desired state that the **existing** compiler already understands. It is an additive\nfront end: the compiler, the Terraform roots, the Ansible roles and the delivery\ntooling keep their current owners.',
'''desired state consumed by the package-owned WSD compiler. The original compiler
implementation now lives in `provisioner/compiler/wsd.py`, with its component map
in `provisioner/compiler/components.py`; there is no old-path wrapper. Terraform
roots, Ansible roles and the remaining delivery tools retain their owners.''')
s=s.replace('`scripts/`; it resolves those modules by name so the existing compiler stays the\nsingle source of native field shapes.',
'''`scripts/` for owners not yet migrated under B05. The compiler has no such
backreach: it reads reviewed assets through `hosting_resources` and shares the
component declaration with the build-only composition renderer. Native field
shapes remain declared exactly once.''')
p.write_text(s)

p=root/'docs/implementation/automation/phase0-interface-retirement.md'
s=p.read_text()+'''
### Package-owned WSD compilation

The implementation formerly at `tools/compile_wsd.py` now lives at
`provisioner/compiler/wsd.py`; its native component map lives at
`provisioner/compiler/components.py`. All in-tree imports, current commands,
architecture links, packaging requirements and tests were migrated. The old file
is deleted and prohibited by the retirement register, not retained as a wrapper.
The build-only composition renderer consumes the same package declaration. The
compiler no longer imports `tools`, `scripts`, a networking observer or a path
bootstrap. Its private JSON-file boundary rejects duplicate keys, non-finite
constants and inputs exceeding 4 MiB before creating output.

Native input shapes, disabled Terraform inputs, state keys and generated resource
bytes are unchanged by relocation. Installed-wheel checks block all `tools` and
`scripts` imports while importing the compiler and loading native declarations
for all three platforms and both phases. Existing compiled plans remain disabled;
this code ownership change does not migrate retained execution state, reauthorize
old plans or close the rest of B05.
'''
p.write_text(s)

p=root/'docs/current/TAD-infrastructure.md'
s=p.read_text().replace('**Version:** 0.2','**Version:** 0.3')
anchor='## Design content'
assert anchor in s
s=s.replace(anchor,anchor+'''

The WSD compiler is installed at `provisioner/compiler/wsd.py`, with one native
component map at `provisioner/compiler/components.py`. All callers migrated and
the old executable was deleted without a shim. Compilation depends only on
reviewed package assets and low-level declarations, not build scripts or native
observers. Its JSON input boundary is bounded and rejects ambiguous input before
output creation. Native field shapes, generated resources, disabled outputs and
state keys are preserved; retained execution ownership still requires B05 work.
''',1)
p.write_text(s)
p=root/'sources/documentation/current_design_records.json'
records=json.loads(p.read_text())
for record in records:
    if record['id']=='TAD-M01':
        assert record['version']=='0.2'
        record['version']='0.3'
        record['change_history'].append({'version':'0.3','date':'2026-09-28',
            'summary':'Moved the actual WSD compiler and component declarations into package ownership without a shim; bounded file input, migrated callers and verified isolated compiler imports while preserving generated native inputs.'})
p.write_text(json.dumps(records,indent=2,ensure_ascii=False)+'\n')
p=root/'docs/current/README.md'
s=p.read_text().replace('The six records are at **version 0.2 (Proposed)** following the 28 September 2026',
                       'TAD-M01 is **version 0.3 (Proposed)**; the other five records remain\n**version 0.2 (Proposed)** following the 28 September 2026')
p.write_text(s)
p=root/'docs/NEXT_WORK.md'
s=p.read_text().replace('**B05 — finish installed ownership.** Continue moving the remaining compiler,\nexecution and evidence owners into the package, migrating all callers and removing',
'''**B05 — finish installed ownership.** WSD compilation and component declarations
are now package-owned without a legacy entry point. Continue moving the remaining
execution and evidence owners into the package, migrating all callers and removing''')
p.write_text(s)
p=root/'docs/product/enterprise-workload-mobility-execution-plan.md'
s=p.read_text().replace('  `scripts` runtime owners and source-bound execution still keep B05 open.',
'''  `scripts` runtime owners and source-bound execution still keep B05 open.
  The actual WSD compiler and component declarations are now package-owned; its
  old executable was deleted, callers migrated, and isolated compiler imports
  reject legacy owner dependencies. Generated native inputs and resources retain
  their existing identities. This relocation does not close retained-state work.''')
p.write_text(s)
print('Relocated WSD compilation without legacy entry points or runtime backreach.')
from pathlib import Path
root=Path.cwd()
for rel in ('provisioner/repository.py','tests/provisioning/adapters/test_adapter_contract.py',
            'tests/provisioning/adapters/test_adapters.py'):
    p=root/rel
    s=p.read_text().replace('from provisioner.compiler import components',
                           'from provisioner.compiler import components as native_components')
    s=s.replace('components.COMPONENTS','native_components.COMPONENTS')
    p.write_text(s)
p=root/'provisioner/compiler/wsd.py'
s=p.read_text().replace('import json\n','import json\nimport math\n')
s=s.replace("    return json.loads(raw, object_pairs_hook=pairs, parse_constant=reject)",
'''    def finite_float(value):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError('Non-finite JSON number')
        return number

    return json.loads(raw, object_pairs_hook=pairs, parse_constant=reject,
                      parse_float=finite_float)''')
s=s.replace('except (OSError, ValueError, KeyError, TypeError) as exc:',
            'except (OSError, ValueError, KeyError, TypeError, RecursionError) as exc:')
p.write_text(s)
from pathlib import Path
root=Path.cwd()
for p in (root/'docs/provisioning').glob('*.md'):
    s=p.read_text()
    for name in ('PLACEMENT','NETWORK','WORKLOAD_NETWORK_BINDING'):
        s=s.replace('provisioner/compiler/wsd.'+name,'provisioner.compiler.wsd.'+name)
    p.write_text(s)
p=root/'scripts/check_installed_distribution.py'
s=p.read_text()
s=s.replace("        for phase in ('domains', 'workloads'):\n            assert wsd.native_variables(platform, phase)",
'''        for phase in ('domains', 'workloads'):
            assert wsd.native_variables(platform, phase)
        environment = json.loads((request.parent / 'environments' /
                                  (platform+'.json.example')).read_text())
        inputs, summary = wsd.compile_environment(environment)
        assert inputs and summary['native_contact'] is False
        assert summary['status'] == 'DRAFT_DISABLED_NOT_AUTHORIZED'
        assert all(value['allow_restricted_build'] is False for value in inputs.values())''')
s=s.replace("        shutil.copyfile(ROOT / 'examples/requests/internal-production.yaml', request)",
'''        shutil.copyfile(ROOT / 'examples/requests/internal-production.yaml', request)
        shutil.copytree(ROOT / 'examples/environments', foreign / 'environments')''')
p.write_text(s)

(root/'tests/test_wsd_compiler_input.py').write_bytes((root/'.github/compiler-owner-input-tests.py').read_bytes())
