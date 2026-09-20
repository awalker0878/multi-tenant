"""Private, durable operator artifacts. These functions do not issue authority."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat

from tools.neutron_observe import strict_loads


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def utcnow():
    return datetime.now(timezone.utc)


def current_window(record, now=None):
    now = now or utcnow()
    times = [datetime.fromisoformat(record[k].replace('Z', '+00:00'))
             for k in ('valid_from', 'valid_until')]
    require(all(t.tzinfo is not None for t in times), 'Timezone required')
    start, end = times
    require(start <= now < end and 0 < (end - start).total_seconds() <= 3600,
            'Authority is expired, future-dated or longer than one hour')


def private_path(path, *, directory=False):
    path = Path(path).absolute()
    require(not any(p.is_symlink() for p in (path, *path.parents)), 'Symlink in private path')
    info = path.stat()
    require(info.st_uid == os.getuid() and not stat.S_IMODE(info.st_mode) & 0o077,
            'Operator artifact must be owner-only')
    require(stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode),
            'Unexpected operator artifact type')
    return path


def read_private(path):
    path = private_path(path)
    # O_NOFOLLOW also rejects a final-component symlink swapped after validation.
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), 'rb') as stream:
        return stream.read()


def load_private(path):
    return strict_loads(read_private(path))


def sync_directory(directory):
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def write_new(path, data):
    path = Path(path)
    private_path(path.parent, directory=True)
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600), 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    sync_directory(path.parent)


def new_directory(path, repository):
    path = Path(path).absolute()
    require(not path.resolve().is_relative_to(Path(repository).resolve()),
            'Use private operator storage outside the repository')
    private_path(path.parent, directory=True)
    path.mkdir(mode=0o700)
    sync_directory(path.parent)
    return path


def file_map(directory):
    result = {}
    for path in sorted(Path(directory).rglob('*')):
        require(not path.is_symlink(), 'Symlinks are not supported in sealed execution files')
        if path.is_file():
            result[path.relative_to(directory).as_posix()] = digest(path.read_bytes())
    return result
