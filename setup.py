"""Bundle reviewed planning resources in the distribution's own package.

No data directory is installed at site-packages root, where it could collide with
another distribution. Source references retain their relative paths inside the
resource package, so reviewed evidence links have the same meaning after install.
"""

import json
from pathlib import Path
from shutil import copy2

from setuptools import setup
from setuptools.command.build_py import build_py


class BuildRuntime(build_py):
    """Copy reviewed inputs below the package that owns their resource API."""

    def run(self):
        source = Path(__file__).resolve().parent
        required = {
            'tools/__init__.py', 'tools/compile_wsd.py', 'tools/check_release.py',
            'scripts/__init__.py', 'scripts/build_wsd_compositions.py',
            'scripts/check_platform_capabilities.py',
            'sources/capabilities/platform_registry.json',
            'policy/rules/standards.json', 'profiles/security/catalog.json',
            'terraform/catalog.json', 'ansible/catalog.json', 'config/toolchain.json',
            'ansible/filter_plugins/guest_filters.py',
            'ansible/callback_plugins/hosting_guest_result.py',
        }
        terraform = json.loads((source / 'terraform/catalog.json').read_text(encoding='utf-8'))
        for entry in terraform['entries']:
            required.add(f"{entry['module']}/main.tf.json")
            required.add(f"{entry['root']}/main.tf.json")
        ansible = json.loads((source / 'ansible/catalog.json').read_text(encoding='utf-8'))
        required.update(f"ansible/{entry['path']}" for entry in ansible['playbooks'])
        required.update(f'ansible/roles/{name}/tasks/main.yml' for name in
                        ('linux_guest_baseline', 'linux_guest_services', 'linux_guest_backup'))
        # Capability validation checks that its reviewed evidence exists. Ship
        # the referenced documents, not the entire documentation workspace.
        evidence_docs = set()
        def collect_docs(value):
            if isinstance(value, dict):
                for item in value.values():
                    collect_docs(item)
            elif isinstance(value, list):
                for item in value:
                    collect_docs(item)
            elif isinstance(value, str) and value.startswith('docs/'):
                path = Path(value)
                if path.is_absolute() or '..' in path.parts:
                    raise ValueError(f'Unsafe reviewed evidence reference: {value}')
                evidence_docs.add(value)

        for index in sorted((source / 'sources/capabilities').glob('*.json')):
            collect_docs(json.loads(index.read_text(encoding='utf-8')))
        required.update(evidence_docs)
        missing = sorted(path for path in required if not (source / path).is_file())
        if missing:
            raise FileNotFoundError(f'Incomplete runtime distribution: {missing}')

        super().run()
        destination = Path(self.build_lib) / 'hosting_resources' / '_assets'
        for directory in ("profiles", "policy", "sources", "terraform", "ansible", "config"):
            for item in sorted((source / directory).rglob("*")):
                if not item.is_file() or "__pycache__" in item.parts:
                    continue
                target = destination / item.relative_to(source)
                target.parent.mkdir(parents=True, exist_ok=True)
                copy2(item, target)
        for relative in sorted(evidence_docs):
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            copy2(source / relative, target)


setup(cmdclass={"build_py": BuildRuntime})
