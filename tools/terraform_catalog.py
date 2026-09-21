"""Discover explicitly registered Terraform writer scopes without fixed counts."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def entries(root: Path = ROOT) -> list[dict]:
    root = root.resolve()
    doc = json.loads((root / 'terraform/catalog.json').read_text(encoding='utf-8'))
    if doc.get('format') != 'hosting-terraform-catalog/1' or not doc.get('entries'):
        raise ValueError('Nonempty Terraform catalogue required')
    rows = doc['entries']
    names, paths = set(), set()
    for row in rows:
        if set(row) != {'id', 'platform', 'kind', 'module', 'root', 'owner_scope'}:
            raise ValueError('Invalid Terraform catalogue entry')
        if row['id'] in names or row['kind'] not in {'component', 'composition'}:
            raise ValueError('Duplicate or invalid Terraform scope')
        names.add(row['id'])
        for field in ('module', 'root'):
            p = root / row[field]
            if (p.is_symlink() or not p.resolve().is_relative_to(root / 'terraform')
                    or not (p / 'main.tf.json').is_file() or row[field] in paths):
                raise ValueError('Missing, duplicate or unsafe Terraform path')
            paths.add(row[field])
        module = json.loads((root / row['module'] / 'main.tf.json').read_text(encoding='utf-8'))
        config = json.loads((root / row['root'] / 'main.tf.json').read_text(encoding='utf-8'))
        source = config['module']['owned']['source']
        if (root / row['root'] / source).resolve() != root / row['module']:
            raise ValueError('Root/module ownership mismatch')
        if module['terraform']['required_providers'] != config['terraform']['required_providers']:
            raise ValueError('Root/module provider mismatch')
    actual = {str(p.parent.relative_to(root)) for p in (root / 'terraform').rglob('main.tf.json')
              if '.terraform' not in p.parts}
    if actual != paths:
        raise ValueError('Unregistered or missing Terraform configuration')
    return rows
