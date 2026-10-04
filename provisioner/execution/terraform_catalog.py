"""Reviewed Terraform writer scopes from package-owned source resources.

The catalog is the sole index; this reader neither runs Terraform nor grants
native authority. The caller supplies a trusted, stable resource tree. Bounded
reads and no-link checks reject ambiguous files, not hostile concurrent changes
to an administrator-controlled directory or all Terraform language errors.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat

from hosting_resources import RESOURCE_ROOT as ROOT
from provisioner.compiler.components import COMPONENTS

MAX_BYTES = 1024 * 1024
MAX_ENTRIES = 512
MAX_PATHS = 20000
_NAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,127}\Z')
_PATH = re.compile(r'[A-Za-z0-9_./-]{1,1024}\Z')


def _linked(path: Path) -> bool:
    return path.is_symlink() or path.is_junction()


def _local_path(root: Path, value: str) -> Path:
    if not isinstance(value, str) or not _PATH.fullmatch(value):
        raise ValueError('Invalid Terraform catalog path')
    relative = PurePosixPath(value)
    if (relative.is_absolute() or relative.as_posix() != value or '..' in relative.parts
            or '.terraform' in relative.parts or len(relative.parts) < 2
            or relative.parts[0] != 'terraform'):
        raise ValueError('Terraform path must be normalized and resource-relative')
    path = root
    for part in relative.parts:
        path /= part
        if _linked(path):
            raise ValueError('Linked Terraform source paths are not supported')
    if not path.resolve().is_relative_to(root / 'terraform'):
        raise ValueError('Terraform source escapes its resource tree')
    return path


def _document(root: Path, relative: str) -> dict:
    path = _local_path(root, relative)
    flags = (os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
             | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_CLOEXEC', 0))
    descriptor = os.open(path, flags)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or not 1 <= info.st_size <= MAX_BYTES:
            raise ValueError('Terraform JSON must be a bounded regular file')
        with os.fdopen(descriptor, 'rb', closefd=False) as stream:
            raw = stream.read(MAX_BYTES + 1)
        after = os.fstat(descriptor)
        if (len(raw) != info.st_size or len(raw) > MAX_BYTES
                or (info.st_size, info.st_mtime_ns, info.st_ctime_ns) !=
                   (after.st_size, after.st_mtime_ns, after.st_ctime_ns)):
            raise ValueError('Terraform JSON changed during reading')
    finally:
        os.close(descriptor)

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate Terraform JSON property')
            result[key] = value
        return result

    def reject(_):
        raise ValueError('Non-finite Terraform JSON number')

    def number(text):
        value = float(text)
        if not math.isfinite(value):
            reject(text)
        return value

    try:
        document = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                              parse_constant=reject, parse_float=number)
    except (UnicodeError, RecursionError) as exc:
        raise ValueError('Invalid Terraform JSON encoding or nesting') from exc
    if not isinstance(document, dict):
        raise ValueError('Terraform JSON must be an object')
    return document


def _owned_source(root: Path, directory: Path, source: object) -> Path:
    if (not isinstance(source, str) or not _PATH.fullmatch(source)
            or not source.startswith(('./', '../')) or '//' in source
            or source.endswith('/')):
        raise ValueError('Root/module ownership mismatch: explicit local source required')
    path = directory
    for index, part in enumerate(source.split('/')):
        if part == '.':
            if index != 0:
                raise ValueError('Root/module ownership mismatch: ambiguous local source')
            continue
        path = path.parent if part == '..' else path / part
        if not path.is_relative_to(root / 'terraform') or _linked(path) or not path.is_dir():
            raise ValueError('Root/module ownership mismatch: unsafe local source')
    return path


def _registered_paths(root: Path) -> set[str]:
    """Scan delivered source only; provider/module caches are not source scopes."""
    found, count = set(), 0

    def unavailable(error):
        raise error

    for directory, dirs, files in os.walk(root / 'terraform', followlinks=False,
                                         onerror=unavailable):
        dirs[:] = sorted(name for name in dirs if name != '.terraform')
        count += len(dirs) + len(files)
        if count > MAX_PATHS:
            raise ValueError('Terraform source tree exceeds the scan bound')
        base = Path(directory)
        if any(_linked(base / name) for name in dirs):
            raise ValueError('Linked Terraform source directories are not supported')
        if 'main.tf.json' in files:
            relative = (base / 'main.tf.json').relative_to(root).as_posix()
            _local_path(root, relative)
            found.add(base.relative_to(root).as_posix())
    return found


def entries(root: Path = ROOT) -> list[dict]:
    """Return validated catalog order unchanged, without a fixed scope count.

    Catalog/provider/source shape checks do not replace Terraform validation,
    signed source custody, current grants, supported tuples or native readback.
    """
    root = Path(root).resolve(strict=True)
    doc = _document(root, 'terraform/catalog.json')
    if (set(doc) != {'format', 'entries'} or doc['format'] != 'hosting-terraform-catalog/1'
            or not isinstance(doc['entries'], list) or not 1 <= len(doc['entries']) <= MAX_ENTRIES):
        raise ValueError('Nonempty bounded Terraform catalogue required')
    names, paths = set(), set()
    for row in doc['entries']:
        if (not isinstance(row, dict)
                or set(row) != {'id', 'platform', 'kind', 'module', 'root', 'owner_scope'}
                or not all(isinstance(row[key], str) and _NAME.fullmatch(row[key])
                           for key in ('id', 'platform', 'kind', 'owner_scope'))):
            raise ValueError('Invalid Terraform catalogue entry')
        if row['id'] in names or row['kind'] not in {'component', 'composition'}:
            raise ValueError('Duplicate or invalid Terraform scope')
        if row['platform'] not in COMPONENTS:
            raise ValueError('Unknown Terraform platform family')
        names.add(row['id'])
        for field in ('module', 'root'):
            path = _local_path(root, row[field])
            if not path.is_dir() or row[field] in paths:
                raise ValueError('Missing, duplicate or unsafe Terraform path')
            paths.add(row[field])
        module = _document(root, row['module'] + '/main.tf.json')
        config = _document(root, row['root'] + '/main.tf.json')
        calls = config.get('module')
        if (not isinstance(calls, dict) or set(calls) != {'owned'}
                or not isinstance(calls['owned'], dict)
                or _owned_source(root, root / row['root'], calls['owned'].get('source')) != root / row['module']):
            raise ValueError('Root/module ownership mismatch')
        providers = []
        for document in (module, config):
            terraform = document.get('terraform')
            required = terraform.get('required_providers') if isinstance(terraform, dict) else None
            if not isinstance(required, dict) or not required:
                raise ValueError('Root/module provider declarations are missing')
            providers.append(required)
        if providers[0] != providers[1]:
            raise ValueError('Root/module provider mismatch')
    if _registered_paths(root) != paths:
        raise ValueError('Unregistered or missing Terraform configuration')
    return doc['entries']
