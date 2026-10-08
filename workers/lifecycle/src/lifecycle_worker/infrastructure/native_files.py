"""Bounded no-follow reads and exact artifact inventory for native worker inputs."""

import os
import stat
from pathlib import Path, PurePosixPath
from typing import Any

from lifecycle_worker.application.native import NativeHeld


def sync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def protected_read(path: Path, limit: int) -> bytes:
    if not path.is_absolute() or limit < 1:
        raise NativeHeld("protected_absolute_file_required")
    # Reject symlinks in every path component, not just the final component.
    for part in (path, *path.parents):
        if part.is_symlink():
            raise NativeHeld("symlink_native_input")
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as handle:
            info = os.fstat(handle.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_size > limit or info.st_mode & 0o022:
                raise NativeHeld("unsafe_native_file")
            raw = handle.read(limit + 1)
            if len(raw) > limit:
                raise NativeHeld("oversized_native_file")
            return raw
    except OSError:
        raise NativeHeld("native_file_unavailable") from None


def relative_file(root: Path, name: Any) -> Path:
    if (
        not isinstance(name, str)
        or not name
        or "\\" in name
        or any(ord(c) < 32 for c in name)
        or PurePosixPath(name).is_absolute()
        or any(p in {"", ".", ".."} for p in name.split("/"))
    ):
        raise NativeHeld("invalid_bundle_path")
    return root / name
