"""Bounded, nonblocking diagnostic spool; never an audit/effect journal."""

import fcntl
import hashlib
import json
import os
import stat
from pathlib import Path
from typing import BinaryIO

LIMIT = 65536


class BoundedSignalBuffer:
    def __init__(self, directory: Path = Path("/tmp/product-telemetry")) -> None:
        self.directory = directory

    def _open(self) -> BinaryIO:
        self.directory.mkdir(mode=0o700, exist_ok=True)
        info = self.directory.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid():
            raise OSError("Invalid diagnostic directory")
        # Kubernetes fsGroup volumes inherit setgid; it grants no access.
        if stat.S_IMODE(info.st_mode) & 0o777 != 0o700:
            raise OSError("Diagnostic directory must be private")
        fd = os.open(self.directory / "events.jsonl", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        handle = os.fdopen(fd, "r+b", buffering=0)
        info = os.fstat(handle.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            handle.close()
            raise OSError("Invalid diagnostic file")
        return handle

    def append(self, record: dict[str, object]) -> str:
        raw = (json.dumps(record, separators=(",", ":"), sort_keys=True) + "\n").encode()
        if len(raw) > 1024:
            return "unavailable"
        try:
            with self._open() as handle:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                size = handle.seek(0, os.SEEK_END)
                if size + len(raw) > LIMIT:
                    return "full"
                if handle.write(raw) != len(raw):
                    handle.truncate(size)
                    return "unavailable"
                return "buffered"
        except BlockingIOError:
            return "contended"
        except OSError:
            return "unavailable"

    def snapshot(self) -> bytes:
        with self._open() as handle:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            raw = handle.read(LIMIT + 1)
            if len(raw) > LIMIT:
                raise ValueError("Oversized diagnostic buffer")
            return raw

    def acknowledge(self, expected_sha256: str) -> None:
        # Call only after an independently retained and validated snapshot. New
        # writes invalidate this acknowledgement; no unseen suffix is deleted.
        with self._open() as handle:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            raw = handle.read(LIMIT + 1)
            if len(raw) > LIMIT or hashlib.sha256(raw).hexdigest() != expected_sha256:
                raise ValueError("Diagnostic snapshot changed")
            handle.truncate(0)
