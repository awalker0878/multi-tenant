"""Conservative admission: published contract artifacts are immutable by version."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess


def compare(base: dict[str, bytes], head: dict[str, bytes]) -> list[str]:
    # Exact bytes intentionally include descriptions and channel bindings. This
    # policy makes no claim to solve general JSON Schema language inclusion.
    return [path for path, value in base.items() if head.get(path) != value]


def inventory(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes()
            for p in sorted((root / 'contracts').rglob('*'))
            if p.is_file() and p.suffix in {'.json', '.yaml', '.yml'}}


def check(root: Path, base_revision: str) -> dict:
    if not re.fullmatch(r'[0-9a-f]{40}', base_revision) or set(base_revision) == {'0'}:
        raise ValueError('An explicit existing base commit is required')
    def git(*args: str) -> bytes:
        try:
            return subprocess.run(['git', *args], cwd=root, check=True,
                                  capture_output=True, timeout=30).stdout
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
            raise ValueError('Complete Git history is required to verify published contracts') from error
    git('cat-file', '-e', base_revision + '^{commit}')
    if git('rev-parse', '--is-shallow-repository').strip() != b'false':
        raise ValueError('Complete Git history is required to verify published contracts; shallow checkout')
    # Validate reachability even when a missing parent predates the last contract
    # edit. A partial history must never establish a new, weaker freeze point.
    git('rev-list', '--parents', base_revision)
    history = ('--first-parent', '--diff-merges=first-parent', '--diff-filter=A', '--no-renames')
    paths = git('log', *history, '--format=', '--name-only', '-z', base_revision,
                '--', 'contracts').decode().split('\0')
    paths = sorted({p.lstrip('\n') for p in paths
                    if Path(p.lstrip('\n')).suffix in {'.json', '.yaml', '.yml'}})
    base, published = {}, {}
    for path in paths:
        # The first appearance on the base branch is the published artifact.
        # Merge commits publish their first-parent diff; draft revisions on a
        # side branch are not mistaken for an earlier release on this branch.
        # Do not follow renames: moving/deleting a published path is a removal.
        revisions = git('log', '--reverse', *history, '--format=%H', base_revision,
                        '--', path).decode().splitlines()
        if not revisions:
            raise ValueError('Missing publication history for contract: ' + path)
        published[path] = revisions[0]
        base[path] = git('show', revisions[0] + ':' + path)
    current = inventory(root)
    conflicts = compare(base, current)
    report = {'base_revision': base_revision, 'policy': 'immutable-existing-contract-artifacts',
              'baseline': 'first-publication-on-base-first-parent-history',
              'published_revisions': published,
              'baseline_sha256': {p: hashlib.sha256(v).hexdigest() for p, v in base.items()},
              'added': sorted(set(current) - set(base)), 'conflicts': conflicts}
    if conflicts:
        raise ValueError('Published contract removed or changed: ' + ', '.join(conflicts))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', required=True)
    args = parser.parse_args()
    print(json.dumps(check(Path(__file__).resolve().parents[3], args.base), indent=2))
