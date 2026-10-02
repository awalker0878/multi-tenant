"""Private, bounded review artifact custody shared by signer and intake.

No signing, enrollment, database or network authority lives in this module.
"""
from contextlib import contextmanager
import os
from pathlib import Path
import secrets
import stat
from typing import Callable


@contextmanager
def private_parent(value: str):
    """Open each ancestor without following links; final parent is private.

    Root-owned sticky ancestors (e.g. /tmp) are allowed, never as the final
    parent. No directory is created and unsupported OS primitives fail closed.
    """
    path = Path(value)
    if (os.name != 'posix' or not isinstance(value, str) or not 1 <= len(value) <= 4096
            or not path.is_absolute() or str(path) != value or value.startswith('//')
            or value != value.strip() or any(ord(c) < 32 or ord(c) == 127 for c in value)
            or any(part in ('.', '..') for part in path.parts) or len(path.parts) < 2):
        raise ValueError('An exact absolute POSIX file path is required')
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    fd = os.open('/', flags)
    try:
        for part in path.parts[1:-1]:
            info = os.fstat(fd)
            if (info.st_uid not in (0, os.geteuid())
                    or info.st_mode & 0o022 and not (info.st_uid == 0 and info.st_mode & stat.S_ISVTX)):
                raise ValueError('Unsafe review ancestor')
            child = os.open(part, flags, dir_fd=fd)
            os.close(fd)
            fd = child
        info = os.fstat(fd)
        if info.st_uid not in (0, os.geteuid()) or info.st_mode & 0o077:
            raise ValueError('Review files require a private parent directory')
        yield fd, path.name
    finally:
        os.close(fd)


def read_private(path: str, limit: int) -> bytes:
    with private_parent(path) as (parent, name):
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
                     dir_fd=parent)
        try:
            before = os.fstat(fd)
            if (not stat.S_ISREG(before.st_mode) or before.st_uid not in (0, os.geteuid())
                    or before.st_mode & 0o077 or before.st_nlink != 1 or not 1 <= before.st_size <= limit):
                raise ValueError('Review input must be a bounded private regular file')
            with os.fdopen(fd, 'rb', closefd=False) as stream:
                raw = stream.read(limit + 1)
            after = os.fstat(fd)
            if (len(raw) != before.st_size or len(raw) > limit
                    or (before.st_size, before.st_mtime_ns, before.st_ctime_ns) !=
                       (after.st_size, after.st_mtime_ns, after.st_ctime_ns)):
                raise ValueError('Review input changed during reading')
            return raw
        finally:
            os.close(fd)


def publish_once(path: str, raw: bytes, recheck: Callable[[], None]) -> None:
    """Create once, never replace. Failed post-link fsync leaves original output.

    A failure is not proof that no final file exists. Do not delete or overwrite
    that file on a retry; reconcile its exact bytes independently.
    """
    with private_parent(path) as (parent, name):
        temporary = '.review-' + secrets.token_hex(16)
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                     0o600, dir_fd=parent)
        try:
            with os.fdopen(fd, 'wb', closefd=False) as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            recheck()
            os.link(temporary, name, src_dir_fd=parent, dst_dir_fd=parent, follow_symlinks=False)
        finally:
            os.close(fd)
            os.unlink(temporary, dir_fd=parent)
            os.fsync(parent)



def require_new_output(path: str) -> None:
    """Reject an existing final name before intake; publication rechecks atomically."""
    with private_parent(path) as (parent, name):
        try:
            os.stat(name, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            return
        raise FileExistsError("Review output already exists")
