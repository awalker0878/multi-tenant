"""Check retained evidence bytes, without treating consistency as authenticity."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re


def sha256(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def retained_path(root: Path, name: str) -> Path:
    path = PurePosixPath(name)
    if (not name or path.is_absolute() or str(path) != name or '..' in path.parts
            or '\\' in name):
        raise ValueError('unsafe_evidence_path')
    target = root / name
    if (any(p.is_symlink() for p in (target, *target.parents))
            or not target.resolve().is_relative_to(root.resolve())):
        raise ValueError('symlinked_evidence_path')
    return target


def verify_record(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        raise ValueError('missing_or_symlinked_retrieval')
    record = json.loads(path.read_bytes())
    files = record.get('retained_file_sha256')
    if not isinstance(files, dict) or not files:
        raise ValueError('missing_retained_inventory')
    for name, expected in sorted(files.items()):
        if not isinstance(expected, str) or not re.fullmatch(r'[0-9a-f]{64}', expected):
            raise ValueError('invalid_retained_digest')
        target = retained_path(path.parent, name)
        if target == path or not target.is_file():
            raise ValueError('missing_retained_file:' + name)
        if sha256(target) != expected:
            raise ValueError('retained_digest_mismatch:' + name)
    return {'retrieval_sha256': sha256(path), 'files_verified': len(files)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2] / 'verification/p01')
    args = parser.parse_args()
    count = files = 0
    # Older records without this map retain their original separate verifiers.
    for path in sorted(args.root.rglob('retrieval.json')):
        if 'retained_file_sha256' in json.loads(path.read_bytes()):
            result = verify_record(path)
            count += 1
            files += result['files_verified']
    if not count:
        raise ValueError('no_retained_inventories')
    print(json.dumps({'result': 'CONSISTENT_RETAINED_BYTES', 'records': count,
                      'file_bindings': files, 'authenticity_or_acceptance_established': False}))


if __name__ == '__main__':
    main()
