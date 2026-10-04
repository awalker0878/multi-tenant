"""Provider-neutral boundaries for protected native read files and JSON.

Native session formats, platform scope and endpoint selection belong to adapters.
These helpers neither choose a vendor nor issue credentials or read authority.
"""
from __future__ import annotations

import json
import math
import os
import stat
from pathlib import Path

from .model import _unique_pairs


class NativeReadHeld(RuntimeError):
    """A native read was refused; never include native bodies or secret values."""


def read_protected(path: Path, limit: int, *, secret: bool = True) -> bytes:
    """No symlink/FIFO fallback; ownership and bounds are checked on the open FD."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid not in (0, os.geteuid())
                or info.st_mode & (0o077 if secret else 0o022) or info.st_size > limit):
            raise NativeReadHeld('Native read configuration is not protected')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            value = stream.read(limit + 1)
        if len(value) > limit:
            raise NativeReadHeld('Native read configuration exceeds its byte limit')
        return value
    finally:
        os.close(fd)


def decode_json(raw: bytes, limit: int) -> object:
    """Bounded, duplicate-free finite JSON with an explicit nesting limit."""
    if len(raw) > limit:
        raise ValueError('Native JSON exceeds byte limit')
    def integer(text):
        value = int(text)
        if not -(2**63) <= value < 2**63:
            raise ValueError('Native integer exceeds signed 64-bit range')
        return value
    def floating(text):
        value = float(text)
        if not math.isfinite(value):
            raise ValueError('Nonfinite native number')
        return value
    result = json.loads(raw.decode('utf-8'), object_pairs_hook=_unique_pairs,
                        parse_int=integer, parse_float=floating, parse_constant=floating)
    pending, count = [(result, 0)], 0
    while pending:
        value, depth = pending.pop()
        count += 1
        if depth > 32 or count > 250000:
            raise ValueError('Native JSON structural budget exceeded')
        children = value.values() if isinstance(value, dict) else value if isinstance(value, list) else ()
        pending.extend((child, depth + 1) for child in children)
    return result
