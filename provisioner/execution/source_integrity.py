"""Read-only source consistency against a pinned Git commit or explicit manifest.

Integrity is not signer trust, architecture approval or native qualification.
Installed callers must select a checkout explicitly; no working-directory or
historical-manifest fallback is available. Source and Git configuration must be
under trusted custody: these checks do not lock a tree against hostile writers.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess

from hosting_resources import SOURCE_ROOT as ROOT

MAX_FILE_BYTES = 128 * 1024 * 1024
MAX_MANIFEST_BYTES = 4 * 1024 * 1024
MAX_GIT_METADATA_BYTES = 8 * 1024 * 1024
MAX_FILES = 25000
_SHA256 = re.compile(r'[0-9a-f]{64}\Z')
_COMMIT = re.compile(r'[0-9a-f]{40}\Z')


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError('Duplicate manifest field')
        result[key] = value
    return result


def _reject_number(_):
    raise ValueError('Unsupported manifest number')


def _number(text):
    value = float(text)
    if not math.isfinite(value):
        _reject_number(text)
    return value


def _relative(name):
    if (not isinstance(name, str) or not 1 <= len(name) <= 4096
            or '\\' in name or ':' in name or any(ord(c) < 32 or ord(c) == 127 for c in name)):
        raise ValueError('Unsafe source path')
    relative = PurePosixPath(name)
    if (relative.is_absolute() or relative.as_posix() != name or name == '.'
            or '..' in relative.parts or '.git' in relative.parts):
        raise ValueError('Unsafe source path')
    return relative


def _path(root, name):
    path = root
    for part in _relative(name).parts:
        path /= part
        if path.is_symlink() or path.is_junction():
            raise ValueError('Linked source path')
    if not path.resolve().is_relative_to(root):
        raise ValueError('Source path escapes its root')
    return path


def _fingerprint(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _read(path, limit, *, blob=False, retain=False):
    """Stream a regular file and detect changes observed during this read."""
    if path.is_symlink() or path.is_junction():
        raise ValueError('Linked source input')
    flags = (os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
             | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_CLOEXEC', 0))
    descriptor = os.open(path, flags)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
            raise ValueError('Source input is not a bounded regular file')
        digest = hashlib.sha1() if blob else hashlib.sha256()
        if blob:
            digest.update(b'blob ' + str(before.st_size).encode('ascii') + b'\0')
        chunks, total = [], 0
        with os.fdopen(descriptor, 'rb', closefd=False) as stream:
            while data := stream.read(min(1024 * 1024, limit - total + 1)):
                total += len(data)
                if total > limit:
                    raise ValueError('Source input exceeds its bound')
                digest.update(data)
                if retain:
                    chunks.append(data)
        if (total != before.st_size or _fingerprint(before) != _fingerprint(os.fstat(descriptor))
                or _fingerprint(before) != _fingerprint(path.stat(follow_symlinks=False))):
            raise ValueError('Source input changed during reading')
        return b''.join(chunks) if retain else digest.hexdigest()
    finally:
        os.close(descriptor)


def verify_snapshot(root, manifest_path):
    """Check only explicitly enumerated bytes, not export completeness or trust."""
    issues, count = [], 0
    try:
        root = Path(root).resolve(strict=True)
        raw = _read(Path(manifest_path), MAX_MANIFEST_BYTES, retain=True)
        data = json.loads(raw.decode('utf-8'), object_pairs_hook=_pairs,
                          parse_constant=_reject_number, parse_float=_number)
        if set(data) != {'file_sha256'}:
            raise ValueError('Exact snapshot manifest fields required')
        items = data['file_sha256']
        if not isinstance(items, dict) or not 1 <= len(items) <= MAX_FILES:
            raise ValueError('Nonempty bounded digest map required')
        for name, digest in items.items():
            _relative(name)
            if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
                raise ValueError('An exact SHA-256 digest is required')
        for name, digest in items.items():
            count += 1
            try:
                actual = _read(_path(root, name), MAX_FILE_BYTES)
            except FileNotFoundError:
                issues.append({'kind': 'MISSING_FILE', 'file': name})
            except (OSError, ValueError):
                issues.append({'kind': 'UNSAFE_OR_UNREADABLE_FILE', 'file': name})
            else:
                if actual != digest:
                    issues.append({'kind': 'DIGEST_MISMATCH', 'file': name})
    except (OSError, ValueError, KeyError, TypeError, RecursionError, UnicodeError, json.JSONDecodeError):
        issues.append({'kind': 'INVALID_SNAPSHOT_MANIFEST'})
    return {'status': 'HASHES_MATCH' if not issues else 'FAILED_INTEGRITY_CHECK',
            'files_checked': count, 'issues': issues,
            'scope': 'Explicit export manifest; not signature or native qualification.'}


def _git(root, *args):
    # Ignore ambient repository/index/config/replace overrides. Do not refresh an
    # index, invoke a monitor hook, prompt, or lazily fetch missing objects.
    environment = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    environment.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
        GIT_TERMINAL_PROMPT='0', GIT_OPTIONAL_LOCKS='0', GIT_NO_LAZY_FETCH='1')
    result = subprocess.check_output(['git', '--no-replace-objects', '-c', 'core.fsmonitor=false',
        '-c', 'core.untrackedCache=false', '-C', str(root), *args], env=environment,
        stdin=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=60)
    if len(result) > MAX_GIT_METADATA_BYTES:
        raise ValueError('Git metadata exceeds its accepted size')
    return result


def _unavailable(count=0):
    return {'status': 'BLOCKED_NO_CURRENT_CHECKOUT', 'files_checked': count,
            'issues': [{'kind': 'CURRENT_GIT_CHECKOUT_REQUIRED',
                        'action': 'Supply an explicit source checkout, or an explicit export root and --manifest.'}]}


def verify(root=ROOT):
    """Verify tracked bytes against one SHA-1 Git commit, then recheck HEAD.

    Git output is size-checked after each subprocess returns; its timeout is per
    command, not a hard memory/filesystem/whole-operation deadline. This does not
    lock or cryptographically sign a concurrently writable checkout.
    """
    issues, count = [], 0
    if root is None:
        return _unavailable()
    try:
        root = Path(root).resolve(strict=True)
        if Path(_git(root, 'rev-parse', '--show-toplevel').decode().strip()).resolve() != root:
            raise ValueError('Not repository root')
        commit = _git(root, 'rev-parse', '--verify', 'HEAD^{commit}').decode().strip()
        if not _COMMIT.fullmatch(commit):
            raise ValueError('Unsupported Git object format')
        records = _git(root, 'ls-tree', '-rz', '--full-tree', commit).split(b'\0')
        if not 1 <= len(records) - 1 <= MAX_FILES or records[-1] != b'':
            raise ValueError('Invalid bounded Git tree')
        for record in records[:-1]:
            metadata, name = record.split(b'\t', 1)
            mode, kind, expected = metadata.split()
            relative = name.decode('utf-8')
            count += 1
            try:
                if (kind != b'blob' or mode not in (b'100644', b'100755')
                        or not _COMMIT.fullmatch(expected.decode('ascii'))):
                    raise ValueError('Unsupported tracked object')
                actual = _read(_path(root, relative), MAX_FILE_BYTES, blob=True)
            except FileNotFoundError:
                issues.append({'kind': 'MISSING_TRACKED_FILE', 'file': relative})
            except (OSError, ValueError):
                issues.append({'kind': 'UNSUPPORTED_OR_UNSAFE_TRACKED_PATH', 'file': relative})
            else:
                if actual != expected.decode('ascii'):
                    issues.append({'kind': 'WORKTREE_DIFFERS_FROM_HEAD', 'file': relative})
        for name in _git(root, 'ls-files', '--others', '--exclude-standard', '-z').split(b'\0'):
            if name:
                issues.append({'kind': 'UNTRACKED_SOURCE_FILE', 'file': name.decode('utf-8')})
        if _git(root, 'diff', '--cached', '--name-only', '--no-ext-diff', '--no-textconv', commit, '--').strip():
            issues.append({'kind': 'INDEX_DIFFERS_FROM_HEAD'})
        if _git(root, 'rev-parse', '--verify', 'HEAD^{commit}').decode().strip() != commit:
            issues.append({'kind': 'HEAD_CHANGED_DURING_CHECK'})
    except (OSError, ValueError, TypeError, UnicodeError, subprocess.SubprocessError):
        return _unavailable(count)
    return {'status': 'HASHES_MATCH' if not issues else 'FAILED_INTEGRITY_CHECK',
            'commit': commit, 'files_checked': count, 'issues': issues,
            'scope': 'Tracked worktree bytes equal current Git HEAD; not signature, architecture approval or native qualification.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT,
                        help='Explicit checkout/export root; required outside source development')
    parser.add_argument('--manifest', type=Path)
    args = parser.parse_args(arvy)
    if args.root is None:
        result = _unavailable()
    else:
        result = (verify_snapshot(args.root, args.manifest) if args.manifest is not None
                  else verify(args.root))
    print(json.dumps(result, indent=2))
    return 0 if not result['issues'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
