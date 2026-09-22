#!/usr/bin/env python3
"""Retired-interface drift check.

Fails when an active document or an active provisioner source file reintroduces an
interface this repository has retired. The register is
`provisioner/retired_interfaces.json`; its own `scope` block names the frozen
documents that are excluded because they record the retired forms as forbidden
examples rather than using them.

This command reads files only. It contacts no platform, runs no engine and issues
no authorization.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

REGISTER = ROOT / 'provisioner' / 'retired_interfaces.json'
FORMAT = 'hosting-retired-interfaces/1'
KINDS = ('path', 'text')
SKIP_PARTS = {'.git', '.venv', '__pycache__', 'build', 'dist', '.pytest_cache',
              '.mypy_cache', '.ruff_cache'}


def _load_register(path: Path = REGISTER) -> dict:
    document = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(document, dict) or document.get('format') != FORMAT:
        raise ValueError(f'Unknown retired-interface register format in {path}')
    entries = document.get('retiredInterfaces')
    if not isinstance(entries, list) or not entries:
        raise ValueError('The retired-interface register lists no interfaces')
    seen: set[str] = set()
    for entry in entries:
        missing = {'interface', 'kind', 'reason', 'replacement', 'enforcement'} - set(entry)
        if missing:
            raise ValueError(f'Incomplete retired-interface entry {entry.get("interface")!r}: '
                             f'{sorted(missing)}')
        if entry['kind'] not in KINDS:
            raise ValueError(f'Unknown retired-interface kind {entry["kind"]!r}')
        if entry['interface'] in seen:
            raise ValueError(f'Duplicate retired interface {entry["interface"]!r}')
        seen.add(entry['interface'])
    return document


def _excluded(document: dict) -> set[str]:
    return {row['path'] for row in document.get('scope', {}).get('excluded', [])}


def _relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _scan_files(document: dict) -> list[Path]:
    """Every active document and provisioner source file the register covers."""
    excluded = _excluded(document)
    scope = document.get('scope', {})
    found: set[Path] = set()
    for pattern in scope.get('documents', []):
        found.update(p for p in ROOT.glob(pattern) if p.is_file())
    for pattern in scope.get('sources', []):
        found.update(p for p in ROOT.glob(pattern) if p.is_file())
    return sorted(p for p in found
                  if _relative(p) not in excluded
                  and not any(part in SKIP_PARTS for part in p.relative_to(ROOT).parts))


def check(root: Path = ROOT, register: Path | None = None) -> dict:
    document = _load_register(register or root / 'provisioner' / 'retired_interfaces.json')
    files = _scan_files(document)
    texts = {_relative(p): p.read_text(encoding='utf-8', errors='replace') for p in files}
    issues: list[dict] = []
    checked = 0
    for entry in document['retiredInterfaces']:
        checked += 1
        name = entry['interface']
        if entry['kind'] == 'path':
            if (root / name).exists():
                issues.append({'kind': 'REINTRODUCED_PATH', 'interface': name,
                               'detail': entry['enforcement']})
            continue
        for relative, text in texts.items():
            if name in text:
                issues.append({'kind': 'REINTRODUCED_TERM', 'interface': name,
                               'path': relative, 'detail': entry['enforcement']})
    return {'format': 'hosting-retired-interface-check/1',
            'status': 'PASSED' if not issues else 'FAILED',
            'register': _relative(register or REGISTER),
            'interfaces_checked': checked,
            'files_scanned': len(texts),
            'excluded': sorted(_excluded(document)),
            'issues': issues,
            'native_infrastructure': 'NOT_CONTACTED'}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=None)
    args = parser.parse_args(argv)
    report = check()
    text = json.dumps(report, indent=2) + '\n'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding='utf-8')
    print(text, end='')
    return 0 if report['status'] == 'PASSED' else 1


if __name__ == '__main__':
    sys.exit(main())