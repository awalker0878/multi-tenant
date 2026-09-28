"""Move the complete qualification dependency chain; no compatibility entry points."""
from pathlib import Path
import json
import re
import subprocess

root = Path.cwd()
pairs = {
    'check_version_source_provenance': 'provenance',
    'check_qualification_campaign_assurance': 'campaign',
    'check_target_selection_assurance': 'target_selection',
}
tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=root).decode().split('\0')
for rel in tracked:
    path = root / rel
    if not path.is_file() or path.suffix not in {'.py', '.md', '.json', '.yaml', '.yml', '.csv', '.sh', '.txt', ''}:
        continue
    # Workflow updates are published separately with the repository app.
    if rel.startswith('.github/') or rel == 'provisioner/retired_interfaces.json':
        continue
    try:
        old_text = path.read_text(encoding='utf-8')
    except UnicodeError:
        continue
    text = old_text
    for old, new in pairs.items():
        for python in ('python', 'python3'):
            text = text.replace(f'{python} scripts/{old}.py', f'{python} -m provisioner.qualification.{new}')
        text = text.replace(f'from scripts import {old} as ', f'from provisioner.qualification import {new} as ')
        text = re.sub(r"sys\.executable,\s*str\(ROOT\s*/\s*'scripts/" + re.escape(old) + r"\.py'\),",
                      f"sys.executable, '-m', 'provisioner.qualification.{new}',", text)
        if rel == 'tests/test_task_tree_integration.py':
            text = text.replace(f"'scripts/{old}.py' in s", f"'provisioner.qualification.{new}' in s")
        text = text.replace(f'scripts/{old}.py', f'provisioner/qualification/{new}.py')
    if text != old_text:
        path.write_text(text, encoding='utf-8')

for old, new in pairs.items():
    source = root / f'scripts/{old}.py'
    target = root / f'provisioner/qualification/{new}.py'
    if not source.is_file() or target.exists():
        raise SystemExit(f'Unexpected relocation state: {source}')
    text = source.read_text(encoding='utf-8')
    text = re.sub(r"if __package__ in \(None, ''\):\n(?:    import sys\n)?    sys.path.insert\(0, str\(Path\(__file__\).resolve\(\).parents\[1\]\)\)\n", '', text)
    if 'sys.' not in text:
        text = text.replace('import sys\n', '')
    if new == 'provenance':
        text = text.replace("PLATFORMS={'nutanix','vmware-nsx','openstack'}", 'from provisioner.domain.capabilities import PLATFORMS')
    target.write_text(text, encoding='utf-8')
    source.unlink()

path = root / 'scripts/check_installed_distribution.py'
text = path.read_text(encoding='utf-8')
text = text.replace('from provisioner.qualification import native, registry',
                    'from provisioner.qualification import campaign, native, provenance, registry, target_selection')
text = text.replace('hosting_resources, native, registry, adoption,',
                    'hosting_resources, campaign, native, provenance, registry, target_selection, adoption,')
anchor = "assert importlib.util.find_spec('scripts.check_platform_qualification') is None"
assert anchor in text
text = text.replace(anchor, anchor + '\n' + '\n'.join(
    f"assert importlib.util.find_spec('scripts.{old}') is None" for old in pairs))
path.write_text(text, encoding='utf-8')

path = root / 'provisioner/retired_interfaces.json'
record = json.loads(path.read_text(encoding='utf-8'))
for old, new in pairs.items():
    record['retiredInterfaces'].append({
        'interface': f'scripts/{old}.py', 'kind': 'path',
        'reason': 'Qualification dependency moved into the installed package; all callers migrated without a compatibility wrapper or import-path mutation.',
        'replacement': f'provisioner/qualification/{new}.py',
        'enforcement': 'the path must not exist',
    })
path.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')

path = root / 'docs/current/TAD-infrastructure.md'
text = path.read_text(encoding='utf-8')
old = '''The old script entry points were removed and their consumers migrated without
wrappers. Run them as `python -m provisioner.qualification.registry` and
`python -m provisioner.qualification.native`. Other runtime owners still require
relocation; this change does not close B05.'''
new = '''The full qualification dependency chain is package-owned: `provenance.py`
validates version/source records, `target_selection.py` validates selected native
campaign scope, and `campaign.py` validates target-bound campaign observations.
All five old script entry points were removed and their consumers migrated without
wrappers or import-path mutation. Run the owners using
`python -m provisioner.qualification.<owner>`, where `<owner>` is `registry`,
`native`, `provenance`, `target_selection` or `campaign`. None imports the legacy
scripts/tools packages. Other runtime owners still require relocation; this change
does not close B05.'''
assert old in text
path.write_text(text.replace(old, new), encoding='utf-8')

path = root / 'docs/implementation/automation/phase0-interface-retirement.md'
text = path.read_text(encoding='utf-8')
text += '''
### Complete qualification dependency closure

The installed qualification package also owns version/source provenance, native
target selection and campaign evidence. Its five modules (`registry`, `native`,
`provenance`, `target_selection`, `campaign`) contain the implementations, not
forwarding wrappers. Every in-tree caller and CLI was migrated; the five old
script paths are prohibited by the retirement register. Architecture tests reject
any package qualification import back into `scripts` or `tools`, and the installed
wheel check requires all five owners to resolve outside the source checkout.
Other execution owners and retained-state conversion remain separate B05 work.
'''
path.write_text(text, encoding='utf-8')
print('Relocated the complete qualification dependency chain without aliases.')
